"""Integración con Google Calendar para agendar citas directo desde el bot.

Usa una cuenta de servicio (service account) de Google: el calendario del
dueño se comparte con el email de esa cuenta de servicio (permiso "hacer
cambios en eventos"), y desde ahí el bot puede consultar disponibilidad y
crear eventos sin que nadie tenga que iniciar sesión ni renovar tokens.
"""

import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import (
    TIMEZONE,
    VENTANAS_HORARIO,
    DIAS_HABILES,
    DURACION_CITA_MINUTOS,
    DIAS_A_CONSULTAR,
)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
ZONA = ZoneInfo(TIMEZONE)


def _servicio():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    credenciales = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("calendar", "v3", credentials=credenciales)


def _calendar_id():
    return os.environ["GOOGLE_CALENDAR_ID"]


def _rango_busqueda():
    # Ventana de búsqueda: desde ahora hasta DIAS_A_CONSULTAR días naturales
    # adelante (alcanza de sobra para juntar varios días hábiles con huecos).
    ahora = datetime.now(ZONA)
    return ahora, ahora + timedelta(days=DIAS_A_CONSULTAR)


def _periodos_ocupados(servicio, inicio, fin):
    respuesta = servicio.freebusy().query(
        body={
            "timeMin": inicio.isoformat(),
            "timeMax": fin.isoformat(),
            "timeZone": TIMEZONE,
            "items": [{"id": _calendar_id()}],
        }
    ).execute()
    ocupados = respuesta["calendars"][_calendar_id()]["busy"]
    return [
        (datetime.fromisoformat(p["start"]), datetime.fromisoformat(p["end"]))
        for p in ocupados
    ]


def _se_traslapa(inicio_slot, fin_slot, ocupados):
    return any(inicio_slot < fin and fin_slot > inicio for inicio, fin in ocupados)


def _generar_slots(ocupados, limite=6):
    ahora = datetime.now(ZONA)
    # Solo ofrecemos horarios con al menos 2 horas de anticipación -- agendar
    # "en 10 minutos" no le da tiempo a nadie de prepararse para la llamada.
    minimo = ahora + timedelta(hours=2)
    duracion = timedelta(minutes=DURACION_CITA_MINUTOS)

    slots = []
    dia = ahora.date()
    dias_revisados = 0
    while len(slots) < limite and dias_revisados < DIAS_A_CONSULTAR:
        fecha = datetime.combine(dia, datetime.min.time(), tzinfo=ZONA)
        if fecha.weekday() in DIAS_HABILES:
            for hora_inicio, minuto_inicio, hora_fin, minuto_fin in VENTANAS_HORARIO:
                ventana_inicio = fecha.replace(hour=hora_inicio, minute=minuto_inicio)
                ventana_fin = fecha.replace(hour=hora_fin, minute=minuto_fin)
                cursor = ventana_inicio
                while cursor + duracion <= ventana_fin and len(slots) < limite:
                    if cursor >= minimo and not _se_traslapa(cursor, cursor + duracion, ocupados):
                        slots.append(cursor)
                    cursor += duracion
        dia += timedelta(days=1)
        dias_revisados += 1
    return slots


DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def formato_legible(momento):
    dia_semana = DIAS_ES[momento.weekday()]
    mes = MESES_ES[momento.month - 1]
    hora_12 = momento.strftime("%I:%M %p").lstrip("0").lower()
    return f"{dia_semana} {momento.day} de {mes}, {hora_12}"


def consultar_disponibilidad():
    """Regresa los próximos horarios libres dentro de las ventanas definidas
    en config.py. Cada slot trae el ISO exacto (para usarlo tal cual al
    llamar crear_evento) y un texto legible en español para mostrarle al
    cliente."""
    try:
        servicio = _servicio()
        inicio, fin = _rango_busqueda()
        ocupados = _periodos_ocupados(servicio, inicio, fin)
        slots = _generar_slots(ocupados)
    except Exception as e:
        print(f"Error consultando disponibilidad de Google Calendar: {e}", flush=True)
        return {"ok": False, "error": "No se pudo consultar el calendario en este momento."}

    return {
        "ok": True,
        "horarios": [
            {"inicio_iso": s.isoformat(), "texto": formato_legible(s)}
            for s in slots
        ],
    }


def crear_evento(inicio_iso, nombre_cliente, telefono_cliente, resumen, correo_cliente=None):
    """Crea el evento en Google Calendar. Antes de insertarlo vuelve a
    checar que el horario siga libre (evita choques si dos clientes eligen
    el mismo slot casi al mismo tiempo). Si el cliente dio su correo, lo
    agrega como invitado -- Google le manda la invitación automáticamente,
    sin que nosotros mandemos ningún correo directo."""
    try:
        inicio = datetime.fromisoformat(inicio_iso)
    except ValueError:
        return {"ok": False, "error": "inicio_iso inválido, debe ser el ISO exacto que devolvió consultar_disponibilidad."}

    fin = inicio + timedelta(minutes=DURACION_CITA_MINUTOS)

    try:
        servicio = _servicio()
        ocupados = _periodos_ocupados(servicio, inicio - timedelta(minutes=1), fin + timedelta(minutes=1))
        if _se_traslapa(inicio, fin, ocupados):
            return {"ok": False, "error": "Ese horario ya se ocupó, hay que elegir otro de la lista actualizada."}

        evento = {
            "summary": f"Llamada RailLabs - {nombre_cliente}",
            "description": (
                f"Cliente: {nombre_cliente}\n"
                f"WhatsApp: {telefono_cliente}\n\n"
                f"Resumen del caso:\n{resumen}"
            ),
            "start": {"dateTime": inicio.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": fin.isoformat(), "timeZone": TIMEZONE},
        }

        correo_enviado = False
        if correo_cliente:
            evento["attendees"] = [{"email": correo_cliente}]
            try:
                servicio.events().insert(
                    calendarId=_calendar_id(), body=evento, sendUpdates="all"
                ).execute()
                correo_enviado = True
            except Exception as e:
                # Algunas cuentas de servicio no pueden invitar asistentes sin
                # "delegación de dominio" (solo existe en Google Workspace, no
                # en Gmail personal) -- si falla por eso, se agenda igual pero
                # sin el invitado, para no perder la cita por esto.
                print(f"No se pudo invitar al cliente por correo, se agenda sin invitado: {e}", flush=True)
                del evento["attendees"]
                servicio.events().insert(calendarId=_calendar_id(), body=evento).execute()
        else:
            servicio.events().insert(calendarId=_calendar_id(), body=evento).execute()
    except Exception as e:
        print(f"Error creando evento en Google Calendar: {e}", flush=True)
        return {"ok": False, "error": "No se pudo agendar en el calendario en este momento."}

    return {"ok": True, "texto": formato_legible(inicio), "correo_enviado": correo_enviado}
