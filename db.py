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
