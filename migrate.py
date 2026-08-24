"""Migración one-off: agrega soporte multi-tenant (tabla cuentas), mensajes
individuales y siembra la cuenta de RailLabs a partir de las env vars
actuales. Correr una sola vez en producción con:

    railway run python migrate.py

Es seguro re-correrlo si falla a medias (usa IF NOT EXISTS / ON CONFLICT /
chequeos de estado antes de cada paso destructivo).
"""
import os

import psycopg2

DATABASE_URL = os.environ["DATABASE_URL"]


def run():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            crear_cuentas_y_columnas(cur)
            cuenta_id = sembrar_cuenta_raillabs(cur)
            migrar_pk_conversaciones(cur, cuenta_id)
            crear_tabla_mensajes(cur)
            backfill_mensajes(cur)
            crear_tablas_fase3(cur)
        conn.commit()
        print(f"Migración completa. cuenta_id de RailLabs = {cuenta_id}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def crear_cuentas_y_columnas(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cuentas (
            id SERIAL PRIMARY KEY,
            nombre_cliente TEXT NOT NULL,
            phone_number_id TEXT NOT NULL UNIQUE,
            whatsapp_token TEXT NOT NULL,
            verify_token TEXT NOT NULL,
            waba_id TEXT,
            activo BOOLEAN NOT NULL DEFAULT true,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    cur.execute("ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS id SERIAL")
    cur.execute(
        "ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS cuenta_id INTEGER REFERENCES cuentas(id)"
    )
    cur.execute(
        "ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS estado TEXT NOT NULL DEFAULT 'abierta'"
    )
    cur.execute(
        "ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS modo TEXT NOT NULL DEFAULT 'bot'"
    )
    cur.execute("ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS notas TEXT")
    cur.execute("ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS visto_en TIMESTAMPTZ")
    cur.execute("ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS nombre TEXT")


def crear_tabla_mensajes(cur):
    # Se crea despues del swap de PK en conversaciones -- Postgres exige que
    # la columna referenciada (id) ya tenga PRIMARY KEY/UNIQUE antes de
    # poder crear un FK hacia ella.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS mensajes (
            id SERIAL PRIMARY KEY,
            conversacion_id INTEGER NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
            direccion TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'texto',
            contenido TEXT NOT NULL,
            wa_message_id TEXT,
            estado_entrega TEXT,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def sembrar_cuenta_raillabs(cur):
    phone_number_id = os.environ["PHONE_NUMBER_ID"]
    whatsapp_token = os.environ["WHATSAPP_TOKEN"]
    verify_token = os.environ["VERIFY_TOKEN"]
    cur.execute(
        """
        INSERT INTO cuentas (nombre_cliente, phone_number_id, whatsapp_token, verify_token)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (phone_number_id) DO UPDATE SET
            whatsapp_token = EXCLUDED.whatsapp_token,
            verify_token = EXCLUDED.verify_token
        RETURNING id
        """,
        ("RailLabs", phone_number_id, whatsapp_token, verify_token),
    )
    return cur.fetchone()[0]


def migrar_pk_conversaciones(cur, cuenta_id):
    # Todas las conversaciones existentes (creadas antes del multi-tenant)
    # pertenecen a la cuenta de RailLabs.
    cur.execute(
        "UPDATE conversaciones SET cuenta_id = %s WHERE cuenta_id IS NULL", (cuenta_id,)
    )
    cur.execute("ALTER TABLE conversaciones ALTER COLUMN cuenta_id SET NOT NULL")

    cur.execute(
        """
        SELECT a.attname FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = 'conversaciones'::regclass AND i.indisprimary
        """
    )
    columnas_pk = {r[0] for r in cur.fetchall()}
    if columnas_pk != {"id"}:
        cur.execute(
            """
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'conversaciones' AND constraint_type = 'PRIMARY KEY'
            """
        )
        pk_actual = cur.fetchone()[0]
        cur.execute(f"ALTER TABLE conversaciones DROP CONSTRAINT {pk_actual}")
        cur.execute("ALTER TABLE conversaciones ADD PRIMARY KEY (id)")

    cur.execute(
        "SELECT 1 FROM pg_constraint WHERE conname = 'conversaciones_cuenta_telefono_key'"
    )
    if not cur.fetchone():
        cur.execute(
            "ALTER TABLE conversaciones ADD CONSTRAINT conversaciones_cuenta_telefono_key "
            "UNIQUE (cuenta_id, telefono)"
        )


def backfill_mensajes(cur):
    # El JSONB no trae timestamp por mensaje individual, asi que se
    # interpolan entre primer_contacto y ultimo_mensaje para mantener el
    # orden correcto en el inbox (no son la hora exacta real de cada envio).
    cur.execute(
        """
        SELECT c.id, c.historial, c.primer_contacto, c.ultimo_mensaje
        FROM conversaciones c
        WHERE NOT EXISTS (SELECT 1 FROM mensajes m WHERE m.conversacion_id = c.id)
          AND jsonb_array_length(c.historial) > 0
        """
    )
    conversaciones = cur.fetchall()
    for conversacion_id, historial, inicio, fin in conversaciones:
        n = len(historial)
        for i, mensaje in enumerate(historial):
            direccion = "entrante" if mensaje.get("role") == "user" else "saliente"
            fraccion = i / (n - 1) if n > 1 else 0
            ts = inicio + (fin - inicio) * fraccion
            cur.execute(
                """
                INSERT INTO mensajes (conversacion_id, direccion, contenido, creado_en)
                VALUES (%s, %s, %s, %s)
                """,
                (conversacion_id, direccion, mensaje.get("content", ""), ts),
            )


def crear_tablas_fase3(cur):
    # Archivar, multimedia, respuestas rápidas y etiquetas/buzones -- todas
    # referencian tablas que ya tienen su PK definitiva desde antes, así que
    # no hay problema de orden como con `mensajes` en la migración original.
    cur.execute(
        "ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS archivada BOOLEAN NOT NULL DEFAULT false"
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS medios (
            id SERIAL PRIMARY KEY,
            mensaje_id INTEGER NOT NULL REFERENCES mensajes(id) ON DELETE CASCADE,
            mime_type TEXT NOT NULL,
            contenido BYTEA NOT NULL,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS plantillas (
            id SERIAL PRIMARY KEY,
            cuenta_id INTEGER NOT NULL REFERENCES cuentas(id) ON DELETE CASCADE,
            texto TEXT NOT NULL,
            orden INTEGER NOT NULL DEFAULT 0,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS etiquetas (
            id SERIAL PRIMARY KEY,
            cuenta_id INTEGER NOT NULL REFERENCES cuentas(id) ON DELETE CASCADE,
            nombre TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#667781',
            UNIQUE (cuenta_id, nombre)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversacion_etiquetas (
            conversacion_id INTEGER NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
            etiqueta_id INTEGER NOT NULL REFERENCES etiquetas(id) ON DELETE CASCADE,
            PRIMARY KEY (conversacion_id, etiqueta_id)
        )
        """
    )


if __name__ == "__main__":
    run()
