# Documentación del backend de SEPA

> Escrita a partir del código de `proyecto-escolar/backend/` (rama `integrar-backend`, octubre 2026).
> Lo que no se pudo confirmar leyendo el código está marcado como **Por confirmar**.

## ¿Qué es SEPA?

SEPA es un sistema escolar web para la Universidad de Guadalajara. Los estudiantes (`@alumnos.udg.mx`) y docentes (`@academicos.udg.mx`) se registran con su correo institucional e inician sesión con su código o número de empleado.
Los docentes crean cursos dentro de un ciclo escolar (2026-A, 2026-B…) y los estudiantes se inscriben con un código de acceso. Los administradores aprueban cuentas y gestionan catálogos, ciclos y usuarios.
Este documento cubre solo el **backend**: la parte que corre en el servidor, guarda los datos y responde al frontend en formato JSON.

## Índice

| # | Archivo | De qué trata |
|---|---------|--------------|
| 1 | [01-tecnologias.md](01-tecnologias.md) | Qué es cada herramienta (FastAPI, SQLAlchemy, Pydantic, bcrypt, JWT, pytest…) con ejemplos de nuestro código |
| 2 | [02-arquitectura.md](02-arquitectura.md) | Carpetas, archivos, capas y el recorrido completo de `POST /usuarios/registro` |
| 3 | [03-base-de-datos.md](03-base-de-datos.md) | Tablas, campos, relaciones (diagrama ER), cómo se crea la base y `crear_admin.py` |
| 4 | [04-seguridad.md](04-seguridad.md) | Contraseñas con bcrypt, tokens JWT, roles, cierre de sesión y `SECRET_KEY` |
| 5 | [05-endpoints.md](05-endpoints.md) | Todos los endpoints: quién los usa, qué reciben y qué responden |
| 6 | [06-errores.md](06-errores.md) | Formato de los errores (422, 401, 403, 404, 409, 500) y dónde se generan |
| 7 | [07-pruebas.md](07-pruebas.md) | Cómo están hechas las pruebas automáticas y cómo agregar una nueva |
| 8 | [08-glosario.md](08-glosario.md) | Términos técnicos explicados en una o dos líneas |

Si es tu primera vez, lee en este orden: **README → 01 → 02 → 05**, y después lo demás según lo necesites.

---

## Cómo correr el backend en Windows, paso a paso

### Requisitos

- **Python 3.10 o más nuevo.** El código usa la sintaxis `str | None`, que no existe en versiones anteriores. El `venv` del equipo fue creado con Python 3.14.
- Una terminal: **PowerShell** (recomendada) o **cmd**.

Todos los comandos se ejecutan **dentro de la carpeta `backend`**. Los archivos se importan entre sí por nombre (`import models`), así que Python debe estar parado ahí.

```powershell
cd "D:\Tareas\Semestre 6 true\Ingenieria de software\ProyectoEscolar\SEPA\proyecto-escolar\backend"
```

### 1. Crear el entorno virtual (venv)

Un *entorno virtual* es una carpeta con una copia aislada de Python y sus librerías, para que las versiones de este proyecto no choquen con otros proyectos.

```powershell
python -m venv venv
```

Esto crea la carpeta `backend\venv\`. Ya está en `.gitignore`, así que no se sube al repositorio. Solo se crea una vez.

### 2. Activar el entorno virtual

Hay que activarlo **cada vez que abras una terminal nueva**.

PowerShell:
```powershell
.\venv\Scripts\Activate.ps1
```

cmd:
```cmd
venv\Scripts\activate.bat
```

Sabrás que funcionó porque el prompt empieza con `(venv)`.

> **Error "la ejecución de scripts está deshabilitada"** en PowerShell: ejecuta
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` y vuelve a activar.
> Esto solo afecta a esa ventana.

### 3. Instalar las dependencias

```powershell
pip install -r requirements.txt
pip install pytest httpx
```

`requirements.txt` instala fastapi, uvicorn, sqlalchemy, email-validator, bcrypt, PyJWT, python-multipart (subida de archivos), pytest y httpx. La segunda línea ya no es necesaria, pero no hace daño.

> **Por confirmar:** `requirements.txt` **no incluye `pytest` ni `httpx`**, y las pruebas los necesitan. `httpx` lo usa por dentro el `TestClient` de FastAPI. Por eso va la segunda línea. Su `venv` actual sí los tiene instalados. Conviene decidir en equipo si se agregan a `requirements.txt` o a un `requirements-dev.txt`.

### 4. Definir la variable `SECRET_KEY`

`SECRET_KEY` es la clave secreta con la que el servidor **firma** los tokens de sesión (ver [04-seguridad.md](04-seguridad.md)). Se lee en `security.py`:

```python
SECRET_KEY = os.environ.get("SECRET_KEY", "clave-de-desarrollo-solo-local")
```

Si no la defines, se usa `"clave-de-desarrollo-solo-local"`. Eso sirve para practicar en tu computadora, pero **nunca** para un servidor real, porque esa clave está publicada en el repositorio.

Genera una clave aleatoria:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Y defínela en la misma terminal donde vas a correr el servidor:

