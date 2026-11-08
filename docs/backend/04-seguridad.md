# 04 · Seguridad

[← Volver al índice](README.md)

Casi todo vive en **`security.py`**, con apoyo de `schemas.py` (reglas de contraseña) y `services.py` (login y logout).

---

## 1. Cómo se guardan las contraseñas (bcrypt)

### El problema

Si la base de datos guardara `"Secreto123"` tal cual, cualquiera con acceso al archivo `.db` (un compañero, un respaldo robado) vería todas las contraseñas. Y como mucha gente repite contraseñas, el daño saldría del sistema.

### La solución: hash con sal

Un **hash** es una función de un solo sentido: de la contraseña sale un texto, pero de ese texto no se puede regresar a la contraseña. **bcrypt** además:

- **Agrega una sal:** un valor aleatorio distinto cada vez. Si Ana y Beto usan `"Secreto123"`, sus hashes son diferentes, y nadie puede usar tablas precalculadas de hashes.
- **Es lento a propósito:** cada intento tarda una fracción de segundo. Para ti es imperceptible, pero probar millones de contraseñas se vuelve imposible.
- **Guarda todo en un solo texto:** el resultado incluye el algoritmo, el costo y la sal. Ejemplo: `$2b$12$` + 22 caracteres de sal + 31 de hash.

### En nuestro código: `security.py`

```python
def hashear(contrasena: str) -> str:
    return bcrypt.hashpw(contrasena.encode(), bcrypt.gensalt()).decode()

def verificar(contrasena: str, hash_guardado: str) -> bool:
    return bcrypt.checkpw(contrasena.encode(), hash_guardado.encode())
```

- `hashear` se usa al **guardar**: `services.py → registrarse`, `_crear_personal` y `recuperarContrasena`.
- `verificar` se usa al **iniciar sesión**: `services.py → iniciarSesion`. bcrypt saca la sal del hash guardado, vuelve a calcular el hash con la contraseña escrita y compara.
- `.encode()` convierte el texto a bytes, porque bcrypt trabaja con bytes.

### Detalle: no revelar qué códigos existen

En `services.py`:

```python
_HASH_FALSO = hashear("contrasena-falsa")
...
def iniciarSesion(db, cred):
    usuarios = [db.get(models.Usuario, i) for i in _ids_por_codigo(db, cred.codigo)]
    if not usuarios:
        verificar(cred.contrasena, _HASH_FALSO)
```

Si el código no existe, el servidor **igual ejecuta bcrypt** contra un hash falso. Sin esto, un código inexistente respondería más rápido que uno real, y un atacante podría medir el tiempo de respuesta para averiguar qué códigos están registrados. Además, el mensaje es el mismo en ambos casos: `"Código o contraseña incorrectos"` (RF-04, lo comprueba `test_rf04_datos_incorrectos_no_revelan_cual_fallo`).

---

## 2. Qué es un JWT y cómo lo usamos

### Qué es

Un **JWT** (*JSON Web Token*) es un texto de tres partes separadas por puntos:

```
eyJhbGciOiJIUzI1NiIs...   .   eyJzdWIiOiIxIiwiZXhwIjox...   .   SflKxwRJSMeKKF2QT4fwpM...
       encabezado                    contenido (payload)                    firma
```

- **Encabezado:** qué algoritmo firma el token. Aquí es `HS256`.
- **Payload:** los datos, en JSON codificado en *base64*. Base64 **no es cifrado**: cualquiera puede leerlo en jwt.io. Por eso nunca se mete información secreta en el payload.
- **Firma:** se calcula con el encabezado, el payload y la **`SECRET_KEY`**. Si alguien cambia un solo carácter del payload (por ejemplo `"sub": "1"` → `"sub": "2"` para hacerse pasar por otro), la firma ya no coincide y el servidor rechaza el token.

### Qué contiene nuestro token: `security.py → crear_token`

```python
SECRET_KEY = os.environ.get("SECRET_KEY", "clave-de-desarrollo-solo-local")
ALGORITMO = "HS256"
HORAS_SESION = 8

def crear_token(usuario_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=HORAS_SESION)
    return jwt.encode({"sub": str(usuario_id), "exp": exp, "jti": uuid.uuid4().hex}, SECRET_KEY, ALGORITMO)
```

