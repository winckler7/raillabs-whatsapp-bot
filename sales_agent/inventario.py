"""Cliente de la API de inventario de solo lectura del sitio de Inmobiliaria
(repo winckler7/inmobiliaria, ruta /api/inventario/<herramienta>). Se usa
solo en el perfil "inmobiliaria" (ver perfil.py): así, si dan de alta,
cambian o venden una casa en el admin del sitio, el bot lo sabe al instante
sin copiar el inventario aquí."""

import json
import os

import requests

HERRAMIENTAS = {"buscar_propiedades", "ver_propiedad", "enviar_fotos"}


def consultar(herramienta, input_):
    """Regresa (resultado, imagenes). resultado es el dict que devolvió la
    herramienta en el sitio; imagenes es la lista [{url, caption}] que
    enviar_fotos pidió mandar (vacía para las demás)."""
    try:
        response = requests.post(
            f"{os.environ['INVENTARIO_API_URL'].rstrip('/')}/api/inventario/{herramienta}",
            headers={"Authorization": f"Bearer {os.environ['INVENTARIO_API_TOKEN']}"},
            json=input_,
            timeout=15,
        )
        response.raise_for_status()
        datos = response.json()
        return json.loads(datos["resultado"]), datos.get("imagenes") or []
    except Exception as e:
        print(f"Error consultando el inventario ({herramienta}): {e}", flush=True)
        return {"error": "No se pudo consultar el inventario en este momento."}, []
