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


def get_or_create_conversacion(cuenta_id, telefono):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM conversaciones WHERE cuenta_id = %s AND telefono = %s",
            (cuenta_id, telefono),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO conversaciones (cuenta_id, telefono) VALUES (%s, %s) RETURNING id",
            (cuenta_id, telefono),
        )
        return cur.fetchone()[0]


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
