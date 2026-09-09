#Load env variables
from dotenv import load_dotenv

load_dotenv()

#Create an API Client
import json
import os

from anthropic import Anthropic
from system_prompt import SYSTEM_PROMPT
import calendario
import correo

client = Anthropic()
model = "claude-sonnet-5"

TOOLS = [
    {
        "name": "consultar_disponibilidad",
        "description": (
            "Devuelve los próximos horarios disponibles para agendar una "
            "llamada con Jorge, dueño de RailLabs (lunes a viernes, 9:00-11:00 y 17:00-18:00, "
            "hora de Ciudad de México). Úsala antes de ofrecerle horarios "
            "concretos al cliente -- nunca inventes ni asumas horarios libres."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "agendar_cita",
        "description": (
            "Crea la cita en el Google Calendar de Jorge con el resumen del "
            "caso en la descripción. Solo llámala después de que el cliente "
            "confirmó explícitamente uno de los horarios que devolvió "
            "consultar_disponibilidad."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "inicio_iso": {
                    "type": "string",
                    "description": (
                        "Fecha y hora de inicio exacta elegida por el "
                        "cliente, tal como vino en el campo inicio_iso de "
                        "consultar_disponibilidad."
                    ),
                },
                "nombre_cliente": {
                    "type": "string",
                    "description": "Nombre real del cliente. Es obligatorio pedírselo antes de agendar si todavía no lo sabes -- nunca uses un nombre genérico ni inventado.",
                },
                "correo_cliente": {
                    "type": "string",
                    "description": "Correo del cliente, solo si lo dio voluntariamente al preguntarle si quiere la invitación por correo. Es opcional -- si no lo dio, omite este campo por completo, no insistas ni lo pidas como requisito.",
                },
                "contexto_actual": {
                    "type": "string",
                    "description": (
                        "Situación actual del cliente en 2-4 líneas: a qué se "
                        "dedica su negocio, qué campaña o servicio le "
                        "interesa, y el motivo o dolor que lo trajo a "
                        "escribir. OJO: esto se le muestra también al cliente "
                        "en su correo de confirmación, no es solo una nota "
                        "interna para Jorge -- escríbelo hablándole "
                        "directo a él en segunda persona ('tienes', 'buscas', "
                        "nunca 'el cliente tiene'), en tono respetuoso, "
                        "positivo y profesional, nunca con juicios de valor "
                        "ni describiéndolo de forma que lo incomode leer."
                    ),
                },
                "objetivo_cliente": {
                    "type": "string",
                    "description": (
                        "Situación deseada del cliente en 1-3 líneas: qué "
                        "resultado busca lograr con esto. Mismo criterio que "
                        "contexto_actual: se le muestra al cliente, en "
                        "segunda persona y tono respetuoso."
                    ),
                },
            },
            "required": ["inicio_iso", "nombre_cliente", "contexto_actual", "objetivo_cliente"],
        },
    },
    {
        "name": "cancelar_cita",
        "description": (
            "Cancela la cita activa del cliente (identificado por su número "
            "de WhatsApp) y borra el evento del Google Calendar de Jorge. "
            "Antes de llamarla: 1) ofrécele reagendar a otro horario en vez "
            "de cancelar del todo (usa reagendar_cita si acepta), y 2) si "
            "de plano quiere cancelar, pídele que lo confirme explícitamente "
            "una vez más. Nunca la llames solo porque preguntó cómo "
            "cancelar o dudó -- solo tras su confirmación explícita."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "reagendar_cita",
        "description": (
            "Mueve la cita activa del cliente a un horario nuevo: cancela el "
            "evento viejo y crea uno nuevo en un solo paso, conservando el "
            "contexto original. Antes de llamarla usa consultar_disponibilidad "
            "para ofrecerle horarios y espera a que confirme cuál elige."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nuevo_inicio_iso": {
                    "type": "string",
                    "description": "Nuevo horario elegido, tal como vino en el campo inicio_iso de consultar_disponibilidad.",
                },
            },
            "required": ["nuevo_inicio_iso"],
        },
    },
]


def add_user_message(messages, text):
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


def add_assistant_message(messages, text):
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)


