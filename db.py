import os

import psycopg2
from psycopg2.extras import Json

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
            SELECT id, cuenta_id, telefono, estado, modo, notas, nombre, primer_contacto, ultimo_mensaje
            FROM conversaciones WHERE id = %s
            """,
            (conversacion_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        columnas = [
            "id", "cuenta_id", "telefono", "estado", "modo", "notas", "nombre",
            "primer_contacto", "ultimo_mensaje",
        ]
        return dict(zip(columnas, row))


def listar_conversaciones(cuenta_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                c.id, c.telefono, c.estado, c.modo, c.nombre, c.ultimo_mensaje,
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
                ) AS no_leidos
            FROM conversaciones c
            WHERE c.cuenta_id = %s
            ORDER BY c.ultimo_mensaje DESC
            """,
            (cuenta_id,),
        )
        columnas = [
            "id", "telefono", "estado", "modo", "nombre", "ultimo_mensaje",
            "ultimo_texto", "no_leidos",
        ]
        return [dict(zip(columnas, row)) for row in cur.fetchall()]


def get_mensajes(conversacion_id, after_id=None):
    with get_conn() as conn, conn.cursor() as cur:
        if after_id:
            cur.execute(
                """
                SELECT id, direccion, tipo, contenido, estado_entrega, creado_en
                FROM mensajes WHERE conversacion_id = %s AND id > %s
                ORDER BY id ASC
                """,
                (conversacion_id, after_id),
            )
        else:
            cur.execute(
                """
                SELECT id, direccion, tipo, contenido, estado_entrega, creado_en
                FROM mensajes WHERE conversacion_id = %s
                ORDER BY id ASC
                """,
                (conversacion_id,),
            )
        columnas = ["id", "direccion", "tipo", "contenido", "estado_entrega", "creado_en"]
        return [dict(zip(columnas, row)) for row in cur.fetchall()]


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
