# 05 · Endpoints

[← Volver al índice](README.md)

Un **endpoint** es una combinación de **método HTTP + ruta** que el backend sabe atender, por ejemplo `POST /usuarios/login`. En total hay **26 endpoints** en 5 routers. Puedes probarlos todos en **http://127.0.0.1:8000/docs**.

## Cómo leer estas tablas

**Métodos HTTP que usamos:**

| Método | Para qué |
|--------|----------|
| `GET` | Consultar; no cambia nada |
| `POST` | Crear algo o ejecutar una acción (login, logout, inscribirse) |
| `PATCH` | Modificar **parte** de algo que ya existe |

**Quién puede usarlo:**

| Etiqueta | Significado | Cómo se revisa |
|----------|-------------|----------------|
| **Público** | Sin iniciar sesión | Sin dependencia de seguridad |
| **Sesión** | Cualquier usuario con token válido y cuenta `activa` | `security.py → usuario_actual` |
| **Estudiante** | Sesión + tener perfil `Estudiante` | `usuario_actual` + revisión en `services.py` |
| **Docente** | Sesión + tener perfil `Docente` | `security.py → requiere_docente` |
| **Docente dueño** | Docente + ser el creador del curso (RF-95) | `requiere_docente` + `services.py → _curso_del_docente` |
| **Admin** | Sesión + tener perfil `Administrador` | `security.py → requiere_admin` |

**Errores comunes a todos los endpoints protegidos** (no se repiten en cada fila):

