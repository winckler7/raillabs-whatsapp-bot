"""Envío de correos por Resend cuando se agenda, cancela o reagenda una
cita: aviso al cliente (si dio su correo) y aviso a Jorge en cada caso. A
diferencia de WhatsApp, el correo no tiene ventana de 24h, así que el
aviso a Jorge se manda al instante en vez de esperar a que él escriba
"RESUMEN DEL DÍA" (ver app.py)."""

import os

import resend

from perfil import ES_INMOBILIARIA, NOMBRE_INMOBILIARIA

# En el perfil inmobiliaria (demo, ver perfil.py) la cita es una visita con
# un asesor, no una llamada con Jorge -- solo cambian los textos.
if ES_INMOBILIARIA:
    CITA = "visita"
    CITA_CON = f"visita con un asesor de {NOMBRE_INMOBILIARIA}"
    MOTIVO = "Inmueble y lo que buscas"
    MOTIVO_DUENO = "Inmueble y lo que busca"
    OBJETIVO = "Forma de pago y plazo"
else:
    CITA = "llamada"
    CITA_CON = "llamada con Jorge de RailLabs"
    MOTIVO = "Motivo de la llamada"
    MOTIVO_DUENO = "Motivo de la llamada"
    OBJETIVO = "Tu objetivo"


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
        f"Confirmación de tu {CITA_CON}",
        (
            f"<p>Hola {nombre_cliente},</p>"
            f"<p>Quedó agendada tu {CITA_CON} para "
            f"<strong>{texto_fecha}</strong> (hora de Ciudad de México).</p>"
            f"<p>Esto es lo que nuestro asistente de IA entendió de tu "
            f"situación en automático:</p>"
            f"<p><strong>{MOTIVO}:</strong> {contexto_actual}</p>"
            f"<p><strong>{OBJETIVO}:</strong> {objetivo_cliente}</p>"
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
            f"<p><strong>Nueva {CITA} agendada por el asistente.</strong></p>"
            f"<p>Para: {nombre_cliente}</p>"
            f"<p>Hora de la {CITA}: {texto_fecha}</p>"
            f"<p>Número de teléfono: {telefono_cliente}</p>"
            f"{linea_correo}"
            f"<p>{MOTIVO_DUENO}: {contexto_actual}</p>"
            f"<p>{OBJETIVO}: {objetivo_cliente}</p>"
        ),
    )


def enviar_cancelacion_cliente(correo_cliente, nombre_cliente, texto_fecha):
    return _enviar(
        correo_cliente,
        f"Tu {CITA} quedó cancelada",
        (
            f"<p>Hola {nombre_cliente},</p>"
            f"<p>Confirmamos que cancelamos tu {CITA_CON} "
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
        f"Tu {CITA} cambió de horario",
        (
            f"<p>Hola {nombre_cliente},</p>"
            f"<p>Movimos tu {CITA_CON} de {texto_fecha_anterior} "
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


def enviar_aviso_asesor(nombre_cliente, telefono_cliente, resumen):
    """El asistente pasó la conversación a un humano (tool pasar_con_asesor):
    el bot ya no contesta a este cliente hasta que lo regresen a modo bot
    desde el panel."""
    owner_email = os.environ.get("OWNER_EMAIL")
    if not owner_email:
        return
    nombre = nombre_cliente or "Cliente de WhatsApp"
    _enviar(
        owner_email,
        f"Un cliente quiere hablar con un asesor: {nombre}",
        (
            f"<p><strong>El asistente pasó esta conversación a un asesor.</strong> "
            f"Contéstale desde el panel; el bot ya no le responde.</p>"
            f"<p>Cliente: {nombre}</p>"
            f"<p>Número de teléfono: {telefono_cliente}</p>"
            f"<p>Resumen: {resumen}</p>"
        ),
    )


def enviar_solicitud_visita(nombre_cliente, telefono_cliente, resumen):
    """El prospecto aceptó la visita (tool solicitar_visita, perfil
    inmobiliaria): el asesor le llama para acordar día y hora."""
    owner_email = os.environ.get("OWNER_EMAIL")
    if not owner_email:
        return
    nombre = nombre_cliente or "Cliente de WhatsApp"
    resumen_html = resumen.replace("\n", "<br>")
    _enviar(
        owner_email,
        f"Llamar para agendar visita: {nombre}",
        (
            f"<p><strong>{nombre} quiere conocer un inmueble.</strong> "
            f"Llámale para acordar el día y la hora de la visita.</p>"
            f"<p>Número de teléfono: {telefono_cliente}</p>"
            f"<p>{resumen_html}</p>"
        ),
    )
