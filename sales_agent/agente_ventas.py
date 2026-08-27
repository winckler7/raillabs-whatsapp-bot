#Load env variables
from dotenv import load_dotenv

load_dotenv()

#Create an API Client
import json
import os

from anthropic import Anthropic
from system_prompt import SYSTEM_PROMPT
import calendario

client = Anthropic()
model = "claude-sonnet-5"

TOOLS = [
    {
        "name": "consultar_disponibilidad",
        "description": (
            "Devuelve los próximos horarios disponibles para agendar una "
            "llamada con Jorge (lunes a viernes, 9:00-11:00 y 17:00-18:00, "
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
                    "description": "Nombre del cliente, si lo dio. Si no lo sabes, usa 'Cliente de WhatsApp'.",
                },
                "resumen": {
                    "type": "string",
                    "description": (
                        "Resumen breve (3-6 líneas) del caso: qué campaña o "
                        "servicio le interesa, contexto relevante de su "
                        "negocio o situación, y cualquier dato que Jorge "
                        "deba saber antes de la llamada."
                    ),
                },
            },
            "required": ["inicio_iso", "resumen"],
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
        resultado = calendario.crear_evento(
            input_["inicio_iso"], nombre_cliente, sender, input_["resumen"]
        )
        if resultado["ok"]:
            # Se registra en la DB en vez de avisar por WhatsApp al momento --
            # un mensaje "empujado" por el bot choca con la ventana de 24h de
            # Meta (solo se puede mandar texto libre si el dueño le escribió
            # al bot en las últimas 24h). En vez de eso, Jorge consulta el
            # resumen del día escribiéndole "RESUMEN DEL DÍA" al bot (ver
            # app.py), lo cual sí cae dentro de esa ventana porque lo inicia él.
            try:
                from db import registrar_cita
                registrar_cita(
                    cuenta["id"], conversacion_id, sender, nombre_cliente,
                    input_["inicio_iso"], input_["resumen"],
                )
            except Exception as e:
                print(f"Error registrando cita en la base de datos: {e}", flush=True)
        return resultado

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
