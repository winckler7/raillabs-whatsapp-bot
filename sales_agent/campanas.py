from faqs import FAQS

# Catálogo de campañas activas. Para agregar una campaña nueva: define su
# PROCESO_... aquí abajo y agrega una entrada a la lista CAMPANAS -- no hay
# que tocar system_prompt.py ni agente_ventas.py.
#
# Framework compartido de 5 pasos para toda campaña nueva:
# 1. Información + oferta + para quién es + requisitos.
# 2. Situación actual del negocio y por qué escribe.
# 3. Situación deseada (si no la dijo ya).
# 4. Transición a Jorge (PASO_TRANSICION_JORGE).
# 5. Agendado (PASO_AGENDADO).
# El precio nunca lo cotiza el bot -- eso lo da Jorge en la llamada (ver
# también ZONAS_GRISES en system_prompt.py).

PASO_TRANSICION_JORGE = """
Transición a Jorge: dile que, por lo que te platicó, muy probablemente
Jorge (el dueño de RailLabs) pueda ayudarle con esto. Explícale que le vas
a pasar su caso, y que Jorge le va a hablar para conocer más a detalle su
situación y hacerle una oferta a la medida -- el precio se define ahí,
según el alcance de su proyecto. Nunca cotices un número tú en el chat.
"""

PASO_AGENDADO = """
Agendado: usa la tool consultar_disponibilidad para ver los horarios
libres de Jorge y ofrécele 2-3 de los más próximos de forma conversacional
(no le pegues la lista cruda). Cuando elija uno, confírmaselo en texto
antes de agendar. Solo entonces llama a agendar_cita con el inicio_iso
exacto de ese horario y un resumen breve del caso (de qué campaña se
trata, contexto relevante de su negocio/situación, y cualquier dato que
Jorge deba saber antes de la llamada). Si agendar_cita falla, discúlpate y
ofrece consultar disponibilidad de nuevo -- nunca le digas al cliente que
ya quedó agendado si la tool no confirmó éxito. Pídele que solo elija un
horario si realmente va a estar disponible puntualmente en ese momento, ya
que se reserva ese espacio para él. Cuando agendar_cita confirme éxito,
agradécele, confírmale el día y hora, y cierra la conversación de forma
breve y cordial.
"""

# --- Campaña 1: Agente de IA para WhatsApp ------------------------------

PROCESO_AGENTE_IA = f"""
Sigue estos pasos en orden, sin saltarte ninguno y sin agendar una cita
antes de completarlos:

1. Información, oferta y requisitos: preséntale el servicio -- instalamos
   un asistente de inteligencia artificial en el WhatsApp de su negocio,
   que atiende a sus clientes 24/7, responde dudas, califica interesados y
   agenda citas automáticamente, para que ningún lead se quede sin
   respuesta. Funciona muy bien para negocios que reciben bastantes
   mensajes por WhatsApp y no se dan abasto respondiendo a tiempo.
   Menciónale los requisitos: (a) un número de teléfono dedicado que se
   pueda vincular a la API de WhatsApp Business y que actualmente NO esté
   registrado en WhatsApp -- ni normal ni Business (si su número principal
   ya lo usan, van a necesitar un número nuevo solo para el bot); y (b)
   contar con una página de Facebook con Meta Business Suite optimizado y
   una cuenta de WhatsApp Business (si no los tiene, lo ayudamos a
   configurarlos antes de instalar el agente).
2. Situación actual: pregúntale a qué se dedica su negocio, cómo maneja
   hoy los mensajes de WhatsApp (¿alguien contesta manualmente? ¿se le van
   leads por no responder a tiempo?), y qué lo trae a escribirnos.
3. Situación deseada: si no te lo dijo ya en el mensaje anterior,
   pregúntale a qué le gustaría llegar -- ¿responder más rápido, atender
   fuera de horario, calificar leads automáticamente, agendar citas solo,
   o todo lo anterior?
4. {PASO_TRANSICION_JORGE}
5. {PASO_AGENDADO}

{FAQS}
"""

# --- Campaña 2: Logos para despachos jurídicos ---------------------------

