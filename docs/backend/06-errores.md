# 06 · Errores

[← Volver al índice](README.md)

Cuando algo sale mal, la API responde con un **código de estado HTTP** (un número que resume el resultado) y un JSON que explica qué pasó. Todos los mensajes que genera nuestro código están **en español** (RF-04).

## Los códigos que usamos

| Código | Nombre | Significado en SEPA | Lo genera |
|--------|--------|---------------------|-----------|
| **200** | OK | Todo bien | — |
| **201** | Created | Se creó algo (usuario, curso, inscripción…) | — |
| **401** | Unauthorized | **No sabemos quién eres**: no hay token, es inválido o expiró, la sesión se cerró o la cuenta no está activa. En el login: código o contraseña incorrectos | `security.py`, `services.py → iniciarSesion` |
| **403** | Forbidden | **Sabemos quién eres, pero no puedes hacer esto**: te falta el rol, el curso no es tuyo, o tu cuenta está pendiente o desactivada (al iniciar sesión) | `security.py`, `services.py` |
| **404** | Not Found | Lo que buscas no existe (curso, usuario, ciclo, código de curso) | `services.py`, `routers/catalogos.py` |
| **409** | Conflict | Lo que pides choca con el estado actual: duplicados, ciclo cerrado, curso archivado, cambiar tu propio estado | `services.py` |
| **422** | Unprocessable Content | Los datos enviados no son válidos | `errores.py` (validación) y `services.py` (reglas) |
| **500** | Internal Server Error | Falla del servidor | `services.py → crearCurso` (único caso explícito) o un error no previsto |

> **Regla práctica para el frontend:** con 401, manda al usuario a la pantalla de login. Con 403, muestra "no tienes permiso". Con 422, marca en rojo los campos.

## Dos formatos de respuesta

Todas las respuestas de error tienen la llave **`detail`**. Las de validación agregan una lista **`errores`**.

### Formato A: errores de validación (422 con `errores[]`)

Ocurren **antes** de que se ejecute el endpoint, cuando Pydantic rechaza el JSON, los parámetros de la ruta o los de consulta.

```json
{
  "detail": "Hay datos inválidos en la solicitud",
  "errores": [
    { "campo": "nombre", "mensaje": "Solo puede contener letras, espacios, apóstrofes y guiones" },
    { "campo": "correoInstitucional", "mensaje": "El correo electrónico no tiene un formato válido" }
  ]
}
```

- `campo`: dónde está el problema. Si la regla involucra varios campos (por ejemplo, que las contraseñas coincidan), vale `"general"`.
- `mensaje`: texto listo para mostrar al usuario.

### Formato B: errores lanzados con `HTTPException` (todos los demás)

Solo tienen `detail`:

```json
{ "detail": "El correo institucional ya está registrado" }
```

> **Importante:** algunos **422 usan el formato B**, porque no los genera Pydantic sino una regla de `services.py`. Son tres casos:
> - `La carrera seleccionada no pertenece al catálogo oficial` (`_validar_catalogos`)
> - `El ciclo en curso es 2026-B` (`_validar_catalogos`)
> - `La hora de fin debe ser posterior a la hora de inicio` (`actualizar_curso`, al editar un curso)
>
> Por eso el frontend debe leer **siempre `detail`** y, **si existe**, recorrer `errores`.

```js
const cuerpo = await respuesta.json();
mostrarAviso(cuerpo.detail);
for (const e of cuerpo.errores ?? []) marcarCampo(e.campo, e.mensaje);
```

---

## Dónde se generan los 422 de validación: `errores.py`

FastAPI trae su propio formato de errores, en inglés y difícil de mostrar. En `main.py` lo reemplazamos:

```python
app.add_exception_handler(RequestValidationError, errores_de_validacion)
```

Esto significa: "cuando ocurra un `RequestValidationError` (Pydantic rechazó la petición), en lugar de la respuesta por defecto llama a `errores_de_validacion`".

### `errores.py → errores_de_validacion`

```python
async def errores_de_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
    errores = [{"campo": ".".join(str(p) for p in e["loc"][1:]) or "general",
                "mensaje": _traducir(e)} for e in exc.errors()]
    return JSONResponse(status_code=422,
                        content={"detail": "Hay datos inválidos en la solicitud", "errores": errores})
```

- `exc.errors()` es la lista de errores que da Pydantic. Cada uno trae `type` (tipo de error), `loc` (ubicación), `msg` (mensaje en inglés) y a veces `ctx` (datos extra, como la longitud mínima).
- **Cómo se arma `campo`:** `loc` es algo como `("body", "nombre")`. Se quita el primer elemento, que dice si el dato venía en el cuerpo (`body`), la consulta (`query`) o la ruta (`path`), y el resto se une con puntos:
  - `("body", "nombre")` → `"nombre"`
  - `("body", "diasSemana", 0)` → `"diasSemana.0"` (el primer elemento de la lista)
  - `("query", "estado")` → `"estado"`
  - `("body",)` → vacío → `"general"` (errores de `@model_validator`)

