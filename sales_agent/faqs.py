# Respuestas ya redactadas y listas para usarse casi textual en el chat --
# el "panel de notas" de un community manager, pero para el bot. A
# diferencia de MENU_SERVICIOS (conocimiento interno que hay que
# parafrasear), lo de aquí SÍ se puede responder casi tal cual cuando el
# cliente pregunta justo eso (ver regla en REGLAS_GENERALES).
#
# Organizado por cada uno de los 6 servicios del saludo inicial
# (SALUDO_INICIAL en system_prompt.py). Jorge: si una pregunta se repite
# mucho y no está aquí, agrégala en la sección del servicio que le
# corresponda -- así el bot no tiene que improvisar la respuesta.

FAQS_BRANDING = """
FAQS -- Branding e identidad visual (La Logomotora):

P: ¿Qué pasa si necesito modificar un asset o corregir un error?
R: Comunicación directa por WhatsApp; se resuelve en máximo 24-48 horas.

P: Somos varios en la empresa, ¿personalizan la papelería para cada
   colaborador?
R: Sí, sin costo extra.

P: ¿Qué pasa si me urge un entregable?
R: Se puede priorizar sin sacrificar calidad, avisando con tiempo.

P: Somos varios tomadores de decisiones, ¿cómo hacemos para que el
   trabajo le guste a todos?
R: No se diseña sobre gustos sino sobre objetivos comerciales -- si
   cumple el objetivo, todos ganan, más allá de preferencias personales.

P: ¿Qué pasa si el branding no trae los resultados esperados?
R: El problema puede estar en la oferta, el proceso de ventas u otras
   áreas -- hay acceso a una consulta estratégica para diagnosticar.

P: ¿Cómo sé en qué etapa va mi proyecto?
R: Cronograma compartido en tiempo real con todas las actualizaciones.

P: ¿Qué pasa si necesito ayuda post-entrega (por ejemplo dónde imprimir
   mis tarjetas)?
R: Especificaciones en el manual de marca, más soporte por WhatsApp.
"""

# Motion Graphics se vende dentro de La Logomotora (es el servicio #4 de
# SERVICIOS INCLUIDOS en MENU_SERVICIOS), así que las FAQs de Branding de
# arriba también le aplican. Espacio para preguntas específicas de
# animación cuando empiecen a repetirse -- por ahora no hay ninguna.
FAQS_MOTION_GRAPHICS = """
FAQS -- Animaciones Motion Graphics:

[Jorge: agrega aquí preguntas específicas de motion graphics conforme te
las vayan haciendo. Mientras tanto, las FAQs de Branding de arriba cubren
lo general del proceso (tiempos, revisiones, entregables).]
"""

FAQS_PUBLICIDAD = """
FAQS -- Publicidad con proyección de resultados (El Vagón de Leads):

P: ¿Qué pasa si no consigo la cantidad de prospectos que quiero?
R: Se define una proyección realista antes de empezar; si no se cumple,
   RailLabs sigue trabajando e incluso puede cubrir el gasto publicitario
   faltante.

P: ¿Qué pasa si gasto más en publicidad de lo que gano en ventas?
R: Por eso existe la hipótesis publicitaria previa, calculando el costo
   de adquisición para que el margen siempre sea positivo.

P: ¿Qué pasa si hay errores en los anuncios?
R: Se revisan con el cliente antes de publicar; si hay error después, se
   resuelve por WhatsApp en máximo 24-48 horas.

P: ¿Qué pasa si tengo muchos leads pero sigo sin vender?
R: Puede ser un problema de comunicación, oferta, administración o
   proceso de ventas -- hay acceso a una videollamada estratégica para
   diagnosticar y corregir.

P: ¿Qué pasa si no sé cómo comunicarme con mis prospectos por WhatsApp?
R: El community manager crea una guía de respuestas para encaminar cada
   tipo de pregunta hacia la venta.

P: ¿Qué pasa si no sé vender?
R: RailLabs enseña -- se puede crear un guión de venta por llamada o un
   workshop de mejores prácticas de cierre.
"""

FAQS_CONTENIDO = """
FAQS -- Creación de Contenidos:

P: ¿Tengo que salir en los videos de mi marca?
R: Se recomienda, pero si la estrategia lo requiere RailLabs puede hacer
   voice-over o salir a cámara en representación del cliente.

[Jorge: agrega aquí más preguntas específicas de contenido (formatos,
cantidad de piezas al mes, quién graba, etc.) conforme te las vayan
haciendo.]
"""

FAQS_TECNOLOGIA_WEB = """
FAQS -- Tecnologías como aplicaciones y páginas web (El Expreso Web):

P: ¿Cómo sé que la página va a quedar como quiero?
R: Se hace un diseño web profesional completo, presentado y revisado con
   el cliente antes de programar.

P: ¿Qué pasa si hay un bug urgente?
R: Soporte por WhatsApp, resuelto en máximo 36 horas.

P: ¿Pueden hacer modificaciones después de entregar?
R: Sí, la mensualidad incluye un fee para agregar funcionalidades nuevas
   y mejorar el sitio cada mes.

P: ¿Cómo sé si mi página me está dando resultados?
R: Cada mes se entregan métricas de visitas y eventos registrados.

P: ¿Puedo conseguir clientes a través de mi página?
R: Sí, con estrategias de SEO, SEM y pauta en redes integradas al
   proyecto.

P: ¿Qué pasa si me urge tener la página?
R: Se puede lanzar una versión base para tener presencia digital activa
   y agregar funcionalidades restantes de forma gradual.
"""

