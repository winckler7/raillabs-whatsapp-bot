import os
import sys
import requests
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
)

app = Flask(__name__)
init_db()

# El verify token lo configura Meta a nivel de la App (no por número de
# WhatsApp), así que se queda como env var global incluso con varias cuentas
# -- las credenciales de envío (token, phone_number_id) sí son por cuenta y
# se buscan en la tabla `cuentas` con get_cuenta_by_phone_number_id().
VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v20.0")


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
        message = value["messages"][0]
    except (KeyError, IndexError, TypeError):
        # No es un mensaje nuevo (p. ej. es un "status update"): lo ignoramos.
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
    conversacion_id = get_or_create_conversacion(cuenta["id"], sender)

    if message.get("type") != "text":
        # Por ahora solo entendemos texto -- avisamos en vez de dejar al
        # cliente sin respuesta (las notas de voz son muy comunes en WhatsApp).
        respuesta = "Por ahora solo puedo leer mensajes de texto, ¿me lo escribes con palabras? 🙏"
        registrar_mensaje(conversacion_id, "saliente", respuesta)
        send_message(cuenta, sender, respuesta)
        return jsonify(status="ignored"), 200

    text = message["text"]["body"]
    registrar_mensaje(conversacion_id, "entrante", text, wa_message_id=message["id"])

    if text.strip().upper() == "BORRAR MIS DATOS":
        # Cumple lo prometido en la pagina de eliminacion de datos exigida
        # por Meta para publicar la app. Borra la conversación (y en cascada
        # sus mensajes, incluido el que se acaba de registrar arriba) --
        # no se registra la confirmación, para no dejar rastro nuevo.
        borrar_historial(cuenta["id"], sender)
        send_message(cuenta, sender, "Listo, borramos tu historial de conversación con nosotros. Si nos vuelves a escribir, empezamos desde cero. 🙏")
        return jsonify(status="borrado"), 200

    messages = get_historial(cuenta["id"], sender)
    add_user_message(messages, text)
    respuesta = chat(messages)
    add_assistant_message(messages, respuesta)
    guardar_historial(cuenta["id"], sender, messages)
    registrar_mensaje(conversacion_id, "saliente", respuesta)

    send_message(cuenta, sender, respuesta)

    return jsonify(status="ok"), 200


def send_message(cuenta, to, body):
    # Envía un mensaje de texto saliente al usuario `to` vía la Graph API de
    # Meta, usando el token y phone_number_id de la cuenta correspondiente.
    graph_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{cuenta['phone_number_id']}/messages"
    headers = {"Authorization": f"Bearer {cuenta['whatsapp_token']}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    response = requests.post(graph_url, headers=headers, json=payload)
    if not response.ok:
        # Meta describe el motivo real del rechazo en el body (ej. número no
        # autorizado, token vencido, etc.) — el código HTTP solo no alcanza.
        print("Error de WhatsApp API:", response.status_code, response.text, flush=True)
    response.raise_for_status()


if __name__ == "__main__":
    app.run(port=5000, debug=True)