### `errores.py → _traducir`

Convierte el tipo de error de Pydantic en un mensaje en español:

| Tipo de Pydantic | Mensaje |
|------------------|---------|
| `missing` | `Este campo es obligatorio` |
| `string_too_short` con mínimo 1 | `Este campo es obligatorio` |
| `string_too_short` con mínimo N | `Debe tener al menos N caracteres` |
| `string_too_long` | `Debe tener máximo N caracteres` |
| `int_parsing` | `Debe ser un número entero` |
| `float_parsing` | `Debe ser un número` |
| `string_type` | `Debe ser texto` |
| `literal_error` | `El valor no está permitido` |
| `time_parsing` | `Hora inválida; usa el formato HH:MM` |
| `date_parsing` | `Fecha inválida; usa el formato AAAA-MM-DD` |
| `string_pattern_mismatch` | `El formato del campo no es válido` |
| `too_short` (listas) | `Debe incluir al menos un elemento` |
| `greater_than_equal` | `El valor es demasiado bajo` |
| `json_invalid` | `El cuerpo de la petición no es un JSON válido` |
| `value_error` de correo | `El correo electrónico no tiene un formato válido` |
| `value_error` nuestro | El texto del `ValueError` que lanzamos en `schemas.py`, sin el prefijo `"Value error, "` |
| Cualquier otro | El mensaje original de Pydantic, en inglés |

Así, nuestros mensajes personalizados (los `raise ValueError("...")` de `schemas.py`) llegan tal cual al usuario.

---

## Un ejemplo de cada error

### 422 de validación: varios campos

`POST /usuarios/registro` con nombre con números, correo incompleto y contraseña corta:

```json
{
  "detail": "Hay datos inválidos en la solicitud",
  "errores": [
    { "campo": "nombre", "mensaje": "Solo puede contener letras, espacios, apóstrofes y guiones" },
    { "campo": "correoInstitucional", "mensaje": "El correo electrónico no tiene un formato válido" },
    { "campo": "contrasena", "mensaje": "La contraseña debe tener al menos 8 caracteres" }
  ]
}
```

### 422 de validación: regla de varios campos (`campo: "general"`)

`POST /usuarios/registro` con contraseñas distintas (`schemas.py → UsuarioCrear.validar_formulario`):

```json
{
  "detail": "Hay datos inválidos en la solicitud",
  "errores": [
    { "campo": "general", "mensaje": "La contraseña y su confirmación no coinciden" }
  ]
}
```

> Las reglas de `@model_validator` solo se revisan **si todos los campos individuales pasaron**. Si el nombre está mal **y** las contraseñas no coinciden, primero solo verás el error del nombre.

### 422 de validación: campos vacíos en el login

Este caso lo comprueba la prueba `test_rf04_campos_vacios_dan_mensaje_especifico`:

```json
{
  "detail": "Hay datos inválidos en la solicitud",
  "errores": [
    { "campo": "codigo", "mensaje": "Este campo es obligatorio" },
    { "campo": "contrasena", "mensaje": "Este campo es obligatorio" }
  ]
}
```

### 422 de validación: listas y parámetros

`POST /cursos` con `"diasSemana": ["domingo"]`:
```json
{ "detail": "Hay datos inválidos en la solicitud",
  "errores": [ { "campo": "diasSemana.0", "mensaje": "El valor no está permitido" } ] }
```

`GET /catalogos/ciclos?estado=viejo`:
```json
{ "detail": "Hay datos inválidos en la solicitud",
  "errores": [ { "campo": "estado", "mensaje": "El valor no está permitido" } ] }
```

`GET /docente/cursos/abc/alumnos`:
```json
{ "detail": "Hay datos inválidos en la solicitud",
  "errores": [ { "campo": "curso_id", "mensaje": "Debe ser un número entero" } ] }
```

### 422 de regla de negocio (formato B)

`POST /usuarios/registro` con `"carrera": "XXXX"`:
```json
{ "detail": "La carrera seleccionada no pertenece al catálogo oficial" }
```

### 401: no autenticado