def _ejecutar_tool(nombre, input_, cuenta, sender, conversacion_id):
    if nombre == "consultar_disponibilidad":
        return calendario.consultar_disponibilidad()

    if nombre == "agendar_cita":
        nombre_cliente = input_.get("nombre_cliente") or "Cliente de WhatsApp"
        correo_cliente = input_.get("correo_cliente")
        contexto_actual = input_["contexto_actual"]
        objetivo_cliente = input_["objetivo_cliente"]
        # La DB y la descripción del evento de Calendar siguen guardando un
        # solo texto de resumen (no vale la pena una migración de columna
        # solo para esto) -- el correo a Jorge sí usa los dos campos por
        # separado, para que se vean como secciones claras.
        resumen = f"Contexto actual: {contexto_actual}\nObjetivo: {objetivo_cliente}"
        resultado = calendario.crear_evento(
            input_["inicio_iso"], nombre_cliente, sender, resumen
        )
        if resultado["ok"]:
            correo_enviado = False
            if correo_cliente:
                correo_enviado = correo.enviar_confirmacion_cliente(
                    correo_cliente, nombre_cliente, resultado["texto"],
                    contexto_actual, objetivo_cliente,
                )
            resultado["correo_enviado"] = correo_enviado

            # El aviso a Jorge se manda por correo apenas se agenda (a
            # diferencia de WhatsApp, el correo no tiene ventana de 24h, así
            # que no hace falta esperar a que él escriba "RESUMEN DEL DÍA").
            correo.enviar_aviso_dueno(
                nombre_cliente, sender, correo_cliente, resultado["texto"],
                contexto_actual, objetivo_cliente,
            )

            try:
                from db import registrar_cita
                registrar_cita(
                    cuenta["id"], conversacion_id, sender, nombre_cliente,
                    input_["inicio_iso"], resumen, correo_cliente,
                    resultado.get("event_id"),
                )
            except Exception as e:
                print(f"Error registrando cita en la base de datos: {e}", flush=True)
        return resultado

    if nombre == "cancelar_cita":
        from db import obtener_cita_activa, marcar_cita_cancelada

        cita = obtener_cita_activa(cuenta["id"], sender)
        if not cita:
            return {"ok": False, "error": "No encontramos una cita activa a tu nombre."}

        if cita["google_event_id"]:
            calendario.cancelar_evento(cita["google_event_id"])
        marcar_cita_cancelada(cita["id"])

        texto_fecha = calendario.formato_legible(cita["inicio"].astimezone(calendario.ZONA))
        if cita["correo"]:
            correo.enviar_cancelacion_cliente(cita["correo"], cita["nombre_cliente"], texto_fecha)
        correo.enviar_aviso_cancelacion_dueno(cita["nombre_cliente"], sender, cita["correo"], texto_fecha)

        return {"ok": True, "texto": texto_fecha}

    if nombre == "reagendar_cita":
        from db import obtener_cita_activa, actualizar_cita_reagendada

        cita = obtener_cita_activa(cuenta["id"], sender)
        if not cita:
            return {"ok": False, "error": "No encontramos una cita activa a tu nombre para reagendar."}

        resultado = calendario.crear_evento(
            input_["nuevo_inicio_iso"], cita["nombre_cliente"], sender, cita["resumen"]
        )
        if not resultado["ok"]:
            return resultado

        texto_anterior = calendario.formato_legible(cita["inicio"].astimezone(calendario.ZONA))
        if cita["google_event_id"]:
            calendario.cancelar_evento(cita["google_event_id"])
        actualizar_cita_reagendada(cita["id"], input_["nuevo_inicio_iso"], resultado.get("event_id"))

        if cita["correo"]:
            correo.enviar_reagendo_cliente(cita["correo"], cita["nombre_cliente"], texto_anterior, resultado["texto"])
        correo.enviar_aviso_reagendo_dueno(
            cita["nombre_cliente"], sender, cita["correo"], texto_anterior, resultado["texto"]
        )

        return {"ok": True, "texto": resultado["texto"]}

    return {"ok": False, "error": f"Tool desconocida: {nombre}"}


def chat(messages, cuenta, sender, conversacion_id=None):
    # Copia local: las tools solo se resuelven dentro de este turno, no se
    # persiste el intercambio tool_use/tool_result en el historial que se
    # guarda en la base de datos (que sigue siendo solo texto plano).
    working = list(messages)

    for _ in range(5):
        message = client.messages.create(
            model=model,
            max_tokens=700,
            # Flujo de ventas ya está guiado paso a paso en el system prompt,
            # asi que no necesitamos que el modelo "piense" antes de responder
            # -- desactivar thinking reduce la latencia, que importa en un chat
            # de WhatsApp donde el usuario espera respuesta casi inmediata.
            thinking={"type": "disabled"},
            # El system prompt ya es grande (menu de servicios + FAQs). Cachear
            # el prefijo evita pagar el costo completo en cada mensaje del chat
            # -- cada turno nuevo solo paga por lo que se agregó desde el turno
            # anterior, el resto se lee de cache a ~10% del costo.
            cache_control={"type": "ephemeral"},
            tools=TOOLS,
            messages=working,
            system=SYSTEM_PROMPT,
        )

        texto = "".join(block.text for block in message.content if block.type == "text")

        if message.stop_reason != "tool_use":
            return texto

        working.append({"role": "assistant", "content": [b.model_dump() for b in message.content]})

        resultados_tools = [
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(_ejecutar_tool(block.name, block.input, cuenta, sender, conversacion_id)),
            }
            for block in message.content
            if block.type == "tool_use"
        ]
        working.append({"role": "user", "content": resultados_tools})

    return "Tuve un problema agendando la cita, ¿lo intentamos de nuevo en un momento?"


def simular_chat_whatsapp():
    """Simula la conversación por consola. Cuando se conecte la API real de
    WhatsApp Business, esta función se reemplaza por el webhook que recibe
    el mensaje entrante y llama a chat(messages) igual que aquí."""
    messages = []
    cuenta = {
        "phone_number_id": os.environ.get("PHONE_NUMBER_ID"),
        "whatsapp_token": os.environ.get("WHATSAPP_TOKEN"),
    }

    print("Simulador de chat de WhatsApp con el asistente de RailLabs.")
    print("Escribe 'salir' para terminar.\n")

    while True:
        user_input = input("Tú: ")
        if user_input.strip().lower() == "salir":
            break

        add_user_message(messages, user_input)
        response = chat(messages, cuenta, "0000000000")
        add_assistant_message(messages, response)

        print(f"\nRailLabs: {response}\n")


if __name__ == "__main__":
    simular_chat_whatsapp()
