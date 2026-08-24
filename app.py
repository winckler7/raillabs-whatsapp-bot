import os
import sys
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sales_agent"))
from agente_ventas import chat, add_user_message, add_assistant_message
from db import (
    init_db,
    get_historial,
    guardar_historial,
    ya_procesado,
    borrar_historial,
    get_cuenta_by_phone_number_id,
    get_or_create_conversacion,
    registrar_mensaje,
    registrar_mensaje_con_media,
    set_nombre_automatico,
    actualizar_estado_entrega,
)
from graph_api import send_message, obtener_media_url, descargar_media
from panel import panel_bp

TIPOS_MEDIA = {"image", "audio", "video", "document", "sticker"}

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.register_blueprint(panel_bp)
init_db()

# El verify token lo configura Meta a nivel de la App (no por número de
# WhatsApp), así que se queda como env var global incluso con varias cuentas
# -- las credenciales de envío (token, phone_number_id) sí son por cuenta y
# se buscan en la tabla `cuentas` con get_cuenta_by_phone_number_id().
VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]


def normalize_mx_number(number):
    # El webhook entrega los numeros de Mexico con un "1" despues del "52"
    # (521XXXXXXXXXX), pero para enviar hay que quitarlo (52XXXXXXXXXX).
    if number.startswith("521") and len(number) == 13:
        return "52" + number[3:]
    return number


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    # Meta llama a este endpoint una sola vez al guardar la config del webhook,
    # para confirmar que el servidor es tuyo antes de empezar a enviarte eventos.
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    # Meta manda aquí cada evento (mensajes, confirmaciones de lectura, etc.)
    # dentro de un JSON anidado; extraemos el primer mensaje si existe.
    data = request.get_json()

    try:
        value = data["entry"][0]["changes"][0]["value"]
    except (KeyError, IndexError, TypeError):
        return jsonify(status="ignored"), 200

    if "statuses" in value:
        # Confirmaciones de entrega/lectura de mensajes que ya mandamos --
        # no son mensajes nuevos, se procesan aparte y siempre son idempotentes
        # (actualizar_estado_entrega nunca baja de nivel un estado).
        for status in value["statuses"]:
            actualizar_estado_entrega(status.get("id"), status.get("status"))
        return jsonify(status="estado_actualizado"), 200

    try:
        message = value["messages"][0]
    except (KeyError, IndexError):
        # No es un mensaje nuevo ni un status conocido: lo ignoramos.
        return jsonify(status="ignored"), 200

    if ya_procesado(message["id"]):
        # Meta reentrega el mismo mensaje si nuestro servidor fallo la
        # primera vez -- sin esto, cada reentrega se responde de nuevo.
        return jsonify(status="duplicado"), 200

    phone_number_id = value["metadata"]["phone_number_id"]
    cuenta = get_cuenta_by_phone_number_id(phone_number_id)
    if not cuenta:
        # No sabemos con qué token/número responder -- no hay cuenta
        # registrada en la tabla `cuentas` para este phone_number_id.
        print(f"Cuenta no encontrada para phone_number_id={phone_number_id}", flush=True)
        return jsonify(status="cuenta_no_encontrada"), 200

    sender = normalize_mx_number(message["from"])
    conversacion = get_or_create_conversacion(cuenta["id"], sender)
    conversacion_id = conversacion["id"]

    # WhatsApp manda el nombre de perfil del contacto junto con el mensaje --
    # se guarda como sugerencia inicial, sin pisar un nombre puesto a mano
    # desde el panel (set_nombre_automatico solo escribe si sigue en null).
    nombre_perfil = (value.get("contacts") or [{}])[0].get("profile", {}).get("name")
    if nombre_perfil:
        set_nombre_automatico(conversacion_id, nombre_perfil)

    tipo_mensaje = message.get("type")

    if tipo_mensaje in TIPOS_MEDIA:
        # Se descarga y guarda para que quede visible en el panel -- el bot
        # sigue sin "entender" el contenido, solo avisa que por ahora
        # necesita texto (igual que con cualquier otro tipo no soportado).
        media_info = message.get(tipo_mensaje, {})
        media_id = media_info.get("id")
        caption = media_info.get("caption") or f"[{tipo_mensaje}]"
        try:
            url = obtener_media_url(media_id, cuenta["whatsapp_token"])
            contenido_bytes, mime_type = descargar_media(url, cuenta["whatsapp_token"])
            registrar_mensaje_con_media(
                conversacion_id, "entrante", caption, tipo_mensaje,
                contenido_bytes, mime_type, wa_message_id=message["id"],
            )
        except Exception as e:
            print(f"Error descargando media de WhatsApp: {e}", flush=True)
            registrar_mensaje(conversacion_id, "entrante", caption, wa_message_id=message["id"], tipo=tipo_mensaje)

        if conversacion["modo"] == "bot":
            respuesta = "Por ahora solo puedo leer mensajes de texto, ¿me lo escribes con palabras? 🙏"
            wa_id = send_message(cuenta, sender, respuesta)
            registrar_mensaje(conversacion_id, "saliente", respuesta, wa_message_id=wa_id)
        return jsonify(status="media_recibido"), 200

    if tipo_mensaje != "text":
        # Otros tipos no soportados (ubicación, contacto, reacción, etc.).
        if conversacion["modo"] == "bot":
            respuesta = "Por ahora solo puedo leer mensajes de texto, ¿me lo escribes con palabras? 🙏"
            wa_id = send_message(cuenta, sender, respuesta)
            registrar_mensaje(conversacion_id, "saliente", respuesta, wa_message_id=wa_id)
        return jsonify(status="ignored"), 200

    text = message["text"]["body"]
    registrar_mensaje(conversacion_id, "entrante", text, wa_message_id=message["id"])

    if text.strip().upper() == "BORRAR MIS DATOS":
        # Cumple lo prometido en la pagina de eliminacion de datos exigida
        # por Meta para publicar la app. Borra la conversación (y en cascada
        # sus mensajes, incluido el que se acaba de registrar arriba) --
        # no se registra la confirmación, para no dejar rastro nuevo. Corre
        # siempre, sin importar el modo -- es un requisito de cumplimiento.
        borrar_historial(cuenta["id"], sender)
        send_message(cuenta, sender, "Listo, borramos tu historial de conversación con nosotros. Si nos vuelves a escribir, empezamos desde cero. 🙏")
        return jsonify(status="borrado"), 200

    if conversacion["modo"] == "humano":
        # Un humano tomó el control de esta conversación desde el panel --
        # el mensaje ya quedó registrado arriba, pero el bot no responde.
        return jsonify(status="modo_humano"), 200

    messages = get_historial(cuenta["id"], sender)
    add_user_message(messages, text)
    respuesta = chat(messages)
    add_assistant_message(messages, respuesta)
    guardar_historial(cuenta["id"], sender, messages)
    wa_id = send_message(cuenta, sender, respuesta)
    registrar_mensaje(conversacion_id, "saliente", respuesta, wa_message_id=wa_id)

    return jsonify(status="ok"), 200


if __name__ == "__main__":
    app.run(port=5000, debug=True)
