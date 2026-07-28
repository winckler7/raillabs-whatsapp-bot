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


def get_historial(telefono):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT historial FROM conversaciones WHERE telefono = %s", (telefono,)
        )
        row = cur.fetchone()
        return row[0] if row else []


def guardar_historial(telefono, historial):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO conversaciones (telefono, historial)
            VALUES (%s, %s)
            ON CONFLICT (telefono)
            DO UPDATE SET historial = EXCLUDED.historial, ultimo_mensaje = now()
            """,
            (telefono, Json(historial)),
        )
