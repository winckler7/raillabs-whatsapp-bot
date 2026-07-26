#Load env variables
from dotenv import load_dotenv

load_dotenv()

#Create an API Client
from anthropic import Anthropic
from system_prompt import SYSTEM_PROMPT

client = Anthropic()
model = "claude-sonnet-5"


def add_user_message(messages, text):
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


def add_assistant_message(messages, text):
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)


def chat(messages):
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
        messages=messages,
        system=SYSTEM_PROMPT,
    )

    # Buscamos el bloque de texto en vez de asumir que está en la posición 0,
    # por si en algún momento se vuelve a activar thinking.
    for block in message.content:
        if block.type == "text":
            return block.text
    return ""


def simular_chat_whatsapp():
    """Simula la conversación por consola. Cuando se conecte la API real de
    WhatsApp Business, esta función se reemplaza por el webhook que recibe
    el mensaje entrante y llama a chat(messages) igual que aquí."""
    messages = []

    print("Simulador de chat de WhatsApp con el asistente de RailLabs.")
    print("Escribe 'salir' para terminar.\n")

    while True:
        user_input = input("Tú: ")
        if user_input.strip().lower() == "salir":
            break

        add_user_message(messages, user_input)
        response = chat(messages)
        add_assistant_message(messages, response)

        print(f"\nRailLabs: {response}\n")


if __name__ == "__main__":
    simular_chat_whatsapp()