| Campo | Significado | Valor |
|-------|-------------|-------|
| `sub` (*subject*) | A quién pertenece | El `id` del usuario, como texto |
| `exp` (*expiration*) | Cuándo vence | **8 horas** después del login |
| `jti` (*JWT ID*) | Identificador único de esta sesión | 32 caracteres aleatorios; sirve para cerrar la sesión (RF-06) |

Ejemplo de payload ya decodificado:

```json
{ "sub": "1", "exp": 1793120400, "jti": "3f9a1c0e8b7d4e2fa6c5b1d09e8f7a6b" }
```

`exp` va en segundos desde el 1 de enero de 1970 (formato estándar de JWT).

### El flujo completo

```mermaid
sequenceDiagram
    autonumber
    actor F as Frontend
    participant API as API SEPA
    participant DB as SQLite

    F->>API: POST /usuarios/login {codigo, contrasena}
    API->>DB: busca el código en Estudiante, Docente y Administrador
    API->>API: bcrypt.checkpw
    API->>API: revisa estado (pendiente → 403, inactivo → 403)
    API-->>F: 200 {access_token, token_type: "bearer", roles, panel, nombre}
    Note over F: Guarda el token (p. ej. en memoria o localStorage)

    F->>API: GET /usuarios/yo<br/>Authorization: Bearer eyJ...
    API->>API: verifica firma y exp (datos_token)
    API->>DB: ¿jti en TokenRevocado?
    API->>DB: carga Usuario, revisa estado activo (usuario_actual)
    API-->>F: 200 {perfil}

    F->>API: POST /usuarios/logout<br/>Authorization: Bearer eyJ...
    API->>DB: INSERT TokenRevocado(jti)
    API-->>F: 200 {"mensaje": "Sesión cerrada correctamente"}

    F->>API: GET /usuarios/yo (mismo token)
    API->>DB: jti está revocado
    API-->>F: 401 "La sesión ya no es válida#59; inicia sesión de nuevo"
```

### Login: `POST /usuarios/login` (`services.py → iniciarSesion`)

1. **Se entra con el código, no con el correo** (RF-04). El código es el de estudiante (9 dígitos) o el número de empleado (docente o administrador). Se pasa a mayúsculas, así que `d-001` y `D-001` son lo mismo.
2. `_ids_por_codigo` busca ese código en las tres tablas de perfil.
3. Se verifica la contraseña con bcrypt. Si falla → **401** `"Código o contraseña incorrectos"`.
4. Solo **con la contraseña correcta** se revela el estado de la cuenta:
   - `pendiente` → **403** `"Tu cuenta está pendiente de aprobación por un administrador"`.
   - `inactivo` → **403** `"Tu cuenta está desactivada"`.
5. Si todo está bien, responde:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "roles": ["estudiante"],
  "panel": "estudiante",
  "nombre": "Ana López"
}
```

`panel` (RF-90) indica al frontend a qué pantalla de inicio mandar al usuario. Si tuviera varios roles, gana el de mayor prioridad según `config.py → PRIORIDAD_PANEL`: administrador > docente > estudiante.

### Duración

`HORAS_SESION = 8`. Pasadas 8 horas, PyJWT rechaza el token al decodificarlo y la API responde **401** `"Sesión inválida o expirada"`. No existe un endpoint para renovar el token: hay que volver a iniciar sesión.

---

## 3. El encabezado `Authorization`

En cada petición a un endpoint protegido, el frontend debe mandar:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

*Bearer* significa "portador": quien porta el token tiene acceso. Por eso el token se cuida como una contraseña.

Ejemplo con `fetch` desde el frontend:

```js
const r = await fetch("http://127.0.0.1:8000/usuarios/yo", {
  headers: { Authorization: `Bearer ${token}` },
});
```

En el backend, `security.py` lee el encabezado con:

```python
bearer = HTTPBearer()
```

`HTTPBearer` es una utilidad de FastAPI que extrae el token del encabezado. Si el encabezado **no viene**, FastAPI responde de inmediato con `{"detail": "Not authenticated"}`, antes de llegar a nuestro código. Si viene con otro esquema (por ejemplo `Token abc` en vez de `Bearer abc`), el mensaje es `"Invalid authentication credentials"`. Estos dos mensajes están en inglés porque los genera FastAPI, no `errores.py`.

> **Por confirmar:** el código de estado cuando **falta** el encabezado. Las versiones recientes de FastAPI responden **401** y las antiguas respondían **403**. La prueba `test_rf05_acceso_protegido` acepta los dos (`in (401, 403)`). Con la versión de su `venv` (FastAPI 0.162) debería ser 401, pero no se pudo ejecutar para confirmarlo.

---

## 4. Cómo se verifica el rol

FastAPI permite **encadenar dependencias**: una función de seguridad puede depender de otra. En `security.py` hay cuatro, cada una construida sobre la anterior:

```mermaid
flowchart LR
    A["bearer = HTTPBearer()<br/>extrae el token del encabezado"] --> B["datos_token<br/>firma, vencimiento, jti no revocado"]
    B --> C["usuario_actual<br/>el usuario existe y está activo"]
    C --> D1["requiere_admin<br/>hay fila en Administrador"]
    C --> D2["requiere_docente<br/>hay fila en Docente"]