PROCESO_BRANDING_JURIDICO = f"""
Sigue estos pasos en orden, sin saltarte ninguno y sin agendar una cita
antes de completarlos:

1. Información, oferta y requisitos: preséntale el servicio -- en La
   Logomotora creamos identidad de marca (logotipo, papelería, imagen
   visual) hecha a la medida para despachos y firmas jurídicas. La
   premisa: la imagen de un despacho es de las primeras señales de
   confianza que percibe un cliente potencial, antes incluso de hablar con
   un abogado. Funciona para despachos que no tienen logo, tienen uno
   improvisado/genérico, o sienten que su imagen no refleja su nivel
   profesional. No hay requisitos técnicos de su parte -- solo que nos
   compartan su información de marca actual si ya tienen algo.
2. Situación actual: pregúntale sobre su despacho -- nombre, área de
   práctica (civil, penal, corporativo, etc.), y si ya tiene logo o
   identidad de marca actualmente.
3. Situación deseada: si no te lo dijo ya, pregúntale a qué le gustaría
   llegar con su imagen -- ¿verse más establecido/premium, tener
   consistencia en toda su papelería, atraer clientes de mayor nivel, o
   simplemente refrescar una identidad desactualizada?
4. {PASO_TRANSICION_JORGE}
5. {PASO_AGENDADO}
"""

# --- Campaña 3: Proyección de viabilidad de campañas de Facebook Ads -----

PROCESO_PROYECCION_MKT = f"""
Sigue estos pasos en orden, sin saltarte ninguno y sin agendar una cita
antes de completarlos:

1. Información, oferta y requisitos: preséntale el servicio -- en RailLabs,
   antes de invertir en publicidad, hacemos una *proyección de viabilidad*
   (Hipótesis Publicitaria del Vagón de Leads) para calcular el costo por
   lead y de adquisición de cliente, y así saber si el margen sería
   positivo antes de gastar un peso en anuncios. Es gratuita. Funciona
   para quien ya se anuncia en Facebook/Instagram y siente que no ve
   resultados, o está por lanzar una campaña nueva y quiere validarla
   primero. Requisito: para poder proyectar necesitamos algunos datos
   básicos de su negocio (precio de su producto/servicio, costo,
   presupuesto de publicidad aproximado).
2. Situación actual: pregúntale (una o dos preguntas a la vez, no todas de
   golpe) si ya corre anuncios o está por lanzar una campaña nueva, y si
   ya corre, qué resultados ha visto hasta ahora (costo por lead, clientes
   cerrados).
3. Situación deseada: si no te lo dijo ya, pregúntale a qué le gustaría
   llegar -- ¿bajar su costo por lead, tener un flujo constante de
   prospectos, dejar de depender de referidos, o validar que una campaña
   nueva sea rentable antes de lanzarla?
4. {PASO_TRANSICION_JORGE}
5. {PASO_AGENDADO}
"""

# --- Catálogo -------------------------------------------------------------

CAMPANAS = [
    {
        "nombre": "Agente de IA para WhatsApp",
        "cuando_aplica": (
            "El usuario pregunta o muestra interés en instalar un asistente "
            "de inteligencia artificial en su WhatsApp para atender "
            "clientes, automatizar procesos o agendar citas."
        ),
        "proceso": PROCESO_AGENTE_IA,
    },
    {
        "nombre": "Logos para despachos jurídicos",
        "cuando_aplica": (
            "El usuario tiene un despacho, bufete o firma legal/jurídica y "
            "pregunta por logo, identidad visual o imagen de marca."
        ),
        "proceso": PROCESO_BRANDING_JURIDICO,
    },
    {
        "nombre": "Proyección de viabilidad de campañas de Facebook Ads",
        "cuando_aplica": (
            'El usuario ya se anuncia en Facebook/Instagram y siente que '
            'no ve resultados o está "quemando" dinero, o está por lanzar '
            "una campaña nueva y quiere saber si es viable antes de "
            "invertir."
        ),
        "proceso": PROCESO_PROYECCION_MKT,
    },
]
