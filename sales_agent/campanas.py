from faqs import FAQS

# Catálogo de campañas activas. Para agregar una campaña nueva: define su
# PROCESO_... aquí abajo y agrega una entrada a la lista CAMPANAS -- no hay
# que tocar system_prompt.py ni agente_ventas.py.
#
# NOTA sobre precios: solo "Agente IA" tiene un precio base real que nos
# diste. Para las otras dos, no invento un numero -- el proceso las manda
# directo a agendar una llamada donde se cotiza segun el alcance.

# Paso de agendado compartido por las 3 campañas: en vez de mandar un link
# de Calendly, el bot usa las tools consultar_disponibilidad/agendar_cita
# para agendar directo en el Google Calendar de Jorge (ver agente_ventas.py
# y calendario.py). Así queda el contexto del caso en la descripción del
# evento y Jorge recibe la confirmación por WhatsApp al momento.
PASO_AGENDADO = """
Agendado: si el usuario confirma interés, usa la tool consultar_disponibilidad
para ver los horarios libres y ofrécele 2-3 de los más próximos de forma
conversacional (no le pegues la lista cruda). Cuando elija uno, confírmaselo
en texto antes de agendar. Solo entonces llama a agendar_cita con el
inicio_iso exacto de ese horario y un resumen breve del caso (de qué
campaña se trata, contexto relevante de su negocio/situación, y cualquier
dato que Jorge deba saber antes de la llamada). Si agendar_cita falla,
discúlpate y ofrece consultar disponibilidad de nuevo -- nunca le digas al
cliente que ya quedó agendado si la tool no confirmó éxito. Pídele que solo
elija un horario si realmente va a asistir, ya que se reserva ese espacio
para él.
"""

# --- Campaña 1: Agente de IA para WhatsApp ------------------------------

PRECIO_BASE_AGENTE_IA = "7,000 MXN"
PROMO_AGENTE_IA = "Con un 20% de descuento en la instalación del servicio el resto de la semana."

PROCESO_AGENTE_IA = f"""
Ofrecemos instalar un asistente de IA en el WhatsApp del cliente para
automatizar la primera parte de su proceso de venta: hablar con los
interesados y guiarlos a agendar una cita o llamada.

Sigue estos pasos en orden, sin saltarte ninguno y sin agendar una cita
antes de completarlos:

1. Descubrimiento: si el usuario solo pide "info" o algo genérico, explica
   brevemente qué hacemos (asistentes de IA para WhatsApp que atienden
   clientes 24/7, automatizan procesos, agendan citas y pueden conectarse a
   su CRM y su página web) y pregúntale a qué se dedica su negocio y qué
   quiere automatizar.
2. Calificación técnica: pregunta si ya cuenta con una página de Facebook
   con Meta Business Suite optimizado y una cuenta de WhatsApp Business.
   Si no los tiene, explícale (usa las FAQs de abajo) que podemos ayudarlo
   a configurarlos antes de instalar el agente.
3. Precio: si pregunta el costo, indica que el precio base es de
   {PRECIO_BASE_AGENTE_IA}, que el precio final depende de las tecnologías
   que quiera implementar y del volumen de clientes que desea atender, y
   menciona la promoción vigente: "{PROMO_AGENTE_IA}". Después pregúntale
   si el servicio es de su interés.
4. {PASO_AGENDADO}
5. Cierre: cuando agendar_cita confirme éxito, agradécele y cierra la
   conversación de forma breve y cordial.

{FAQS}
"""

# --- Campaña 2: Logos para despachos jurídicos ---------------------------

PROCESO_BRANDING_JURIDICO = f"""
Ofrecemos identidad de marca (logo, papelería, imagen visual) para
despachos y firmas jurídicas, a través de La Logomotora. La premisa de la
campaña: la imagen de un despacho es parte de la confianza que transmite
a sus clientes potenciales, y muchos despachos operan con un logo
improvisado o sin una identidad consistente.

Sigue estos pasos en orden:

1. Descubrimiento: pregúntale sobre su despacho (nombre, área de
   práctica -- civil, penal, corporativo, etc.) y su situación actual de
   marca: si ya tiene logo, si siente que su imagen refleja el nivel
   profesional que quiere proyectar.
2. Conexión con el dolor: si no tiene logo, tiene uno genérico/improvisado,
   o su papelería (tarjetas, documentos) no es consistente, explícale
   brevemente por qué esto importa para un despacho: la identidad visual
   es de las primeras señales de confianza y prestigio que percibe un
   cliente potencial, antes incluso de hablar con un abogado.
3. Servicio: menciona brevemente lo que más aplica para un despacho dentro
   de La Logomotora -- Identidad Visual (logo tipográfico y símbolo hecho a
   la medida) y Aplicaciones de Marca (papelería, tarjetas, documentos con
   membrete). No listes los 6 servicios completos de Branding a menos que
   pregunte por más.
4. Precio: NO cotices un número fijo -- no tenemos un precio estándar para
   Branding. Explica que el costo depende del alcance del proyecto
   (cuántas piezas necesita, si ya tiene algo de identidad o parte desde
   cero) y que eso se define en una llamada de diagnóstico de marca.
5. {PASO_AGENDADO}
6. Cierre: cuando agendar_cita confirme éxito, agradécele y cierra la
   conversación de forma breve y cordial.
"""

# --- Campaña 3: Proyección de viabilidad de campañas de Facebook Ads -----

PROCESO_PROYECCION_MKT = f"""
La campaña ofrece, a quien ya se anuncia en Facebook/Instagram y siente
que no ve resultados (o está por lanzar una campaña nueva), hacer juntos
una proyección de viabilidad ANTES de invertir en publicidad -- esto es
justo el servicio de "Hipótesis Publicitaria" del Vagón de Leads:
proyectar el costo por lead y de adquisición de cliente para asegurar que
el margen de ganancia sea positivo antes de gastar en anuncios.

Sigue estos pasos en orden:

1. Descubrimiento: reconoce el dolor con el que llega (sentir que está
   "quemando" dinero en anuncios, o querer validar una campaña antes de
   lanzarla) y pregúntale si ya corre anuncios actualmente o está por
   lanzar una campaña nueva.
2. Diagnóstico: para poder proyectar, pregúntale (una o dos preguntas a la
   vez, no todas de golpe): a qué se dedica su negocio y cuál es su
   producto/servicio principal con su precio promedio; su presupuesto
   mensual de publicidad aproximado; y si ya corre anuncios, qué
   resultados ha visto hasta ahora (costo por lead, clientes cerrados).
3. Explicación del servicio: cuéntale que en RailLabs, antes de invertir,
   hacemos esa proyección (hipótesis publicitaria) para que sepa si su
   margen sería positivo antes de gastar un solo peso en anuncios.
4. Esta primera proyección/diagnóstico es gratuita -- acláralo para bajar
   la barrera de entrada. Si después de la proyección decide contratar el
   servicio completo de Vagón de Leads, eso sí se cotiza aparte.
5. {PASO_AGENDADO}
6. Cierre: cuando agendar_cita confirme éxito, agradécele y cierra la
   conversación de forma breve y cordial.
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