Token alterado o expirado (`security.py → datos_token`):
```json
{ "detail": "Sesión inválida o expirada" }
```
Token de una sesión cerrada con logout:
```json
{ "detail": "La sesión ya no es válida; inicia sesión de nuevo" }
```
Login con datos incorrectos (`services.py → iniciarSesion`):
```json
{ "detail": "Código o contraseña incorrectos" }
```
Sin encabezado `Authorization` (lo genera FastAPI, en inglés; ver la nota *Por confirmar* en [04-seguridad.md](04-seguridad.md#3-el-encabezado-authorization)):
```json
{ "detail": "Not authenticated" }
```

### 403: sin permiso

Un estudiante intenta `GET /admin/usuarios` (`security.py → requiere_admin`):
```json
{ "detail": "Se requiere rol de administrador" }
```
Un docente intenta ver los alumnos de un curso ajeno (`services.py → _curso_del_docente`):
```json
{ "detail": "Este curso no te pertenece" }
```
Un docente pendiente intenta iniciar sesión:
```json
{ "detail": "Tu cuenta está pendiente de aprobación por un administrador" }
```

### 404: no existe

`POST /inscripcion` con un código que no existe:
```json
{ "detail": "El código no corresponde a ningún curso" }
```
Una ruta que no existe (lo genera FastAPI):
```json
{ "detail": "Not Found" }
```

### 409: conflicto

Registro con un correo ya usado:
```json
{ "detail": "El correo institucional ya está registrado" }
```
Inscribirse dos veces:
```json
{ "detail": "Ya estás inscrito en este curso" }
```
Crear un curso en un ciclo cerrado:
```json
{ "detail": "No se pueden crear cursos en un ciclo que ya terminó" }
```

### 500: error del servidor

`services.py → crearCurso`, si tras 5 intentos no logra un código de curso único:
```json
{ "detail": "No se pudo generar un código de curso único" }
```
Cualquier otra excepción no prevista también da 500, con el texto plano `Internal Server Error`. El detalle aparece en la terminal donde corre Uvicorn.

---

## Lista completa de mensajes `HTTPException` por archivo

| Archivo → función | Código | Mensaje |
|-------------------|--------|---------|
| `security.py → datos_token` | 401 | Sesión inválida o expirada |
| `security.py → datos_token` | 401 | La sesión ya no es válida; inicia sesión de nuevo |
| `security.py → usuario_actual` | 401 | Sesión inválida |
| `security.py → usuario_actual` | 401 | Usuario no válido |
| `security.py → requiere_admin` | 403 | Se requiere rol de administrador |
| `security.py → requiere_docente` | 403 | Se requiere rol de docente |
| `routers/catalogos.py → ciclo_actual` | 404 | No hay un ciclo escolar en curso registrado |
| `services.py → crear_carrera` | 409 | Ya existe una carrera con esa clave o nombre |
| `services.py → _validar_catalogos` | 422 | La carrera seleccionada no pertenece al catálogo oficial |
| `services.py → _validar_catalogos` | 409 | No hay un ciclo escolar en curso registrado; contacta a un administrador |
| `services.py → _validar_catalogos` | 422 | El ciclo en curso es *AAAA-X* |
| `services.py → registrarse` / `_crear_personal` | 409 | El correo institucional ya está registrado |
| `services.py → registrarse` | 409 | El código de estudiante ya está registrado |
| `services.py → registrarse` / `_crear_personal` | 409 | El número de empleado ya está registrado |
| `services.py → registrarse` / `_crear_personal` | 409 | Ya existe un registro con esos datos |
| `services.py → iniciarSesion` | 401 | Código o contraseña incorrectos |
| `services.py → iniciarSesion` | 403 | Tu cuenta está pendiente de aprobación por un administrador |
| `services.py → iniciarSesion` | 403 | Tu cuenta está desactivada |
| `services.py → cambiar_estado_usuario` | 404 | Usuario no encontrado |
| `services.py → cambiar_estado_usuario` | 409 | No puedes cambiar tu propio estado |
| `services.py → recuperarContrasena` | 404 | Usuario no encontrado |
| `services.py → crearCiclo` | 409 | Ya existe un ciclo con ese nombre |
| `services.py → reasignar_docente` | 404 | Curso no encontrado |
| `services.py → reasignar_docente` | 404 | Docente no encontrado |
| `services.py → reasignar_docente` | 409 | El docente está inactivo |
| `services.py → crearCurso` | 404 | Ciclo escolar no encontrado |
| `services.py → crearCurso` | 409 | No se pueden crear cursos en un ciclo que ya terminó |
| `services.py → crearCurso` | 409 | Ya tienes un curso con esa materia y sección en este ciclo |
| `services.py → crearCurso` | 500 | No se pudo generar un código de curso único |
| `services.py → _curso_del_docente` | 404 | Curso no encontrado |
| `services.py → _curso_del_docente` | 403 | Este curso no te pertenece |
| `services.py → actualizar_curso` | 422 | La hora de fin debe ser posterior a la hora de inicio |
| `services.py → inscribirseCurso` | 403 | Solo los estudiantes pueden inscribirse |
| `services.py → inscribirseCurso` | 404 | El código no corresponde a ningún curso |
| `services.py → inscribirseCurso` | 409 | El curso no está activo |
| `services.py → inscribirseCurso` | 409 | Ya estás inscrito en este curso |

[← Endpoints](05-endpoints.md) · [Volver al índice](README.md) · [Siguiente: Pruebas →](07-pruebas.md)