PowerShell:
```powershell
$env:SECRET_KEY = "pega-aqui-la-clave-generada"
```

cmd:
```cmd
set SECRET_KEY=pega-aqui-la-clave-generada
```

La variable dura mientras la terminal siga abierta. Si cambias la clave, todos los tokens que ya se habían entregado dejan de servir y hay que iniciar sesión de nuevo.

#### Variable opcional: `DOCENTE_REQUIERE_APROBACION`

Está en `config.py`. Por defecto vale `1`: un docente que se registra queda en estado `pendiente` hasta que un administrador lo aprueba. Para desactivarlo:

```powershell
$env:DOCENTE_REQUIERE_APROBACION = "0"
```

### 5. Crear el primer administrador

La API no permite crear el primer administrador, porque para crear uno ya hay que ser administrador. Para eso existe un script:

```powershell
python crear_admin.py
```

El script te pide:

1. Nombre
2. Apellidos
3. Correo institucional
4. Número de empleado, que será **tu código para iniciar sesión**
5. Contraseña: no se ve mientras escribes. Debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número.

Si todo sale bien verás algo como:

```
Administrador creado (id 1). Inicia sesión con el código A-001.
```

Además, crea el archivo de base de datos `sistema_escolar.db` (si no existía) y lo llena con los datos iniciales. Más detalle en [03-base-de-datos.md](03-base-de-datos.md#crear_adminpy).

### 6. Arrancar el servidor con Uvicorn

```powershell
uvicorn main:app --reload
```

- `main:app` significa "en el archivo `main.py`, usa la variable `app`".
- `--reload` reinicia el servidor solo cada vez que guardas un `.py`. Úsalo únicamente al desarrollar.

Verás `Uvicorn running on http://127.0.0.1:8000`. Para detenerlo, presiona `Ctrl + C`.

### 7. Probar la API en `/docs`

Abre en el navegador:

- **http://127.0.0.1:8000/docs**: documentación interactiva (Swagger UI). Puedes ejecutar cada endpoint desde ahí.
- http://127.0.0.1:8000/redoc: la misma información con otro diseño.

Para usar un endpoint protegido desde `/docs`:

1. Ejecuta `POST /usuarios/login` con tu código y contraseña.
2. Copia el valor de `access_token` de la respuesta.
3. Haz clic en el botón **Authorize** (arriba a la derecha), pega el token y acepta.
4. A partir de ahí, `/docs` envía el token en cada petición.

### 8. Correr las pruebas automáticas

Con el venv activado y desde la carpeta `backend`:

```powershell
pytest -v
```

`-v` (*verbose*) muestra el nombre de cada prueba. Las pruebas usan una base de datos temporal en memoria, así que **no tocan los datos** de `sistema_escolar.db`. Más detalle en [07-pruebas.md](07-pruebas.md).

### Resumen rápido (las siguientes veces)

```powershell
cd "...\proyecto-escolar\backend"
.\venv\Scripts\Activate.ps1
$env:SECRET_KEY = "tu-clave"
uvicorn main:app --reload
```

### Problemas comunes

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `ModuleNotFoundError: No module named 'fastapi'` | El venv no está activado | Paso 2 |
| `ModuleNotFoundError: No module named 'models'` | Estás en otra carpeta | `cd` a `backend` |
| Al correr `pytest`, un error que menciona `httpx` | Falta httpx | `pip install httpx` |
| El frontend dice "CORS" en la consola | El frontend no se sirve en el puerto 5500 | Ver CORS en [02-arquitectura.md](02-arquitectura.md#mainpy-el-punto-de-arranque) |
| El login funcionaba y de repente da 401 | El token expiró (8 h), se cerró la sesión o cambió `SECRET_KEY` | Inicia sesión de nuevo |

---

## Pendientes "Por confirmar"

Puntos que el código no deja claros. Conviene resolverlos en equipo:

1. **`requirements.txt` incompleto:** faltan `pytest` y `httpx`, que las pruebas necesitan.
2. **401 o 403 sin encabezado `Authorization`:** depende de la versión de FastAPI; la prueba acepta ambos. Ver [04-seguridad.md](04-seguridad.md#3-el-encabezado-authorization).
3. **Contraseñas de más de 72 bytes:** con acentos, una contraseña de 72 caracteres puede pasar la validación y aun así superar el límite de bcrypt. Ver [04-seguridad.md](04-seguridad.md#6-validación-de-contraseñas-rf-03).
4. **Correo del administrador:** `AdminCrear` no restringe el dominio, a diferencia de `DocenteCrear`. ¿Es intencional?
5. **Archivo `.env`:** está en `.gitignore`, pero el código no lo lee; las variables se definen en la terminal.
6. **RF de dos endpoints de administración:** `GET /admin/cursos` y `PATCH /admin/cursos/{curso_id}/docente` no citan ningún RF en el código.
7. **RF-89 y RF-92:** solo aparecen dentro de rangos en comentarios ("RF-01 a RF-07, RF-89 a RF-92" en `services.py` y "RF-89 a RF-93" en `test_registro_login.py`). No hay código ni prueba que los cite por número, así que no sabemos qué cubren.
