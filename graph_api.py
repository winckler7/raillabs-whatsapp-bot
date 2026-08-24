import os

import requests

GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v20.0")


def send_message(cuenta, to, body):
    # Envía un mensaje de texto saliente al usuario `to` vía la Graph API de
    # Meta, usando el token y phone_number_id de la cuenta correspondiente.
    # Compartido entre el webhook (app.py) y el envío manual del panel
    # (panel.py) para no duplicar esta lógica.
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
