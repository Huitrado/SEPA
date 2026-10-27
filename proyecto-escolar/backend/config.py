import os
import re
from datetime import date

# Dominio del correo -> rol que se asigna automáticamente al registrarse
DOMINIOS_ROL = {
    "alumnos.udg.mx": "estudiante",
    "academicos.udg.mx": "docente",
}

# Mientras no se verifique que la persona sea dueña del correo, un docente que se
# registra queda "pendiente" hasta que un administrador lo apruebe.
# Para desactivarlo: variable de entorno DOCENTE_REQUIERE_APROBACION=0
DOCENTE_REQUIERE_APROBACION = os.getenv("DOCENTE_REQUIERE_APROBACION", "1") != "0"

# RF-18: calificación mínima aprobatoria, fija e inmodificable (sobre 100)
UMBRAL_APROBATORIO = 60.0

# RF-17: únicos tipos de evaluación permitidos (valor guardado -> etiqueta en pantalla)
TIPOS_EVALUACION = {
    "numerica": "Calificación Numérica",
    "aprobado_no_aprobado": "Aprobado/No Aprobado",
}

# RF-13: días permitidos, en orden de la semana
DIAS_SEMANA = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado")

# RF-90: si un usuario tiene varios roles, se le manda al panel de mayor prioridad
PRIORIDAD_PANEL = ("administrador", "docente", "estudiante")

# RF-02: carreras con las que arranca el catálogo (el administrador agrega el resto)
CARRERAS_INICIALES = {
    "ICOM": "Ingeniería en Computación",
    "INFO": "Ingeniería Informática",
}

# RF-07
MENSAJE_RECUPERACION = (
    "Si olvidaste tu contraseña, comunícate con tu coordinador de carrera o con un "
    "administrador institucional para solicitar el restablecimiento manual."
)

def rol_por_correo(correo: str) -> str | None:
    """Devuelve el rol según el dominio exacto del correo, o None si no es institucional."""
    if "@" not in correo:
        return None
    dominio = correo.rsplit("@", 1)[1].strip().lower()
    return DOMINIOS_ROL.get(dominio)

def dominio_de(rol: str) -> str:
    return next(d for d, r in DOMINIOS_ROL.items() if r == rol)

# Calendario institucional de ciclos escolares: letra -> ((mes, día) de inicio, (mes, día) de término)
CALENDARIO_CICLOS = {
    "A": ((1, 16), (7, 15)),    # 2026-A: del 16 de enero al 15 de julio
    "B": ((7, 16), (12, 16)),   # 2026-B: del 16 de julio al 16 de diciembre
}

def fechas_ciclo(nombre: str) -> tuple[date, date] | None:
    """Fechas oficiales de un ciclo a partir de su nombre ('2026-B'), o None si el nombre no es válido."""
    m = re.fullmatch(r"(\d{4})-([AB])", nombre.strip().upper())
    if not m:
        return None
    anio, letra = int(m[1]), m[2]
    (mi, di), (mt, dt) = CALENDARIO_CICLOS[letra]
    return date(anio, mi, di), date(anio, mt, dt)
