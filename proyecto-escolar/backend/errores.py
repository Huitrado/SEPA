"""RF-04: mensajes de error específicos y en español para los datos inválidos."""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_FIJOS = {
    "missing": "Este campo es obligatorio",
    "int_parsing": "Debe ser un número entero",
    "float_parsing": "Debe ser un número",
    "string_type": "Debe ser texto",
    "literal_error": "El valor no está permitido",
    "time_parsing": "Hora inválida; usa el formato HH:MM",
    "date_parsing": "Fecha inválida; usa el formato AAAA-MM-DD",
    "string_pattern_mismatch": "El formato del campo no es válido",
    "too_short": "Debe incluir al menos un elemento",
    "greater_than_equal": "El valor es demasiado bajo",
    "json_invalid": "El cuerpo de la petición no es un JSON válido",
}

def _traducir(e: dict) -> str:
    tipo, msg, ctx = e["type"], e["msg"], e.get("ctx") or {}
    if tipo == "string_too_short":
        minimo = ctx.get("min_length")
        return "Este campo es obligatorio" if minimo == 1 else f"Debe tener al menos {minimo} caracteres"
    if tipo == "too_short" and isinstance(e.get("input"), str):
        minimo = ctx.get("min_length")
        return "Este campo es obligatorio" if minimo == 1 else f"Debe tener al menos {minimo} caracteres"
    if tipo == "string_too_long":
        return f"Debe tener máximo {ctx.get('max_length')} caracteres"
    if tipo == "value_error":
        if msg.startswith("value is not a valid email address"):
            return "El correo electrónico no tiene un formato válido"
        return msg.removeprefix("Value error, ")
    return _FIJOS.get(tipo, msg)

async def errores_de_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
    errores = [{"campo": ".".join(str(p) for p in e["loc"][1:]) or "general",
                "mensaje": _traducir(e)} for e in exc.errors()]
    return JSONResponse(status_code=422,
                        content={"detail": "Hay datos inválidos en la solicitud", "errores": errores})