- **401**: falta el token, es inválido o expiró, la sesión se cerró, o el usuario ya no está activo.
- **403**: el usuario no tiene el rol requerido. Ver también la nota de [04-seguridad.md](04-seguridad.md#3-el-encabezado-authorization) sobre 401/403 cuando falta el encabezado.
- **422**: el JSON o los parámetros no pasan la validación (formato en [06-errores.md](06-errores.md)).

En los ejemplos, `{curso_id}` y `{usuario_id}` son **parámetros de ruta**: se reemplazan por un número, como `/docente/cursos/3`. `?estado=...` es un **parámetro de consulta** (*query*), opcional salvo que se indique.

---

## Router `usuarios`: registro y sesión

Archivo: `routers/usuarios.py` · Prefijo: `/usuarios`

| Método | Ruta | Quién | Recibe | Respuestas | RF |
|--------|------|-------|--------|------------|----|
| POST | `/usuarios/registro` | Público | JSON `UsuarioCrear` | **201**, 409, 422 | RF-01, RF-02, RF-03 |
| POST | `/usuarios/login` | Público | JSON `{codigo, contrasena}` | **200**, 401, 403, 422 | RF-04, RF-90 |
| POST | `/usuarios/logout` | Token válido* | Nada (solo el token) | **200**, 401 | RF-06, RF-91 |
| GET | `/usuarios/yo` | Sesión | Nada | **200**, 401 | RF-05, RF-90 |
| GET | `/usuarios/recuperar-contrasena` | Público | Nada | **200** | RF-07 |

\* `logout` usa `datos_token`, no `usuario_actual`: basta con que el token sea válido, aunque la cuenta esté inactiva.

### `POST /usuarios/registro`

`routers/usuarios.py → registrar_usuario` → `services.py → registrarse`

El **rol se decide por el dominio del correo** (`config.py → DOMINIOS_ROL`):

| Dominio | Rol | Campos extra obligatorios | Estado inicial |
|---------|-----|---------------------------|----------------|
| `@alumnos.udg.mx` | estudiante | `codigo` (9 dígitos), `carrera` (clave del catálogo), `ciclo` (el ciclo vigente) | `activo` |
| `@academicos.udg.mx` | docente | `noEmpleado` (3–20 caracteres: letras, números, guiones); `departamento` es opcional | `pendiente`, o `activo` si `DOCENTE_REQUIERE_APROBACION=0` |
| Cualquier otro | — | Se rechaza con 422 | — |

Campos de `UsuarioCrear` (`schemas.py`):

| Campo | Obligatorio | Reglas |
|-------|-------------|--------|
| `nombre`, `apellidos` | Sí | 1–100 caracteres; letras (con acentos y ñ), espacios, `'`, `.` y `-`; debe empezar con letra |
| `correoInstitucional` | Sí | Formato de correo; se pasa a minúsculas |
| `contrasena` | Sí | Reglas RF-03 (ver [04-seguridad.md](04-seguridad.md#6-validación-de-contraseñas-rf-03)) |
| `confirmarContrasena` | Sí | Igual a `contrasena` |
| `codigo` | Estudiante | 9 dígitos; se acepta como texto o número |
| `carrera` | Estudiante | Clave alfanumérica de 2–10 caracteres, en mayúsculas; debe existir en `Carrera` |
| `ciclo` | Estudiante | Se pasa a mayúsculas; debe ser el ciclo vigente (`GET /catalogos/ciclo-actual`) |
| `noEmpleado` | Docente | Ver tabla de arriba; se pasa a mayúsculas |
| `departamento` | No | Texto libre |

Petición (estudiante):
```json
{
  "codigo": "123456789", "nombre": "Ana", "apellidos": "López",
  "carrera": "INFO", "ciclo": "2026-B",
  "correoInstitucional": "ana@alumnos.udg.mx",
  "contrasena": "Secreto123", "confirmarContrasena": "Secreto123"
}
```

**201** (estudiante):
```json
{
  "id": 1, "nombre": "Ana", "apellidos": "López",
  "correoInstitucional": "ana@alumnos.udg.mx",
  "estado": "activo", "rol": "estudiante",
  "mensaje": "Cuenta creada correctamente"
}
```

**201** (docente, con aprobación activada):
```json
{
  "id": 2, "nombre": "Luis", "apellidos": "Pérez",
  "correoInstitucional": "luis@academicos.udg.mx",
  "estado": "pendiente", "rol": "docente",
  "mensaje": "Cuenta creada; un administrador debe aprobarla antes de que puedas entrar"
}
```

Errores posibles:

| Código | `detail` | Cuándo |
|--------|----------|--------|
| 409 | `El correo institucional ya está registrado` | Correo repetido |
| 409 | `El código de estudiante ya está registrado` | Código repetido |
| 409 | `El número de empleado ya está registrado` | `noEmpleado` repetido entre docentes |
| 409 | `No hay un ciclo escolar en curso registrado; contacta a un administrador` | No hay ciclo activo ni próximo |
| 409 | `Ya existe un registro con esos datos` | Choque en la base al guardar (respaldo) |
| 422 | `La carrera seleccionada no pertenece al catálogo oficial` | Carrera inexistente (formato simple, sin `errores[]`) |
| 422 | `El ciclo en curso es 2026-B` | El ciclo enviado no es el vigente (formato simple) |
| 422 | `Hay datos inválidos en la solicitud` + `errores[]` | Cualquier falla de validación del esquema |

### `POST /usuarios/login`

`routers/usuarios.py → iniciar_sesion` → `services.py → iniciarSesion`

Petición:
```json
{ "codigo": "123456789", "contrasena": "Secreto123" }
```
`codigo` es el código de estudiante o el número de empleado (docente o administrador). Se pasa a mayúsculas y puede enviarse como número.

**200**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "roles": ["estudiante"],
  "panel": "estudiante",
  "nombre": "Ana López"
}
```

| Código | `detail` |
|--------|----------|
| 401 | `Código o contraseña incorrectos` (el mismo mensaje si el código no existe o si la contraseña está mal) |
| 403 | `Tu cuenta está pendiente de aprobación por un administrador` |
| 403 | `Tu cuenta está desactivada` |

### `POST /usuarios/logout`

`routers/usuarios.py → cerrar_sesion` → `services.py → cerrarSesion`

Encabezado `Authorization: Bearer <token>`, sin cuerpo.

**200**:
```json
{ "mensaje": "Sesión cerrada correctamente" }
```
Después de esto, el mismo token recibe 401 en cualquier endpoint, incluido otro logout.

### `GET /usuarios/yo`

`routers/usuarios.py → mi_perfil` → `services.py → perfil_de`

**200**:
```json
{
  "id": 1, "nombre": "Ana", "apellidos": "López",
  "correoInstitucional": "ana@alumnos.udg.mx",
  "codigo": "123456789",
  "roles": ["estudiante"],
  "panel": "estudiante"
}
```
`codigo` es el código de estudiante o el número de empleado, según el perfil.

### `GET /usuarios/recuperar-contrasena`

`routers/usuarios.py → recuperar_contrasena`. Solo devuelve un texto fijo (`config.py → MENSAJE_RECUPERACION`).

**200**:
```json
{ "mensaje": "Si olvidaste tu contraseña, comunícate con tu coordinador de carrera o con un administrador institucional para solicitar el restablecimiento manual." }
```

---

## Router `catalogos`: listas públicas

Archivo: `routers/catalogos.py` · Prefijo: `/catalogos` · **Todos son públicos**: el formulario de registro los necesita antes de iniciar sesión.

| Método | Ruta | Quién | Recibe | Respuestas | RF |
|--------|------|-------|--------|------------|----|
| GET | `/catalogos/carreras` | Público | Nada | **200** | RF-02 |
| GET | `/catalogos/ciclos` | Público | Query opcional `estado` = `activo`, `proximo` o `cerrado` | **200**, 422 | RF-02, RF-08 |
| GET | `/catalogos/ciclo-actual` | Público | Nada | **200**, 404 | RF-02 |
| GET | `/catalogos/tipos-evaluacion` | Público | Nada | **200** | RF-17 |
| GET | `/catalogos/dias-semana` | Público | Nada | **200** | RF-13 |

### `GET /catalogos/carreras`

Ordenadas por nombre. **200**:
```json
[
  { "id": 1, "clave": "ICOM", "nombre": "Ingeniería en Computación" },
  { "id": 2, "clave": "INFO", "nombre": "Ingeniería Informática" }
]
```

### `GET /catalogos/ciclos`

`services.py → listar_ciclos`. Del más reciente al más antiguo (por `id`). El `estado` **se calcula con la fecha de hoy**. **200**:
```json
[
  { "id": 2, "nombreOficial": "2027-A", "fechaInicio": "2027-01-16", "fechaTermino": "2027-07-15", "estado": "proximo" },
  { "id": 1, "nombreOficial": "2026-B", "fechaInicio": "2026-07-16", "fechaTermino": "2026-12-16", "estado": "activo" }
]
```

### `GET /catalogos/ciclo-actual`

`services.py → ciclo_vigente`. Es el ciclo que el estudiante debe enviar al registrarse. **200**:
```json
{ "id": 1, "nombreOficial": "2026-B", "fechaInicio": "2026-07-16", "fechaTermino": "2026-12-16", "estado": "activo" }
```
**404**: `{"detail": "No hay un ciclo escolar en curso registrado"}`

### `GET /catalogos/tipos-evaluacion`

**200**:
```json
[
  { "valor": "numerica", "etiqueta": "Calificación Numérica" },
  { "valor": "aprobado_no_aprobado", "etiqueta": "Aprobado/No Aprobado" }
]
```

### `GET /catalogos/dias-semana`

**200**:
```json
["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]
```
Sin acentos y sin domingo.

---

## Router `cursos`: gestión académica

Archivo: `routers/cursos.py` · Sin prefijo

| Método | Ruta | Quién | Recibe | Respuestas | RF |
|--------|------|-------|--------|------------|----|
| POST | `/cursos` | Docente | JSON `CursoCrear` | **201**, 404, 409, 422, 500 | RF-09, RF-12, RF-13, RF-14, RF-17, RF-18 |
| GET | `/cursos` | Sesión | Nada | **200** | RF-14 |
| POST | `/inscripcion` | Estudiante | JSON `{codigoCurso}` | **201**, 403, 404, 409, 422 | RF-15 |

### `POST /cursos`

`routers/cursos.py → crear_curso` → `services.py → crearCurso`

| Campo | Obligatorio | Reglas |
|-------|-------------|--------|
| `nombreMateria` | Sí | 1–100 caracteres |
| `seccion` | Sí | 1–10 caracteres; se pasa a mayúsculas |
| `descripcion` | Sí | 1–500 caracteres (RF-12) |
| `cicloEscolar_id` | Sí | `id` de un ciclo existente que no haya terminado (RF-09) |
| `tipoEvaluacion` | Sí | `numerica` o `aprobado_no_aprobado` (RF-17) |
| `diasSemana` | Sí | Lista de 1 o más días de `/catalogos/dias-semana`, sin repetir (RF-13) |
| `horaInicio`, `horaFin` | Sí | Formato `HH:MM`; el fin debe ser posterior al inicio (RF-13) |

El servidor **fija** `umbralNumerico` (60 o 0, RF-18), `codigoCurso` (RF-14), `estado = "activo"` y `docente_id` (el docente que hace la petición). Si el cliente manda esos campos, se ignoran.

Petición:
```json
{
  "nombreMateria": "Bases de datos", "seccion": "D01", "descripcion": "Curso de SQL",
  "cicloEscolar_id": 1, "tipoEvaluacion": "numerica",
  "diasSemana": ["miercoles", "lunes"], "horaInicio": "08:00", "horaFin": "10:00"
}
```

**201** (`CursoSalida`; los días salen ordenados):
```json
{
  "id": 1, "nombreMateria": "Bases de datos", "seccion": "D01", "descripcion": "Curso de SQL",
  "estado": "activo", "tipoEvaluacion": "numerica", "umbralNumerico": 60.0,
  "cicloEscolar_id": 1, "diasSemana": ["lunes", "miercoles"],
  "horaInicio": "08:00", "horaFin": "10:00", "docente_id": 2,
  "codigoCurso": "A1B2C3D4"
}
```

| Código | `detail` |
|--------|----------|
| 404 | `Ciclo escolar no encontrado` |
| 409 | `No se pueden crear cursos en un ciclo que ya terminó` |
| 409 | `Ya tienes un curso con esa materia y sección en este ciclo` |
| 500 | `No se pudo generar un código de curso único` (tras 5 intentos; prácticamente imposible) |

Se **puede** crear un curso en un ciclo `proximo` (`test_rf09_se_puede_preparar_un_curso_del_ciclo_proximo`).

### `GET /cursos`

`routers/cursos.py → obtener_cursos`. Lista **todos los cursos activos** de todos los docentes, **sin** `codigoCurso` (`CursoPublico`, RF-14). **200**:
```json
[
  {
    "id": 1, "nombreMateria": "Bases de datos", "seccion": "D01", "descripcion": "Curso de SQL",
    "estado": "activo", "tipoEvaluacion": "numerica", "umbralNumerico": 60.0,
    "cicloEscolar_id": 1, "diasSemana": ["lunes", "miercoles"],
    "horaInicio": "08:00", "horaFin": "10:00", "docente_id": 2
  }
]
```

### `POST /inscripcion`

`routers/cursos.py → inscribir_alumno` → `services.py → inscribirseCurso`

Petición (el código no distingue mayúsculas; máximo 10 caracteres):
```json
{ "codigoCurso": "a1b2c3d4" }
```

**201**:
```json
{ "mensaje": "Inscripción exitosa", "curso": "Bases de datos" }
```

| Código | `detail` |
|--------|----------|
| 403 | `Solo los estudiantes pueden inscribirse` |
| 404 | `El código no corresponde a ningún curso` |
| 409 | `El curso no está activo` (archivado) |
| 409 | `Ya estás inscrito en este curso` |

---

## Router `docentes`: controles del docente

Archivo: `routers/docentes.py` · Prefijo: `/docente` (en singular) · RF-95: solo el docente creador del curso.

| Método | Ruta | Quién | Recibe | Respuestas | RF |
|--------|------|-------|--------|------------|----|
| GET | `/docente/cursos` | Docente | Query `estado` = `activo` (por defecto) o `archivado` | **200**, 422 | RF-11, RF-14, RF-95 |
| GET | `/docente/cursos/{curso_id}/alumnos` | Docente dueño | Nada | **200**, 403, 404 | RF-16, RF-95 |
| PATCH | `/docente/cursos/{curso_id}` | Docente dueño | JSON `CursoActualizar` (todo opcional) | **200**, 403, 404, 422 | RF-13, RF-17, RF-18, RF-95 |
| PATCH | `/docente/cursos/{curso_id}/estado` | Docente dueño | JSON `{estado}` = `activo` o `archivado` | **200**, 403, 404, 422 | RF-10, RF-95 |

Errores de dueño (`services.py → _curso_del_docente`): **404** `Curso no encontrado`, **403** `Este curso no te pertenece`.

### `GET /docente/cursos`

`services.py → cursos_del_docente`. Solo los cursos del docente, **con** `codigoCurso`, para compartirlo con los alumnos. **200**: lista de objetos `CursoSalida`, iguales al de `POST /cursos`. Si no tiene cursos, `[]`.

### `GET /docente/cursos/{curso_id}/alumnos`

`services.py → alumnos_de_curso`. Ordenados por apellidos y nombre. **200**:
```json
[
  {
    "matricula_id": 1, "estudiante_id": 3, "codigoEstudiante": "123456789",
    "nombre": "Ana", "apellidos": "López", "correoInstitucional": "ana@alumnos.udg.mx",
    "estado": "activo", "fechaInscripcion": "2026-10-25T14:03:00",
    "calificacionAcumuladaActual": null
  }
]
```

### `PATCH /docente/cursos/{curso_id}`

`services.py → actualizar_curso`. **Solo se cambian los campos que envíes.** Admite `nombreMateria`, `seccion`, `descripcion`, `tipoEvaluacion`, `diasSemana`, `horaInicio` y `horaFin`, con las mismas reglas que al crear.

- Un campo enviado como `null` se ignora.
- `cicloEscolar_id`, `umbralNumerico`, `codigoCurso` y `docente_id` **no se pueden cambiar** aquí: si se envían, se ignoran.
- Si cambia `tipoEvaluacion`, el servidor recalcula `umbralNumerico` (RF-18).
- La hora de fin se compara contra la de inicio **ya guardada** si solo envías una.

Petición:
```json
{ "diasSemana": ["martes"], "horaInicio": "09:00", "horaFin": "11:00" }
```
**200**: el `CursoSalida` actualizado.

**422** por horario (formato simple, sin `errores[]`, porque lo genera `services.py`):
```json
{ "detail": "La hora de fin debe ser posterior a la hora de inicio" }
```

### `PATCH /docente/cursos/{curso_id}/estado`

`services.py → cambiar_estado_curso`. Archiva o reactiva un curso (RF-10).

```json
{ "estado": "archivado" }
```
**200**: el `CursoSalida` con `"estado": "archivado"`. Un curso archivado ya no aparece en `GET /cursos` ni acepta inscripciones.

---

## Router `admin`: administración

Archivo: `routers/admin.py` · Prefijo: `/admin` · **Todos exigen Admin** (`requiere_admin`).

| Método | Ruta | Quién | Recibe | Respuestas | RF |
|--------|------|-------|--------|------------|----|
| POST | `/admin/docentes` | Admin | JSON `DocenteCrear` | **201**, 409, 422 | RF-93 |
| POST | `/admin/administradores` | Admin | JSON `AdminCrear` | **201**, 409, 422 | RF-93 |
| GET | `/admin/usuarios` | Admin | Query opcional `rol` (`estudiante`, `docente`, `administrador`) y `estado` (`activo`, `inactivo`, `pendiente`) | **200**, 422 | RF-93 |
| PATCH | `/admin/usuarios/{usuario_id}/estado` | Admin | JSON `{estado}` = `activo` o `inactivo` | **200**, 404, 409, 422 | RF-93 |
| PATCH | `/admin/usuarios/{usuario_id}/contrasena` | Admin | JSON `{nueva_contrasena}` | **200**, 404, 422 | RF-07 |
| POST | `/admin/carreras` | Admin | JSON `{clave, nombre}` | **201**, 409, 422 | RF-02 |
| POST | `/admin/ciclos` | Admin | JSON `CicloCrear` | **201**, 409, 422 | RF-08 |
| GET | `/admin/cursos` | Admin | Nada | **200** | Por confirmar |
| PATCH | `/admin/cursos/{curso_id}/docente` | Admin | JSON `{docente_id}` | **200**, 404, 409, 422 | Por confirmar |

### `POST /admin/docentes`

`services.py → crear_docente`. A diferencia del registro público, el docente queda **`activo` de inmediato**.

```json
{
  "nombre": "Doc", "apellidos": "Ente", "correoInstitucional": "d1@academicos.udg.mx",
  "contrasena": "Docente123", "noEmpleado": "D-1", "departamento": "Sistemas"
}
```
El correo **debe** terminar en `@academicos.udg.mx` (`schemas.py → DocenteCrear.correo_de_docente`). `departamento` es opcional.

**201** (`UsuarioSalida`):
```json
{ "id": 2, "nombre": "Doc", "apellidos": "Ente", "correoInstitucional": "d1@academicos.udg.mx" }
```
**409**: `El correo institucional ya está registrado` · `El número de empleado ya está registrado`

### `POST /admin/administradores`

`services.py → crear_administrador`. Mismos campos que el anterior, sin `departamento`. **El correo no tiene restricción de dominio (Por confirmar si es intencional).** **201**: `UsuarioSalida`.

### `GET /admin/usuarios`

`services.py → listar_usuarios`. Ejemplo: `/admin/usuarios?estado=pendiente` para ver docentes por aprobar. **200**:
```json
[
  {
    "id": 2, "nombre": "Luis", "apellidos": "Pérez",
    "correoInstitucional": "luis@academicos.udg.mx",
    "estado": "pendiente", "roles": ["docente"]
  }
]
```

### `PATCH /admin/usuarios/{usuario_id}/estado`

`services.py → cambiar_estado_usuario`. Sirve para **aprobar** un docente pendiente (`"activo"`) o **desactivar** cualquier cuenta (`"inactivo"`). No se puede poner `"pendiente"`.

```json
{ "estado": "activo" }
```
**200**: el usuario con el formato de `GET /admin/usuarios`.

| Código | `detail` |
|--------|----------|
| 404 | `Usuario no encontrado` |
| 409 | `No puedes cambiar tu propio estado` (evita que el sistema se quede sin administradores) |

### `PATCH /admin/usuarios/{usuario_id}/contrasena`

`services.py → recuperarContrasena`. Restablecimiento manual (RF-07); la nueva contraseña cumple RF-03.

```json
{ "nueva_contrasena": "Nueva12345" }
```
**200**: `{"mensaje": "Contraseña restablecida correctamente"}` · **404**: `Usuario no encontrado`

### `POST /admin/carreras`

`services.py → crear_carrera`.

```json
{ "clave": "icom", "nombre": "Ingeniería en Computación" }
```
**201**: `{"id": 3, "clave": "ICOM", "nombre": "Ingeniería en Computación"}` (la clave se guarda en mayúsculas)
**409**: `Ya existe una carrera con esa clave o nombre`

### `POST /admin/ciclos`

`services.py → crearCiclo`. Solo hace falta el nombre: **las fechas salen del calendario oficial** (`schemas.py → CicloCrear.validar_calendario`). Si envías fechas, deben coincidir exactamente con las oficiales.

```json
{ "nombreOficial": "2027-a" }
```
**201**:
```json
{ "id": 2, "nombreOficial": "2027-A", "fechaInicio": "2027-01-16", "fechaTermino": "2027-07-15", "estado": "proximo" }
```

| Código | Mensaje | Cuándo |
|--------|---------|--------|
| 409 | `Ya existe un ciclo con ese nombre` | Nombre repetido |
| 422 | `El nombre del ciclo debe tener el formato AAAA-A o AAAA-B (por ejemplo 2026-B)` | `2027-C`, `27-A`… |
| 422 | `El ciclo 2027-B va del 16/07/2027 al 16/12/2027` | Fechas distintas a las oficiales |

### `GET /admin/cursos`

`routers/admin.py → listar_todos_los_cursos`. Todos los cursos, **activos y archivados**, de todos los docentes, **con** `codigoCurso`. **200**: lista de `CursoSalida`.

### `PATCH /admin/cursos/{curso_id}/docente`

`services.py → reasignar_docente`. Cambia el docente responsable de un curso. `docente_id` es el `id` del usuario docente (el mismo número en `Usuario` y en `Docente`).

```json
{ "docente_id": 3 }
```
**200**: el `CursoSalida` con el nuevo `docente_id`.

| Código | `detail` |
|--------|----------|
| 404 | `Curso no encontrado` |
| 404 | `Docente no encontrado` |
| 409 | `El docente está inactivo` (también si está `pendiente`) |

---

## Endpoints que FastAPI agrega solo

| Ruta | Qué es |
|------|--------|
| `GET /docs` | Documentación interactiva (Swagger UI) |
| `GET /redoc` | Documentación alternativa (ReDoc) |
| `GET /openapi.json` | Descripción de la API en formato OpenAPI, de la que salen las dos anteriores |

[← Seguridad](04-seguridad.md) · [Volver al índice](README.md) · [Siguiente: Errores →](06-errores.md)
