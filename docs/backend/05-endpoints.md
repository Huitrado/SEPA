# 05 · Endpoints

[← Volver al índice](README.md)

Un **endpoint** es una combinación de **método HTTP + ruta** que el backend sabe atender, por ejemplo `POST /usuarios/login`. En total hay **43 endpoints** en 5 routers. Puedes probarlos todos en **http://127.0.0.1:8000/docs**.

## Cómo leer estas tablas

**Métodos HTTP que usamos:**

| Método | Para qué |
|--------|----------|
| `GET` | Consultar; no cambia nada |
| `POST` | Crear algo o ejecutar una acción (login, logout, inscribirse) |
| `PATCH` | Modificar **parte** de algo que ya existe |
| `PUT` | Reemplazar algo completo (por ejemplo, la lista de asistencia de una sesión) |
| `DELETE` | Eliminar algo |

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
| GET | `/catalogos/materias` | Público | Nada | **200** | RF-12 |
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

### `GET /catalogos/materias`

`routers/catalogos.py → materias`. Materias del plan de estudios (se cargan de `planes.json`), ordenadas por nombre, para elegir al crear un curso. **200**:
```json
[
  { "id": 12, "clave": "I5288", "nombre": "Bases de Datos" }
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
| GET | `/actividades/{actividad_id}/archivo` | Docente dueño o alumno inscrito activo | Nada | **200** (archivo), 403, 404 | RF-36 |

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

### `GET /actividades/{actividad_id}/archivo`

`routers/cursos.py → descargar_archivo_actividad` → `services.py → archivo_de_actividad`. Descarga el archivo que el docente adjuntó a la actividad (RF-36). Lo pueden bajar **el docente del curso** y **los alumnos con matrícula activa** en él.

**200**: el archivo, con `Content-Disposition: attachment; filename="<título de la actividad>.<extensión>"`. Siempre se envía como descarga, nunca se muestra dentro de la página.

Desde el frontend hay que pedirlo con `fetch` y el token, y luego guardarlo con un `Blob`: un `<a href>` normal no envía el encabezado `Authorization`.

| Código | `detail` |
|--------|----------|
| 403 | `No tienes acceso a esta actividad` |
| 404 | `Actividad no encontrada` |
| 404 | `La actividad no tiene archivo adjunto` |

---

## Router `docentes`: controles del docente

Archivo: `routers/docentes.py` · Prefijo: `/docente` (en singular) · RF-95: solo el docente creador del curso.

| Método | Ruta | Quién | Recibe | Respuestas | RF |
|--------|------|-------|--------|------------|----|
| GET | `/docente/cursos` | Docente | Query `estado` = `activo` (por defecto) o `archivado` | **200**, 422 | RF-11, RF-14, RF-95 |
| GET | `/docente/cursos/{curso_id}/alumnos` | Docente dueño | Nada | **200**, 403, 404 | RF-16, RF-95 |
| PATCH | `/docente/cursos/{curso_id}` | Docente dueño | JSON `CursoActualizar` (todo opcional) | **200**, 403, 404, 422 | RF-13, RF-17, RF-18, RF-95 |
| PATCH | `/docente/cursos/{curso_id}/estado` | Docente dueño | JSON `{estado}` = `activo` o `archivado` | **200**, 403, 404, 422 | RF-10, RF-95 |
| POST | `/docente/cursos/{curso_id}/sesiones` | Docente dueño | JSON opcional `{tema}` | **201**, 403, 404, 409, 422 | RF-19, RF-22, RF-27 |
| GET | `/docente/cursos/{curso_id}/sesiones/{sesion_id}` | Docente dueño | Nada | **200**, 403, 404 | RF-20, RF-25 |
| PUT | `/docente/cursos/{curso_id}/sesiones/{sesion_id}/lista` | Docente dueño | JSON `ListaAsistencia` | **200**, 403, 404, 422 | RF-20, RF-23, RF-25 |
| GET | `/docente/cursos/{curso_id}/asistencia` | Docente dueño | Nada | **200**, 403, 404 | RF-24, RF-26, RF-28, RF-49 |
| GET | `/docente/cursos/{curso_id}/categorias` | Docente dueño | Nada | **200**, 403, 404 | RF-31, RF-32 |
| POST | `/docente/cursos/{curso_id}/categorias` | Docente dueño | JSON `{nombre, porcentajePeso}` | **201**, 403, 404, 409, 422 | RF-31, RF-32 |
| PATCH | `/docente/cursos/{curso_id}/categorias/{categoria_id}` | Docente dueño | JSON `{nombre?, porcentajePeso?}` | **200**, 403, 404, 409, 422 | RF-31, RF-32 |
| DELETE | `/docente/cursos/{curso_id}/categorias/{categoria_id}` | Docente dueño | Nada | **200**, 403, 404, 409 | RF-31 |
| GET | `/docente/cursos/{curso_id}/actividades` | Docente dueño | Nada | **200**, 403, 404 | RF-29 a RF-35 |
| POST | `/docente/cursos/{curso_id}/actividades` | Docente dueño | JSON `ActividadCrear` | **201**, 403, 404, 409, 422 | RF-29 a RF-35 |
| GET | `/docente/cursos/{curso_id}/actividades/{actividad_id}` | Docente dueño | Nada | **200**, 403, 404 | RF-29 a RF-35 |
| PATCH | `/docente/cursos/{curso_id}/actividades/{actividad_id}` | Docente dueño | JSON `ActividadActualizar` (todo opcional) | **200**, 403, 404, 422 | RF-29 a RF-35 |
| DELETE | `/docente/cursos/{curso_id}/actividades/{actividad_id}` | Docente dueño | Nada | **200**, 403, 404, 409 | RF-29 a RF-35 |
| PUT | `/docente/cursos/{curso_id}/actividades/{actividad_id}/archivo` | Docente dueño | `multipart/form-data` con el campo `archivo` | **200**, 403, 404, 413, 415, 422 | RF-36, RNF-8 |
| DELETE | `/docente/cursos/{curso_id}/actividades/{actividad_id}/archivo` | Docente dueño | Nada | **200**, 403, 404 | RF-36 |

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


### Control de asistencia (RF-19 a RF-28)

Reglas comunes:

- **Solo alumnos activos.** Las matrículas con otro estado (por ejemplo `baja`) no aparecen en las listas ni en la cuadrícula, y no se aceptan al guardar.
- **Estados de un alumno en una sesión:** `pendiente` (la lista aún no se guarda), `asistencia`, `falta` o `retardo`.
- **Porcentaje** (`services.py → calcular_porcentaje_asistencia`): (asistencias + retardos) / sesiones con lista guardada × 100. Un retardo cuenta como asistencia, las sesiones pendientes no cuentan y, sin sesiones guardadas, el porcentaje es **100**.
- **Estatus normativo** (RF-49, `services.py → estatus_normativo`): `Ordinario` ≥ 80 %, `Extraordinario` ≥ 65 % y < 80 %, `Sin Derecho` < 65 %.
- **Semáforo por asistencia** (`services.py → semaforo_asistencia`): `verde` > 85 %, `amarillo` de 80 % a 85 % (80 % exacto es amarillo), `rojo` < 80 %.
- Los umbrales están en `config.py` (`ASISTENCIA_ORDINARIO`, `ASISTENCIA_EXTRAORDINARIO`, `SEMAFORO_VERDE`, `SEMAFORO_AMARILLO`). `services.py → porcentaje_asistencia(db, matricula_id)` da el porcentaje de un alumno para otros módulos.

#### `POST /docente/cursos/{curso_id}/sesiones`

`routers/docentes.py → generar_sesion` → `services.py → generarSesionClase`. Genera la sesión **de hoy** (RF-19, RF-27). La fecha la pone el servidor y el horario se copia del curso. El cuerpo es opcional:

```json
{ "tema": "Normalización" }
```

Cada alumno activo queda en `pendiente` y la lista con `listaGuardada: false` (RF-22). **201** (`SesionClaseDetalle`):
```json
{
  "id": 1, "curso_id": 1, "fecha": "2026-10-26", "horaInicio": "08:00", "horaFin": "10:00",
  "tema": "Normalización", "listaGuardada": false,
  "alumnos": [
    { "matricula_id": 1, "estudiante_id": 3, "codigoEstudiante": "123456789",
      "nombre": "Ana", "apellidos": "López", "estado": "pendiente", "observaciones": null }
  ]
}
```

| Código | `detail` |
|--------|----------|
| 409 | `Hoy no es día de clase de este curso` (hoy no está en `diasSemana`) |
| 409 | `Ya existe una sesión de este curso para hoy` |
| 409 | `El curso está archivado` |
| 409 | `El ciclo escolar del curso no está en curso` (ciclo próximo o cerrado) |

#### `GET /docente/cursos/{curso_id}/sesiones/{sesion_id}`

`services.py → ver_sesion`. La sesión con la lista de alumnos activos y su estado, para pasar lista o corregirla. **200**: igual que la respuesta de `POST .../sesiones`. Un alumno que se inscribió después de generar la sesión aparece como `pendiente`.

**404**: `Sesión no encontrada` (no existe o es de otro curso).

#### `PUT /docente/cursos/{curso_id}/sesiones/{sesion_id}/lista`

`services.py → guardarListaAsistencia`. Guarda la lista y pone `listaGuardada: true` (RF-20, RF-23). Sirve también para **editar** la lista de una sesión pasada (RF-25): se envía la lista completa otra vez.

```json
{
  "asistencias": [
    { "matricula_id": 1, "estado": "retardo", "observaciones": "Llegó 08:20" },
    { "matricula_id": 2, "estado": "falta" }
  ]
}
```

| Campo | Reglas |
|-------|--------|
| `matricula_id` | Matrícula **activa** de este curso; sin repetir |
| `estado` | `asistencia`, `falta` o `retardo` |
| `observaciones` | Opcional; hasta 500 caracteres |

Hay que incluir a **todos los alumnos que estaban en la lista** al generar la sesión. Un alumno inscrito después se puede incluir, pero no es obligatorio.

**200**: el `SesionClaseDetalle` con los estados guardados.

| Código | `detail` |
|--------|----------|
| 404 | `Sesión no encontrada` |
| 422 | `Hay alumnos que no pertenecen a este curso o no están activos (matrícula 7)` |
| 422 | `Falta el estado de algunos alumnos de la lista (matrícula 2)` |
| 422 | `Hay datos inválidos en la solicitud` + `errores[]` (estado inválido o alumno repetido: `Un alumno aparece más de una vez en la lista`) |

#### `GET /docente/cursos/{curso_id}/asistencia`

`services.py → cuadricula_asistencia`. La cuadrícula del curso (RF-24, RF-26): `sesiones` son las columnas, ordenadas por fecha, con `listaGuardada` para marcar las pendientes. `alumnos` son las filas, con un estado por sesión **en el mismo orden** que `sesiones`. **200** (`CuadriculaAsistencia`):
```json
{
  "curso_id": 1,
  "sesiones": [
    { "id": 1, "curso_id": 1, "fecha": "2026-10-26", "horaInicio": "08:00", "horaFin": "10:00", "tema": null, "listaGuardada": true },
    { "id": 2, "curso_id": 1, "fecha": "2026-10-28", "horaInicio": "08:00", "horaFin": "10:00", "tema": null, "listaGuardada": false }
  ],
  "alumnos": [
    {
      "matricula_id": 1, "estudiante_id": 3, "codigoEstudiante": "123456789",
      "nombre": "Ana", "apellidos": "López",
      "estados": [
        { "sesion_id": 1, "estado": "retardo", "observaciones": "Llegó 08:20" },
        { "sesion_id": 2, "estado": "pendiente", "observaciones": null }
      ],
      "porcentajeAsistencia": 100.0, "estatusNormativo": "Ordinario", "semaforo": "verde"
    }
  ]
}
```
`estado` es `null` si el alumno se inscribió después de esa sesión y no se le registró; esa sesión no cuenta en su porcentaje. `porcentajeAsistencia` se redondea a 2 decimales.


### Categorías de evaluación (RF-31, RF-32)

El docente divide la calificación del curso en categorías (por ejemplo, Exámenes 60 % y Tareas 40 %). Reglas:

- `nombre`: 1–100 caracteres; no se puede repetir en el mismo curso (sin distinguir mayúsculas).
- `porcentajePeso`: número mayor que 0 y hasta 100; admite decimales.
- **La suma no puede superar 100** al crear ni al editar (409).
- **RF-32:** si la suma no es exactamente 100, la categoría **se guarda igual** y la respuesta trae una `advertencia`. Todas las respuestas incluyen el resumen de pesos:

| Campo | Qué es |
|-------|--------|
| `sumaPesos` | Suma de los pesos del curso, redondeada a 2 decimales |
| `pesosCompletos` | `true` solo si la suma es exactamente 100 |
| `advertencia` | `null` si la suma es 100; si no, p. ej. `Los pesos de las categorías suman 60 %; deben sumar exactamente 100 %` |

Errores de categoría (`services.py → _categoria_del_curso`): **404** `Categoría no encontrada` (no existe o es de otro curso).

#### `GET /docente/cursos/{curso_id}/categorias`

`services.py → listar_categorias`. Por orden de creación. **200** (`CategoriasCurso`):
```json
{
  "categorias": [
    { "id": 1, "curso_id": 1, "nombre": "Exámenes", "porcentajePeso": 60.0 }
  ],
  "sumaPesos": 60.0, "pesosCompletos": false,
  "advertencia": "Los pesos de las categorías suman 60 %; deben sumar exactamente 100 %"
}
```
Sin categorías: `categorias: []`, `sumaPesos: 0` y la advertencia.

#### `POST /docente/cursos/{curso_id}/categorias`

`services.py → crearCategoria`.

```json
{ "nombre": "Tareas", "porcentajePeso": 40 }
```

**201** (`CategoriaGuardada`):
```json
{
  "categoria": { "id": 2, "curso_id": 1, "nombre": "Tareas", "porcentajePeso": 40.0 },
  "sumaPesos": 100.0, "pesosCompletos": true, "advertencia": null
}
```

| Código | `detail` |
|--------|----------|
| 409 | `Ya existe una categoría con ese nombre en este curso` |
| 409 | `La suma de los pesos no puede superar 100 % (las demás categorías suman 70 %)` |

#### `PATCH /docente/cursos/{curso_id}/categorias/{categoria_id}`

`services.py → actualizar_categoria`. Solo se cambian los campos que envíes; un campo en `null` se ignora. Mismas reglas y errores que al crear.

```json
{ "porcentajePeso": 45.5 }
```
**200**: `CategoriaGuardada`, igual que al crear.

#### `DELETE /docente/cursos/{curso_id}/categorias/{categoria_id}`

`services.py → eliminar_categoria`. **200**: el listado actualizado (`CategoriasCurso`), igual que `GET .../categorias`.

**409**: `No se puede eliminar una categoría que ya tiene actividades`.

### Actividades (RF-29, RF-30, RF-33 a RF-36)

Cada actividad pertenece a una categoría del curso. Reglas:

- **RF-34:** las actividades de una categoría **valen lo mismo**, sin importar su `puntuacionMaxima`. `valorEnCurso` es el porcentaje del curso que vale la actividad: peso de la categoría / número de actividades de esa categoría. Con Tareas al 40 % y 3 tareas, cada una vale 13.33. Cambia cuando se agregan o quitan actividades. `services.py → valores_actividades(db, curso_id)` lo calcula para otros módulos.
- La **fecha límite** debe ser posterior a la fecha y hora actuales al crear y al editar. Se guarda en hora local como `"2026-11-01T23:59:00"`. Si llega con zona horaria, se convierte a la hora local del servidor.
- No se crean actividades en un curso archivado.

Campos de `ActividadCrear` (`schemas.py`):

| Campo | Obligatorio | Reglas |
|-------|-------------|--------|
| `categoriaEvaluacion_id` | Sí | Categoría de **este** curso (si no, 404 `Categoría no encontrada`) |
| `titulo` | Sí | 1–100 caracteres |
| `descripcion` | No | Hasta 2000 caracteres |
| `fechaHoraLimite` | Sí | Fecha y hora ISO, p. ej. `"2026-11-01T23:59"`; futura |
| `puntuacionMaxima` | Sí | Mayor que 0 y hasta 1000 |

Respuesta de una actividad (`ActividadSalida`):
```json
{
  "id": 1, "categoriaEvaluacion_id": 2, "categoria": "Tareas",
  "titulo": "Tarea 1", "descripcion": "Resolver ejercicios",
  "fechaHoraLimite": "2026-11-01T23:59:00", "puntuacionMaxima": 10.0,
  "valorEnCurso": 13.33, "tieneArchivo": false
}
```

Errores de actividad (`services.py → _actividad_del_curso`): **404** `Actividad no encontrada` (no existe o es de otro curso).

#### `GET /docente/cursos/{curso_id}/actividades`

`services.py → listar_actividades`. Todas las actividades del curso, ordenadas por fecha límite. **200**: lista de `ActividadSalida`.

#### `POST /docente/cursos/{curso_id}/actividades`

`services.py → crearActividad`.

```json
{
  "categoriaEvaluacion_id": 2, "titulo": "Tarea 1", "descripcion": "Resolver ejercicios",
  "fechaHoraLimite": "2026-11-01T23:59", "puntuacionMaxima": 10
}
```
**201**: `ActividadSalida`.

| Código | `detail` |
|--------|----------|
| 404 | `Categoría no encontrada` |
| 409 | `El curso está archivado` |
| 422 | `La fecha límite debe ser posterior a la fecha y hora actuales` |

#### `GET /docente/cursos/{curso_id}/actividades/{actividad_id}`

`services.py → ver_actividad`. **200**: `ActividadSalida`.

#### `PATCH /docente/cursos/{curso_id}/actividades/{actividad_id}`

`services.py → actualizar_actividad`. Solo se cambian los campos que envíes; un campo en `null` se ignora. Se puede mover la actividad a otra categoría del mismo curso. Mismas reglas que al crear. **200**: `ActividadSalida`.

#### `DELETE /docente/cursos/{curso_id}/actividades/{actividad_id}`

`services.py → eliminar_actividad`. Borra la actividad y su archivo adjunto. **200**: la lista actualizada de actividades del curso, porque el `valorEnCurso` de las demás cambia.

**409**: `No se puede eliminar una actividad que ya tiene entregas`.

#### `PUT /docente/cursos/{curso_id}/actividades/{actividad_id}/archivo`

`routers/docentes.py → adjuntar_archivo` → `services.py → adjuntarArchivoActividad`. Adjunta el archivo del docente (RF-36). Si ya había uno, lo **reemplaza** y borra el anterior.

Se envía como **`multipart/form-data`** con un campo llamado `archivo`, no como JSON. Desde JavaScript:

```js
const datos = new FormData();
datos.append("archivo", input.files[0]);
fetch(`${API}/docente/cursos/${cursoId}/actividades/${actividadId}/archivo`, {
  method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: datos,
});
```
No pongas `Content-Type` a mano: el navegador lo arma con el separador correcto.

**RNF-8:** máximo **10 MB**. Solo `.pdf`, `.doc`, `.docx`, `.png`, `.jpg`, `.jpeg`, `.gif` y `.zip`; se revisa la extensión, sin distinguir mayúsculas. El archivo se guarda en `backend/uploads/actividades/` con un nombre aleatorio. Las constantes están en `config.py` (`CARPETA_ARCHIVOS`, `TAMANO_MAXIMO_ARCHIVO`, `EXTENSIONES_PERMITIDAS`).

**200**: `ActividadSalida` con `"tieneArchivo": true`.

| Código | `detail` |
|--------|----------|
| 413 | `El archivo supera el tamaño máximo de 10 MB` |
| 415 | `Tipo de archivo no permitido. Solo se aceptan PDF, Word (.doc, .docx), imágenes (.png, .jpg, .jpeg, .gif) y ZIP` |
| 422 | `El archivo está vacío` |
| 422 | `Hay datos inválidos en la solicitud` + `errores[]` (no se envió el campo `archivo`) |

#### `DELETE /docente/cursos/{curso_id}/actividades/{actividad_id}/archivo`

`services.py → quitar_archivo_actividad`. Quita y borra el archivo adjunto. **200**: `ActividadSalida` con `"tieneArchivo": false`.

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
