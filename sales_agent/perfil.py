# Perfil con el que contesta el número de WhatsApp. "raillabs" es el bot de
# siempre; "inmobiliaria" convierte temporalmente el número en el demo del
# asistente para inmobiliarias (raillabs.co/inmobiliarias), con el
# inventario en vivo del sitio de Inmobiliaria. Para regresar a RailLabs
# basta con quitar PERFIL_AGENTE en Railway (o ponerlo en "raillabs") -- el
# código de RailLabs no se toca, y el estado previo quedó en el tag de git
# raillabs-antes-demo-inmobiliaria.
import os

PERFIL = os.environ.get("PERFIL_AGENTE", "raillabs").strip().lower()
ES_INMOBILIARIA = PERFIL == "inmobiliaria"

# Nombre de la inmobiliaria ficticia del demo -- igual que SITE_NAME en el
# sitio de Inmobiliaria, para que el cliente vea la misma marca en ambos.
NOMBRE_INMOBILIARIA = os.environ.get("DEMO_INMOBILIARIA_NOMBRE", "Inmobiliaria Demo")
NOMBRE_ASISTENTE_INMOBILIARIA = os.environ.get("DEMO_INMOBILIARIA_ASISTENTE", "Ray")
