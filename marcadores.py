"""Marcadores internos de etapa del embudo ([[ETAPA:...]]) que el modelo
agrega a sus respuestas. Nunca deben llegar al cliente: este módulo los
detecta y los quita en cualquier posición del texto y con cualquier variante
razonable de formato (el modelo a veces los pone a mitad del mensaje, con un
solo corchete, en minúsculas, o cortados si se queda sin tokens).
"""
import re

ORDEN_ETAPAS = ["situacion_actual", "situacion_deseada", "propuesta_cita"]

_MARCADOR = re.compile(r"[ \t]*\[{1,2}\s*ETAPA\s*:\s*([A-Za-z_]+)\s*\]{1,2}[ \t]*", re.IGNORECASE)
_MARCADOR_CORTADO = re.compile(r"[ \t]*\[{1,2}\s*ETAPA\b[^\]]*\Z|[ \t]*\[\[\s*\Z", re.IGNORECASE)


def limpiar_marcadores(texto):
    if not texto:
        return texto
    # Se reemplaza por un espacio (no por "") para que las palabras vecinas
    # no se peguen cuando el marcador va en medio de una línea.
    texto = _MARCADOR.sub(" ", texto)
    texto = _MARCADOR_CORTADO.sub("", texto)
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    texto = re.sub(r"[ \t]+\n", "\n", texto)
    texto = re.sub(r"\n[ \t]+", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def separar_etapa(texto):
    """Regresa (texto_limpio, etapa). Si hay varios marcadores válidos se
    queda con el más avanzado; los inválidos se descartan sin error."""
    encontradas = [m.group(1).lower() for m in _MARCADOR.finditer(texto or "")]
    validas = [e for e in encontradas if e in ORDEN_ETAPAS]
    etapa = max(validas, key=ORDEN_ETAPAS.index) if validas else None
    return limpiar_marcadores(texto), etapa