```

| Dependencia | Qué revisa | Si falla |
|-------------|-----------|----------|
| `datos_token` | Que la firma sea válida y no haya expirado (`jwt.decode`) | 401 `"Sesión inválida o expirada"` |
| | Que tenga `jti` y que no esté en `TokenRevocado` | 401 `"La sesión ya no es válida; inicia sesión de nuevo"` |
| `usuario_actual` | Que `sub` sea un número | 401 `"Sesión inválida"` |
| | Que el usuario exista y su `estado` sea `activo` | 401 `"Usuario no válido"` |
| `requiere_admin` | Que exista una fila en `Administrador` con ese `id` | 403 `"Se requiere rol de administrador"` |
| `requiere_docente` | Que exista una fila en `Docente` con ese `id` | 403 `"Se requiere rol de docente"` |

Así se usan en un router (`routers/admin.py`):

```python
@router.post("/carreras", ...)
def crear_carrera(datos: schemas.CarreraCrear, db: Session = Depends(get_db),
                  _: models.Usuario = Depends(requiere_admin)):
```

El parámetro se llama `_` porque la función no usa el administrador; solo importa que la verificación pase.

**Puntos importantes:**

- **Los permisos se revisan con las tablas de perfil** (`Administrador`, `Docente`), **no** con la tabla `Rol`/`UsuarioRol`. Los roles de `UsuarioRol` solo se usan para `roles` y `panel` en las respuestas.
- **Desactivar una cuenta corta el acceso de inmediato:** `usuario_actual` revisa `estado == "activo"` en **cada** petición, así que un token emitido antes de la desactivación deja de servir.
- **Para estudiantes no hay `requiere_estudiante`.** `POST /inscripcion` usa `usuario_actual` y es `services.py → inscribirseCurso` quien revisa que exista una fila en `Estudiante` (si no, 403).
- **Ser dueño del curso** (RF-95) **no** lo revisa `security.py` sino `services.py → _curso_del_docente`: si `curso.docente_id` no es el del docente → 403 `"Este curso no te pertenece"`. Un administrador que no sea docente recibe 403 desde antes, en `requiere_docente`.
- **RF-96** (el alumno no puede crear ni editar cursos ni ciclos) se cumple porque esas rutas exigen `requiere_docente` o `requiere_admin`.

---

## 5. Cómo funciona el logout

**El problema:** un JWT es válido hasta que expira, y el servidor no lo "guarda" en ningún lado. Si el frontend solo borrara el token, alguien que lo hubiera copiado podría seguir usándolo hasta 8 horas.

**La solución (RF-06, RF-91): lista de tokens revocados.** `services.py → cerrarSesion`:

```python
def cerrarSesion(db, payload):
    jti = payload["jti"]
    if not db.get(models.TokenRevocado, jti):
        expira = datetime.fromtimestamp(payload["exp"], timezone.utc).isoformat()
        db.add(models.TokenRevocado(jti=jti, expira=expira))
    # limpieza: un token expirado ya es inválido por sí solo
    db.query(models.TokenRevocado).filter(
        models.TokenRevocado.expira < datetime.now(timezone.utc).isoformat()).delete()
    db.commit()
