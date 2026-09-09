import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import Json

ZONA_NEGOCIO = ZoneInfo("America/Mexico_City")

DATABASE_URL = os.environ["DATABASE_URL"]


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversaciones (
                telefono TEXT PRIMARY KEY,
                historial JSONB NOT NULL DEFAULT '[]',
                primer_contacto TIMESTAMPTZ NOT NULL DEFAULT now(),
                ultimo_mensaje TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mensajes_procesados (
                message_id TEXT PRIMARY KEY,
                procesado_en TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS citas (
                id SERIAL PRIMARY KEY,
                cuenta_id INTEGER NOT NULL REFERENCES cuentas(id) ON DELETE CASCADE,
                conversacion_id INTEGER REFERENCES conversaciones(id) ON DELETE SET NULL,
                telefono TEXT NOT NULL,
                nombre_cliente TEXT,
                correo TEXT,
                inicio TIMESTAMPTZ NOT NULL,
                resumen TEXT NOT NULL,
                creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        # ALTER de respaldo para cuando la tabla ya existía antes de agregar
        # `correo` (CREATE TABLE IF NOT EXISTS de arriba no la actualiza).
        cur.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS correo TEXT")
        # `google_event_id` para poder cancelar/reagendar el evento después,
        # y `cancelada_en` para marcar cancelaciones sin borrar el registro.
        cur.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS google_event_id TEXT")
        cur.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS cancelada_en TIMESTAMPTZ")


def ya_procesado(message_id):
    # Meta puede reentregar el mismo webhook (ej. si nuestro servidor fallo
    # la primera vez) -- sin esto, cada reentrega se responde como si fuera
    # un mensaje nuevo. Inserta el id y regresa True solo si ya existia.
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO mensajes_procesados (message_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (message_id,),
        )
        return cur.rowcount == 0


def get_cuenta_by_phone_number_id(phone_number_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, nombre_cliente, phone_number_id, whatsapp_token, verify_token, waba_id
            FROM cuentas
            WHERE phone_number_id = %s AND activo = true
            """,
            (phone_number_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "nombre_cliente": row[1],
            "phone_number_id": row[2],
            "whatsapp_token": row[3],
            "verify_token": row[4],
            "waba_id": row[5],
        }


def get_cuenta_by_id(cuenta_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, nombre_cliente, phone_number_id, whatsapp_token FROM cuentas WHERE id = %s",
            (cuenta_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "nombre_cliente": row[1],
            "phone_number_id": row[2],
            "whatsapp_token": row[3],
        }


def listar_cuentas():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, nombre_cliente FROM cuentas WHERE activo = true ORDER BY nombre_cliente"
        )
        return [{"id": r[0], "nombre_cliente": r[1]} for r in cur.fetchall()]


def get_or_create_conversacion(cuenta_id, telefono):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, estado, modo FROM conversaciones WHERE cuenta_id = %s AND telefono = %s",
            (cuenta_id, telefono),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                INSERT INTO conversaciones (cuenta_id, telefono)
                VALUES (%s, %s)
                RETURNING id, estado, modo
                """,
                (cuenta_id, telefono),
            )
            row = cur.fetchone()
        return {"id": row[0], "estado": row[1], "modo": row[2]}


def get_conversacion(conversacion_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, cuenta_id, telefono, estado, modo, notas, nombre, archivada,
                   primer_contacto, ultimo_mensaje
            FROM conversaciones WHERE id = %s
            """,
            (conversacion_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        columnas = [
            "id", "cuenta_id", "telefono", "estado", "modo", "notas", "nombre", "archivada",
            "primer_contacto", "ultimo_mensaje",
        ]
        detalle = dict(zip(columnas, row))
        detalle["etiquetas"] = get_etiquetas_conversacion(conversacion_id)
        return detalle


def listar_conversaciones(cuenta_id, archivadas=False):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                c.id, c.telefono, c.estado, c.modo, c.nombre, c.ultimo_mensaje, c.archivada,
                (
                    SELECT contenido FROM mensajes m
                    WHERE m.conversacion_id = c.id
                    ORDER BY m.id DESC LIMIT 1
                ) AS ultimo_texto,
                (
                    SELECT count(*) FROM mensajes m
                    WHERE m.conversacion_id = c.id
                      AND m.direccion = 'entrante'
                      AND (c.visto_en IS NULL OR m.creado_en > c.visto_en)
                ) AS no_leidos,
                COALESCE((
                    SELECT json_agg(json_build_object('id', e.id, 'nombre', e.nombre, 'color', e.color))
                    FROM conversacion_etiquetas ce JOIN etiquetas e ON e.id = ce.etiqueta_id
                    WHERE ce.conversacion_id = c.id
                ), '[]') AS etiquetas
            FROM conversaciones c
            WHERE c.cuenta_id = %s AND c.archivada = %s
            ORDER BY c.ultimo_mensaje DESC
            """,
            (cuenta_id, archivadas),
        )
        columnas = [
            "id", "telefono", "estado", "modo", "nombre", "ultimo_mensaje", "archivada",
            "ultimo_texto", "no_leidos", "etiquetas",
        ]
        return [dict(zip(columnas, row)) for row in cur.fetchall()]


def get_mensajes(conversacion_id, after_id=None):
    with get_conn() as conn, conn.cursor() as cur:
        condicion = "AND id > %s" if after_id else ""
        params = (conversacion_id, after_id) if after_id else (conversacion_id,)
        cur.execute(
            f"""
            SELECT m.id, m.direccion, m.tipo, m.contenido, m.estado_entrega, m.creado_en,
                   EXISTS(SELECT 1 FROM medios med WHERE med.mensaje_id = m.id) AS tiene_media
            FROM mensajes m WHERE conversacion_id = %s {condicion}
            ORDER BY id ASC
            """,
            params,
        )
        columnas = [
            "id", "direccion", "tipo", "contenido", "estado_entrega", "creado_en", "tiene_media",
        ]
        return [dict(zip(columnas, row)) for row in cur.fetchall()]


def get_estados_salientes(conversacion_id, limit=30):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, estado_entrega FROM mensajes
            WHERE conversacion_id = %s AND direccion = 'saliente'
            ORDER BY id DESC LIMIT %s
            """,
            (conversacion_id, limit),
        )
        return {r[0]: r[1] for r in cur.fetchall()}


RANGO_ESTADO_ENTREGA = {"enviado": 1, "entregado": 2, "leido": 3}
TRADUCCION_ESTADO_META = {
    "sent": "enviado",
    "delivered": "entregado",
    "read": "leido",
    "failed": "fallido",
}


def actualizar_estado_entrega(wa_message_id, estado_meta):
    # Meta puede reentregar el mismo status varias veces, y a veces fuera de
    # orden -- no se baja de nivel (ej. no pisar "leido" con "entregado" si
    # llega tarde), salvo "fallido" que siempre se aplica.
    estado = TRADUCCION_ESTADO_META.get(estado_meta)
    if not estado or not wa_message_id:
        return
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, estado_entrega FROM mensajes WHERE wa_message_id = %s", (wa_message_id,)
        )
        row = cur.fetchone()
        if not row:
            return
        mensaje_id, actual = row
        if estado == "fallido" or RANGO_ESTADO_ENTREGA.get(estado, 0) >= RANGO_ESTADO_ENTREGA.get(actual, 0):
            cur.execute("UPDATE mensajes SET estado_entrega = %s WHERE id = %s", (estado, mensaje_id))


def registrar_mensaje_con_media(
    conversacion_id, direccion, contenido, tipo, media_bytes, mime_type, wa_message_id=None
):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO mensajes (conversacion_id, direccion, tipo, contenido, wa_message_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (conversacion_id, direccion, tipo, contenido, wa_message_id),
        )
        mensaje_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO medios (mensaje_id, mime_type, contenido) VALUES (%s, %s, %s)",
            (mensaje_id, mime_type, psycopg2.Binary(media_bytes)),
        )
        return mensaje_id


def get_media(mensaje_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT mime_type, contenido FROM medios WHERE mensaje_id = %s", (mensaje_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {"mime_type": row[0], "contenido": bytes(row[1])}


def set_archivada(conversacion_id, archivada):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE conversaciones SET archivada = %s WHERE id = %s", (archivada, conversacion_id)
        )


def listar_plantillas(cuenta_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, texto FROM plantillas WHERE cuenta_id = %s ORDER BY orden, id", (cuenta_id,)
        )
        return [{"id": r[0], "texto": r[1]} for r in cur.fetchall()]


def crear_plantilla(cuenta_id, texto):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO plantillas (cuenta_id, texto) VALUES (%s, %s) RETURNING id",
            (cuenta_id, texto),
        )
        return cur.fetchone()[0]


def borrar_plantilla(plantilla_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM plantillas WHERE id = %s", (plantilla_id,))


def listar_etiquetas(cuenta_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, nombre, color FROM etiquetas WHERE cuenta_id = %s ORDER BY nombre",
            (cuenta_id,),
        )
        return [{"id": r[0], "nombre": r[1], "color": r[2]} for r in cur.fetchall()]


def crear_etiqueta(cuenta_id, nombre, color="#667781"):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO etiquetas (cuenta_id, nombre, color) VALUES (%s, %s, %s)
            ON CONFLICT (cuenta_id, nombre) DO UPDATE SET color = EXCLUDED.color
            RETURNING id
            """,
            (cuenta_id, nombre, color),
        )
        return cur.fetchone()[0]


def borrar_etiqueta(etiqueta_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM etiquetas WHERE id = %s", (etiqueta_id,))


def get_etiquetas_conversacion(conversacion_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.id, e.nombre, e.color FROM etiquetas e
            JOIN conversacion_etiquetas ce ON ce.etiqueta_id = e.id
            WHERE ce.conversacion_id = %s
            ORDER BY e.nombre
            """,
            (conversacion_id,),
        )
        return [{"id": r[0], "nombre": r[1], "color": r[2]} for r in cur.fetchall()]


def set_etiquetas_conversacion(conversacion_id, etiqueta_ids):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM conversacion_etiquetas WHERE conversacion_id = %s", (conversacion_id,))
        for etiqueta_id in etiqueta_ids:
            cur.execute(
                "INSERT INTO conversacion_etiquetas (conversacion_id, etiqueta_id) VALUES (%s, %s)",
                (conversacion_id, etiqueta_id),
            )


def marcar_visto(conversacion_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE conversaciones SET visto_en = now() WHERE id = %s", (conversacion_id,)
        )


def set_estado(conversacion_id, estado):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE conversaciones SET estado = %s WHERE id = %s", (estado, conversacion_id)
        )


def set_modo(conversacion_id, modo):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE conversaciones SET modo = %s WHERE id = %s", (modo, conversacion_id)
        )


def set_nombre(conversacion_id, nombre):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE conversaciones SET nombre = %s WHERE id = %s", (nombre, conversacion_id)
        )


def set_nombre_automatico(conversacion_id, nombre):
    # Se llama con el nombre de perfil que manda WhatsApp en cada mensaje --
    # solo lo guarda si todavía no hay uno (para no pisar una edición manual
    # hecha desde el panel).
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE conversaciones SET nombre = %s WHERE id = %s AND nombre IS NULL",
            (nombre, conversacion_id),
        )


def set_notas(conversacion_id, notas):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE conversaciones SET notas = %s WHERE id = %s", (notas, conversacion_id)
        )


def registrar_mensaje(conversacion_id, direccion, contenido, wa_message_id=None, tipo="texto"):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO mensajes (conversacion_id, direccion, tipo, contenido, wa_message_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (conversacion_id, direccion, tipo, contenido, wa_message_id),
        )


def get_historial(cuenta_id, telefono):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT historial FROM conversaciones WHERE cuenta_id = %s AND telefono = %s",
            (cuenta_id, telefono),
        )
        row = cur.fetchone()
        return row[0] if row else []


def guardar_historial(cuenta_id, telefono, historial):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO conversaciones (cuenta_id, telefono, historial)
            VALUES (%s, %s, %s)
            ON CONFLICT (cuenta_id, telefono)
            DO UPDATE SET historial = EXCLUDED.historial, ultimo_mensaje = now()
            """,
            (cuenta_id, telefono, Json(historial)),
        )


def borrar_historial(cuenta_id, telefono):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM conversaciones WHERE cuenta_id = %s AND telefono = %s",
            (cuenta_id, telefono),
        )
        return cur.rowcount > 0


def registrar_cita(cuenta_id, conversacion_id, telefono, nombre_cliente, inicio, resumen, correo=None, google_event_id=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO citas (cuenta_id, conversacion_id, telefono, nombre_cliente, correo, inicio, resumen, google_event_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (cuenta_id, conversacion_id, telefono, nombre_cliente, correo, inicio, resumen, google_event_id),
        )


def obtener_cita_activa(cuenta_id, telefono):
    """La próxima cita futura y no cancelada de este cliente, si tiene una."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, nombre_cliente, correo, inicio, resumen, google_event_id
            FROM citas
            WHERE cuenta_id = %s AND telefono = %s
              AND cancelada_en IS NULL AND inicio > now()
            ORDER BY inicio ASC
            LIMIT 1
            """,
            (cuenta_id, telefono),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0], "nombre_cliente": row[1], "correo": row[2],
            "inicio": row[3], "resumen": row[4], "google_event_id": row[5],
        }


def marcar_cita_cancelada(cita_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE citas SET cancelada_en = now() WHERE id = %s", (cita_id,))


def actualizar_cita_reagendada(cita_id, nuevo_inicio, nuevo_google_event_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE citas SET inicio = %s, google_event_id = %s WHERE id = %s",
            (nuevo_inicio, nuevo_google_event_id, cita_id),
        )


def resumen_del_dia(cuenta_id):
    # "Hoy" se calcula en hora de Ciudad de México, no en la del servidor
    # (Railway corre en UTC) -- si no, un contacto de las 7pm en CDMX podría
    # contarse en el día equivocado.
    ahora = datetime.now(ZONA_NEGOCIO)
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_dia = inicio_dia + timedelta(days=1)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*) FROM conversaciones
            WHERE cuenta_id = %s AND primer_contacto >= %s AND primer_contacto < %s
            """,
            (cuenta_id, inicio_dia, fin_dia),
        )
        contactos_nuevos = cur.fetchone()[0]

        cur.execute(
            """
            SELECT telefono, nombre_cliente, correo, inicio, resumen FROM citas
            WHERE cuenta_id = %s AND creado_en >= %s AND creado_en < %s
              AND cancelada_en IS NULL
            ORDER BY inicio
            """,
            (cuenta_id, inicio_dia, fin_dia),
        )
        citas = [
            {"telefono": r[0], "nombre_cliente": r[1], "correo": r[2], "inicio": r[3], "resumen": r[4]}
            for r in cur.fetchall()
        ]

    return {"contactos_nuevos": contactos_nuevos, "citas": citas}