FAQS_ASISTENTE_IA = """
FAQS -- Asistentes de WhatsApp automatizados con Inteligencia Artificial:

P: ¿Cuánto cuesta el asistente de IA / el chatbot?
R: El precio se da a partir de una cotización, ya que cada negocio necesita
integraciones distintas para que el asistente funcione bien con su
proceso -- por ejemplo, no es lo mismo un negocio que agenda citas que uno
que vende por catálogo.

Lo que sí es fijo es la base de instalación de $10,000 MXN, que incluye:
✅ Ingeniería de prompting a la medida de tu negocio
✅ Conexión de tu número de WhatsApp al asistente de IA
✅ Panel para contestar manual cuando quieras y ver el historial de tus
   clientes
✅ Infraestructura y hosting, sin que tengas que administrar nada técnico
✅ Resumen diario de tu actividad

Sobre esa base se suman las integraciones que tu negocio en particular
necesite. Cuéntame un poco de tu negocio y te ayudo a ver qué necesitarías.

P: ¿Y la mensualidad, cuánto es?
R: La mensualidad cubre el hosting, el uso de la infraestructura de IA, y
el mantenimiento y mejora continua de las plantillas de conversación de tu
asistente -- el monto exacto se define con Jorge en la llamada, según las
integraciones que tengas.

Si el cliente insiste por un número exacto/cerrado (aplica tanto a la
instalación como a la mensualidad), usa esta respuesta -- y OJO: nunca la
uses como cierre de la conversación, siempre debe llevar al siguiente
paso del framework de descubrimiento (pregúntale de qué se trata su
negocio si todavía no lo sabes):
R: Entiendo que quieras un número concreto, pero honestamente no te podría
dar un precio final sin conocer tu caso primero -- cada negocio necesita
cosas distintas (agendado, catálogo, CRM, etc.) y eso es justo lo que
cambia el precio. Para poder cotizarte bien necesito saber un poco de cómo
funciona tu negocio hoy. ¿Me cuentas a qué te dedicas y cómo manejas tus
clientes por WhatsApp actualmente?

P: ¿Qué es Meta Business Suite y por qué lo necesito?
R: Es la plataforma de Meta donde administras tu página de Facebook,
Instagram y WhatsApp Business en un solo lugar. La necesitamos porque ahí
es donde se conecta el agente de IA para poder leer y responder tus
mensajes.

P: ¿Qué diferencia hay entre WhatsApp normal y WhatsApp Business?
R: WhatsApp Business es la versión para empresas de Meta, con catálogo,
respuestas automáticas y, sobre todo, la API que permite conectar
herramientas externas como nuestro agente de IA. WhatsApp normal no lo
permite.

P: ¿El agente puede acceder a mi CRM?
R: Sí, contamos con integraciones para conectar el agente a CRMs populares
(por ejemplo HubSpot, Pipedrive o uno a la medida) para que registre leads
y actualice el estado de cada conversación automáticamente.

P: ¿El agente puede tomar información de mi página web?
R: Sí, podemos entrenarlo con el contenido de tu sitio (servicios,
precios, preguntas frecuentes) para que responda con información
específica de tu negocio y no solo de forma genérica.

P: ¿Cuánto tarda la implementación?
R: Depende de la cantidad de integraciones que se necesiten, pero un
agente básico conectado a WhatsApp Business suele estar listo en pocos
días hábiles.

P: ¿El agente reemplaza por completo a una persona?
R: Automatiza la primera parte del proceso: atender, calificar y agendar.
Las llamadas y el cierre de venta los sigue haciendo tu equipo humano -- el
agente les ahorra el tiempo de contestar uno por uno.

P: ¿Funciona las 24 horas?
R: Sí, el agente está disponible todo el tiempo, incluyendo fines de
semana y fuera de horario laboral, para que ningún interesado se quede sin
respuesta.

P: ¿Es seguro? ¿Qué pasa con los datos de mis clientes?
R: La conversación se maneja a través de la infraestructura oficial de
Meta para WhatsApp Business, y los datos que el agente recopila (nombre,
interés, disponibilidad) solo se usan para el proceso de venta y agendado.

P: ¿Puedo usar el número de WhatsApp que ya tengo?
R: No -- la API de WhatsApp Business necesita un número que no esté
registrado en WhatsApp (ni normal ni Business) al momento de conectarlo.
Si tu número actual ya lo usas para hablar con clientes, vas a necesitar
un número nuevo dedicado para el bot -- te ayudamos a configurarlo.

P: No tengo página de Facebook ni WhatsApp Business todavía, ¿qué hago?
R: No hay problema, podemos ayudarte a configurarlos desde cero antes de
instalar el agente -- es un paso previo que también acompañamos.

P: ¿Puede manejar varias conversaciones al mismo tiempo?
R: Sí, esa es una de las ventajas principales: puede atender a todos tus
interesados en simultáneo, sin filas de espera.
"""

FAQS = (
    FAQS_BRANDING
    + FAQS_MOTION_GRAPHICS
    + FAQS_PUBLICIDAD
    + FAQS_CONTENIDO
    + FAQS_TECNOLOGIA_WEB
    + FAQS_ASISTENTE_IA
)