```

1. Guarda el `jti` de la sesión en `TokenRevocado`.
2. A partir de ahí, `datos_token` rechaza cualquier petición con ese token (401).
3. **Limpieza:** borra los registros de tokens que ya expiraron, porque esos se rechazan solos por `exp` y no hace falta recordarlos.
4. Iniciar sesión otra vez genera un `jti` nuevo, así que la nueva sesión funciona (`test_rf06_logout_invalida_la_sesion`).

Detalles:

- El endpoint `/usuarios/logout` depende de `datos_token`, **no** de `usuario_actual`. Por eso un usuario desactivado también puede cerrar sesión.
- Llamar a logout **dos veces** con el mismo token: la segunda vez responde 401, porque el token ya está revocado.
- El encabezado `Cache-Control: no-store` (middleware `sin_cache` en `main.py`) complementa el RF-06: el navegador no guarda respuestas que se pudieran ver con el botón "atrás".

---

## 6. Validación de contraseñas (RF-03)

Se aplica en `schemas.py → _contrasena`, a través del tipo `Contrasena`, que se usa en `UsuarioCrear`, `PersonalCrear` (docentes y administradores) y `NuevaContrasena` (restablecimiento):

| Regla | Mensaje de error |
|-------|------------------|
| Al menos 8 caracteres | `La contraseña debe tener al menos 8 caracteres` |
| Máximo 72 caracteres | `La contraseña no puede tener más de 72 caracteres` |
| Al menos una minúscula | `La contraseña debe incluir al menos una letra minúscula` |
| Al menos una mayúscula | `La contraseña debe incluir al menos una letra mayúscula` |
| Al menos un número | `La contraseña debe incluir al menos un número` |
| En el registro: debe coincidir con `confirmarContrasena` | `La contraseña y su confirmación no coinciden` |

**¿Por qué máximo 72?** bcrypt solo toma en cuenta los primeros 72 bytes de la contraseña. Con más, dos contraseñas distintas que comparten los primeros 72 bytes darían el mismo hash. Las versiones recientes de la librería `bcrypt` incluso lanzan error. El límite evita ambos problemas.

> Nota: `len(v)` cuenta **caracteres**, pero bcrypt cuenta **bytes**. Una letra con acento (`á`) ocupa 2 bytes, así que una contraseña de 72 caracteres con acentos pasaría la validación y superaría los 72 bytes. **Por confirmar** si esto puede causar un error al hashear con la versión de bcrypt del proyecto (5.0.0).

El **login** no aplica estas reglas: `UsuarioLogin.contrasena` solo exige que no esté vacía. Tiene sentido, porque solo se compara.

### Restablecer la contraseña (RF-07)

No existe un "olvidé mi contraseña" automático:

- `GET /usuarios/recuperar-contrasena` solo devuelve el mensaje de `config.py → MENSAJE_RECUPERACION`: comunicarse con el coordinador o un administrador.
- El administrador usa `PATCH /admin/usuarios/{usuario_id}/contrasena` (`services.py → recuperarContrasena`), que aplica las mismas reglas de RF-03.

---

## 7. Por qué `SECRET_KEY` se lee de una variable de entorno

```python
SECRET_KEY = os.environ.get("SECRET_KEY", "clave-de-desarrollo-solo-local")
```

- **Quien conoce la `SECRET_KEY` puede fabricar tokens válidos** para cualquier usuario, incluido un administrador, sin saber ninguna contraseña. Es la llave maestra del sistema.
- Si estuviera escrita en el código, estaría en GitHub y cualquiera con acceso al repositorio la tendría.
- Una **variable de entorno** es un valor que se configura en el sistema operativo o en la terminal, fuera del código. Así cada ambiente (tu laptop, el servidor de la escuela) tiene su propia clave y ninguna queda en Git. Por eso `.env` está en `.gitignore`.
- El valor por defecto `"clave-de-desarrollo-solo-local"` existe para que el proyecto arranque sin configurar nada al desarrollar. **Como es público, en un servidor real hay que definir siempre `SECRET_KEY`.**
- Si se cambia la `SECRET_KEY`, todos los tokens existentes dejan de ser válidos y todos deben volver a iniciar sesión.

Cómo definirla en Windows: ver [README.md](README.md#4-definir-la-variable-secret_key).

> **Por confirmar:** el código no lee archivos `.env` (no usa `python-dotenv`). Aunque `.gitignore` menciona `.env`, crear ese archivo **no** basta: la variable se debe definir en la terminal.

[← Base de datos](03-base-de-datos.md) · [Volver al índice](README.md) · [Siguiente: Endpoints →](05-endpoints.md)
