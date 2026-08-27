# Configuracion compartida entre campañas.

# Zona horaria y horarios en los que Jorge acepta llamadas agendadas por el
# bot. Cada tupla de VENTANAS_HORARIO es (hora_inicio, minuto_inicio,
# hora_fin, minuto_fin) en formato 24h.
TIMEZONE = "America/Mexico_City"
VENTANAS_HORARIO = [(9, 0, 11, 0), (17, 0, 18, 0)]
DIAS_HABILES = {0, 1, 2, 3, 4}  # lunes(0) a viernes(4), datetime.weekday()

# Duración real de la llamada es 30 min, pero se bloquean 45 en el
# calendario para dejar colchón entre citas consecutivas.
DURACION_CITA_MINUTOS = 45

# Cuántos días naturales adelante se buscan huecos libres.
DIAS_A_CONSULTAR = 14
