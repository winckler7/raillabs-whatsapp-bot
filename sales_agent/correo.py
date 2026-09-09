"""Envío de correos por Resend cuando se agenda, cancela o reagenda una
cita: aviso al cliente (si dio su correo) y aviso a Jorge en cada caso. A
diferencia de WhatsApp, el correo no tiene ventana de 24h, así que el
aviso a Jorge se manda al instante en vez de esperar a que él escriba
"RESUMEN DEL DÍA" (ver app.py)."""

import os

import resend


def _api_key_configurada():
    return bool(os.environ.get("RESEND_API_KEY"))


def _from():
    return os.environ["RESEND_FROM_EMAIL"]


def _enviar(to, subject, html):
    """Devuelve True/False según si se pudo mandar -- un error aquí nunca
    debe tumbar el flujo de agendado/cancelación/reagendado."""
    if not _api_key_configurada():
        return False
    try:
        resend.api_key = os.environ["RESEND_API_KEY"]
        resend.Emails.send({"from": _from(), "to": [to], "subject": subject, "html": html})
        return True
    except Exception as e:
        print(f"Error mandando correo a {to}: {e}", flush=True)
        return False


def enviar_confirmacion_cliente(correo_cliente, nombre_cliente, texto_fecha, contexto_actual, objetivo_cliente):
    """Incluye lo que el asistente de IA entendió de la situación del
    cliente -- funciona como demo en vivo del producto (el bot mismo) sin
    que el cliente tenga que preguntar."""
    return _enviar(
        correo_cliente,
        "Confirmación de tu llamada con RailLabs",
        (
            f"<p>Hola {nombre_cliente},</p>"
            f"<p>Quedó agendada tu llamada con Jorge de RailLabs para "
            f"<strong>{texto_fecha}</strong> (hora de Ciudad de México).</p>"
            f"<p>Esto es lo que nuestro asistente de IA entendió de tu "
            f"situación en automático, antes de que Jorge te hable:</p>"
            f"<p><strong>Motivo de la llamada:</strong> {contexto_actual}</p>"
            f"<p><strong>Tu objetivo:</strong> {objetivo_cliente}</p>"
            f"<p>Cualquier cosa, respóndenos por este medio o por WhatsApp.</p>"
        ),
    )


def enviar_aviso_dueno(nombre_cliente, telefono_cliente, correo_cliente, texto_fecha, contexto_actual, objetivo_cliente):
    owner_email = os.environ.get("OWNER_EMAIL")
    if not owner_email:
        return
    linea_correo = f"<p>Correo: {correo_cliente}</p>" if correo_cliente else ""
    _enviar(
        owner_email,
        f"Nueva cita: {nombre_cliente} -- {texto_fecha}",
        (
            f"<p><strong>Invitación agendada para llamada telefónica con Jorge.</strong></p>"
            f"<p>Para: {nombre_cliente}</p>"
            f"<p>Hora de la llamada: {texto_fecha}</p>"
            f"<p>Número de teléfono: {telefono_cliente}</p>"
            f"{linea_correo}"
            f"<p>Motivo de la llamada: {contexto_actual}</p>"
            f"<p>Objetivo del cliente: {objetivo_cliente}</p>"
        ),
    )


def enviar_cancelacion_cliente(correo_cliente, nombre_cliente, texto_fecha):
    return _enviar(
        correo_cliente,
        "Tu llamada con RailLabs quedó cancelada",
        (
            f"<p>Hola {nombre_cliente},</p>"
            f"<p>Confirmamos que cancelamos tu llamada con Jorge de RailLabs "
            f"que estaba agendada para <strong>{texto_fecha}</strong>.</p>"
            f"<p>Si quieres agendar en otro momento, solo escríbenos por WhatsApp.</p>"
        ),
    )


def enviar_aviso_cancelacion_dueno(nombre_cliente, telefono_cliente, correo_cliente, texto_fecha):
    owner_email = os.environ.get("OWNER_EMAIL")
    if not owner_email:
        return
    linea_correo = f"<p>Correo: {correo_cliente}</p>" if correo_cliente else ""
    _enviar(
        owner_email,
        f"Cita cancelada: {nombre_cliente} -- {texto_fecha}",
        (
            f"<p><strong>Se canceló una cita agendada.</strong></p>"
            f"<p>Para: {nombre_cliente}</p>"
            f"<p>Hora que ya no aplica: {texto_fecha}</p>"
            f"<p>Número de teléfono: {telefono_cliente}</p>"
            f"{linea_correo}"
        ),
    )


def enviar_reagendo_cliente(correo_cliente, nombre_cliente, texto_fecha_anterior, texto_fecha_nueva):
    return _enviar(
        correo_cliente,
        "Tu llamada con RailLabs cambió de horario",
        (
            f"<p>Hola {nombre_cliente},</p>"
            f"<p>Movimos tu llamada con Jorge de RailLabs de {texto_fecha_anterior} "
            f"a <strong>{texto_fecha_nueva}</strong> (hora de Ciudad de México).</p>"
            f"<p>Cualquier cosa, respóndenos por este medio o por WhatsApp.</p>"
        ),
    )


def enviar_aviso_reagendo_dueno(nombre_cliente, telefono_cliente, correo_cliente, texto_fecha_anterior, texto_fecha_nueva):
    owner_email = os.environ.get("OWNER_EMAIL")
    if not owner_email:
        return
    linea_correo = f"<p>Correo: {correo_cliente}</p>" if correo_cliente else ""
    _enviar(
        owner_email,
        f"Cita reagendada: {nombre_cliente} -- {texto_fecha_nueva}",
        (
            f"<p><strong>Se movió una cita agendada.</strong></p>"
            f"<p>Para: {nombre_cliente}</p>"
            f"<p>Hora anterior: {texto_fecha_anterior}</p>"
            f"<p>Hora nueva: {texto_fecha_nueva}</p>"
            f"<p>Número de teléfono: {telefono_cliente}</p>"
            f"{linea_correo}"
        ),
    )
