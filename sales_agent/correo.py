"""Envío de correos por Resend cuando se agenda una cita: confirmación al
cliente (si dio su correo) y aviso a Jorge de cada cita nueva. A diferencia
de WhatsApp, el correo no tiene ventana de 24h, así que el aviso a Jorge se
manda al instante en vez de esperar a que él escriba "RESUMEN DEL DÍA"
(ver app.py)."""

import os

import resend


def _api_key_configurada():
    return bool(os.environ.get("RESEND_API_KEY"))


def _from():
    return os.environ["RESEND_FROM_EMAIL"]


def enviar_confirmacion_cliente(correo_cliente, nombre_cliente, texto_fecha):
    """Manda la confirmación de la cita al cliente. Devuelve True/False según
    si se pudo mandar -- el bot usa esto para avisarle o no que revise su
    correo, sin que un error aquí tumbe el flujo de agendado."""
    if not _api_key_configurada():
        return False
    try:
        resend.api_key = os.environ["RESEND_API_KEY"]
        resend.Emails.send({
            "from": _from(),
            "to": [correo_cliente],
            "subject": "Confirmación de tu llamada con RailLabs",
            "html": (
                f"<p>Hola {nombre_cliente},</p>"
                f"<p>Quedó agendada tu llamada con Jorge de RailLabs para "
                f"<strong>{texto_fecha}</strong> (hora de Ciudad de México).</p>"
                f"<p>Cualquier cosa, respóndenos por este medio o por WhatsApp.</p>"
            ),
        })
        return True
    except Exception as e:
        print(f"Error mandando confirmación por correo al cliente: {e}", flush=True)
        return False


def enviar_aviso_dueno(nombre_cliente, telefono_cliente, correo_cliente, texto_fecha, contexto_actual, objetivo_cliente):
    """Avisa a Jorge por correo de cada cita nueva, apenas se agenda."""
    owner_email = os.environ.get("OWNER_EMAIL")
    if not _api_key_configurada() or not owner_email:
        return
    try:
        linea_correo = f"<p>Correo: {correo_cliente}</p>" if correo_cliente else ""
        resend.api_key = os.environ["RESEND_API_KEY"]
        resend.Emails.send({
            "from": _from(),
            "to": [owner_email],
            "subject": f"Nueva cita: {nombre_cliente} -- {texto_fecha}",
            "html": (
                f"<p><strong>Invitación agendada para llamada telefónica con Jorge.</strong></p>"
                f"<p>Para: {nombre_cliente}</p>"
                f"<p>Hora de la llamada: {texto_fecha}</p>"
                f"<p>Número de teléfono: {telefono_cliente}</p>"
                f"{linea_correo}"
                f"<p>Contexto de motivo de la llamada o situación actual: {contexto_actual}</p>"
                f"<p>Objetivo del cliente o situación deseada: {objetivo_cliente}</p>"
            ),
        })
    except Exception as e:
        print(f"Error avisando a Jorge por correo de la cita nueva: {e}", flush=True)
