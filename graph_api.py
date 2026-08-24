import os

import requests

GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v20.0")


def send_message(cuenta, to, body):
    # Envía un mensaje de texto saliente al usuario `to` vía la Graph API de
    # Meta, usando el token y phone_number_id de la cuenta correspondiente.
    # Compartido entre el webhook (app.py) y el envío manual del panel
    # (panel.py) para no duplicar esta lógica. Regresa el id que Meta le
    # asigna al mensaje, para poder cruzarlo después con los webhooks de
    # estado de entrega (sent/delivered/read).
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
    return response.json()["messages"][0]["id"]


def subir_media(cuenta, contenido_bytes, mime_type, filename):
    # Sube un archivo al servidor de media de Meta -- regresa un media_id
    # temporal que se usa para mandarlo en un mensaje (no es una URL pública).
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{cuenta['phone_number_id']}/media"
    headers = {"Authorization": f"Bearer {cuenta['whatsapp_token']}"}
    files = {"file": (filename, contenido_bytes, mime_type)}
    data = {"messaging_product": "whatsapp"}
    response = requests.post(url, headers=headers, files=files, data=data)
    if not response.ok:
        print("Error subiendo media a WhatsApp:", response.status_code, response.text, flush=True)
    response.raise_for_status()
    return response.json()["id"]


def enviar_media(cuenta, to, media_id, tipo):
    graph_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{cuenta['phone_number_id']}/messages"
    headers = {"Authorization": f"Bearer {cuenta['whatsapp_token']}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": tipo,
        tipo: {"id": media_id},
    }
    response = requests.post(graph_url, headers=headers, json=payload)
    if not response.ok:
        print("Error de WhatsApp API (media):", response.status_code, response.text, flush=True)
    response.raise_for_status()
    return response.json()["messages"][0]["id"]


def obtener_media_url(media_id, whatsapp_token):
    # El media_id que manda un webhook entrante no es descargable directo --
    # primero hay que resolverlo a una URL temporal (expira en minutos).
    response = requests.get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}",
        headers={"Authorization": f"Bearer {whatsapp_token}"},
    )
    response.raise_for_status()
    return response.json()["url"]


def descargar_media(url, whatsapp_token):
    # La URL temporal de Meta también exige el bearer token para descargar.
    response = requests.get(url, headers={"Authorization": f"Bearer {whatsapp_token}"})
    response.raise_for_status()
    return response.content, response.headers.get("Content-Type", "application/octet-stream")
