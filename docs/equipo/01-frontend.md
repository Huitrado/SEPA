# 01 · Cómo funciona el frontend

> Para: compañeros que nunca han visto SEPA. Lectura: ~10 minutos.
> Siguiente: [02 · El backend explicado desde cero](02-backend-como-funciona.md)

El **frontend** es la parte del sistema que ves en el navegador: las pantallas, los botones y los formularios. Vive en la carpeta `proyecto-escolar/frontend/`.

---

## 1. Las tres piezas: HTML, CSS y JavaScript

| Pieza | Qué es, en una frase | En SEPA |
|-------|---------------------|---------|
| **HTML** | El "esqueleto" de la página: qué textos, campos y botones hay. | `registro.html`, `login.html`, `dashboard.html` |
| **CSS** | La "ropa": colores, tamaños, márgenes y tipografía. | `css/style.css` + Tailwind |
| **JavaScript (JS)** | El "cerebro": reacciona a clics, revisa datos y habla con el backend. | `js/app.js`, `js/auth.js` |

**Tailwind** es una librería de CSS: en lugar de escribir reglas en un `.css`, se ponen clases ya hechas directo en el HTML, por ejemplo `class="bg-primary rounded-lg"` (fondo azul oscuro, esquinas redondeadas). Nosotros la cargamos **desde internet** con esta línea, que está en cada `.html`:

```html
<script src="https://cdn.tailwindcss.com"></script>
```

Por eso **sin internet las páginas se ven sin diseño** (funcionan, pero feas). Lo mismo pasa con la letra Inter y los íconos, que vienen de Google Fonts.

---

## 2. Archivos y pantallas

```
frontend/
├── registro.html        Pantalla "Crear cuenta"
├── login.html           Pantalla "Iniciar sesión"
├── dashboard.html       Panel después de entrar
├── css/
│   └── style.css        Estilos que Tailwind no trae (campo en rojo, animación)
└── js/
    ├── tailwind-config.js  Colores y tipografía del diseño (para Tailwind)
    ├── app.js              Herramientas comunes: URL del backend, sesión, pedir(), errores
    └── auth.js             La lógica de las tres pantallas
```

| Pantalla | Qué hace | Lógica en |
|----------|----------|-----------|
| `registro.html` | Formulario con dos pestañas: **Soy estudiante** (código de 9 dígitos, carrera, ciclo) y **Soy docente** (número de empleado, departamento opcional). | `auth.js → iniciarRegistro`, `enviarRegistro` |
| `login.html` | Pide **código** (de estudiante o número de empleado) y **contraseña**. No se entra con el correo. | `auth.js → iniciarLogin`, `enviarLogin` |
| `dashboard.html` | Muestra tu perfil: nombre, correo, código y roles. Tiene el botón **Cerrar sesión**. | `auth.js → iniciarPanel`, `mostrarPerfil`, `cerrarSesion` |

¿Cómo sabe `auth.js` en qué pantalla está? Cada página lo dice en su etiqueta `<body>`:

```html
<body class="bg-surface font-body-md text-on-surface antialiased" data-pagina="login">
```

y al cargar, `auth.js` ejecuta la función que toca (está al inicio del archivo, en el `DOMContentLoaded`).

### Cómo se navega entre pantallas

```mermaid
flowchart LR
    R["registro.html"] -- "Inicia sesión" --> L["login.html"]
    L -- "Regístrate" --> R
    L -- "Login correcto" --> D["dashboard.html"]
    D -- "Cerrar sesión" --> L
    D -- "Sesión vencida (401)" --> L
    L -- "Ya había sesión abierta" --> D
```

- Después del login, el backend responde con un campo `panel` (`estudiante`, `docente` o `administrador`). La tabla `PAGINA_POR_PANEL` en `js/app.js` dice a qué página mandar a cada uno. **Hoy los tres van a `dashboard.html`.**
- Si abres `dashboard.html` sin haber iniciado sesión, te regresa al login.

---

## 3. Cómo habla el frontend con el backend

El frontend **no guarda datos**: todo se lo pide al backend, que es un programa aparte (ver el [documento 02](02-backend-como-funciona.md)).

### 3.1 La dirección del backend: una sola constante

En `js/app.js`:

```js
const API_URL = "http://127.0.0.1:8000";
```

Es la **única** línea con la dirección del backend. Si el backend cambia de puerto o de servidor, solo se cambia aquí.

### 3.2 `fetch` y JSON

- **`fetch`** es la función del navegador para mandar una petición a otro programa por internet (o en tu misma computadora) y esperar la respuesta.
- **JSON** es el formato de texto en el que viajan los datos, por ejemplo `{"codigo": "123456789", "contrasena": "Secreto123"}`.

Nadie llama a `fetch` directamente: todo pasa por **una sola función**, `pedir()`, en `js/app.js`. Así, el manejo del token y de los errores se escribe una vez. Ejemplo real del login (`auth.js → enviarLogin`):

```js
const respuesta = await pedir("/usuarios/login", { metodo: "POST", datos });
```

### 3.3 Qué endpoints usa cada pantalla

Un **endpoint** es una "ventanilla" del backend: un método (GET, POST…) más una ruta.

| Pantalla | Endpoint | Para qué |
|----------|----------|----------|
| Registro | `GET /catalogos/carreras` | Llenar la lista de carreras |
| Registro | `GET /catalogos/ciclo-actual` | Mostrar el ciclo escolar en curso (p. ej. `2026-B`) |
| Registro | `POST /usuarios/registro` | Crear la cuenta |
| Login | `POST /usuarios/login` | Entrar; devuelve el token y el `panel` |
| Login | `GET /usuarios/recuperar-contrasena` | Enlace "¿Olvidaste tu contraseña?": solo muestra instrucciones |
| Panel | `GET /usuarios/yo` | Traer tu perfil (requiere token) |
| Panel | `POST /usuarios/logout` | Cerrar la sesión en el servidor (requiere token) |

La lista completa de endpoints del backend está en [docs/backend/05-endpoints.md](../backend/05-endpoints.md).

### 3.4 El token: tu "pulsera" de acceso

1. Al iniciar sesión, el backend devuelve un **token**: un texto largo que demuestra que ya te identificaste (como la pulsera de un evento).
2. `js/app.js → guardarSesion` lo guarda en **`sessionStorage`**, una pequeña memoria del navegador que **se borra al cerrar la pestaña**.
3. En cada petición protegida, `pedir()` lo agrega en un **encabezado** (información extra que viaja junto a la petición):

   ```
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   ```

   Esto pasa cuando se llama `pedir(ruta, { conToken: true })`.
4. Al cerrar sesión, el backend "anula" ese token y el frontend lo borra (`app.js → borrarSesion`).

El token dura **8 horas**. Más detalle en [docs/backend/04-seguridad.md](../backend/04-seguridad.md).

### 3.5 Cómo se muestran los errores

Cuando algo sale mal, el backend responde con un **código de estado** (un número) y un JSON que **siempre** trae `detail` (el mensaje). Los errores de validación (422) además traen una lista `errores` con `campo` y `mensaje`. Formato completo en [docs/backend/06-errores.md](../backend/06-errores.md).

`app.js → mostrarErrorApi` decide qué hacer:

| Código | Significado | Qué ve el usuario |
|--------|-------------|-------------------|
| sin conexión | El backend está apagado | Aviso: "No se pudo conectar con el servidor…" |
| **401** | No sabemos quién eres | En el login: "Código o contraseña incorrectos". En el panel: te manda al login con "Tu sesión expiró…" |
| **403** | Sabemos quién eres, pero no puedes | Aviso con el motivo, p. ej. "Tu cuenta está pendiente de aprobación…" |
| **409** | Choque con algo que ya existe | Aviso, p. ej. "El correo institucional ya está registrado" |
| **422** | Datos inválidos | Cada campo se marca **en rojo** con su mensaje (`app.js → marcarCampo`) |

Truco del código: los `<input>` usan como `name` **el mismo nombre de campo que el backend** (`nombre`, `correoInstitucional`, `codigo`…). Así, cuando el backend dice `{"campo": "nombre", ...}`, `marcarCampo` encuentra el campo solito.

Además, `registro.html` revisa algunas cosas **antes** de llamar al backend (`auth.js → validarRegistro`): dominio del correo según la pestaña, reglas de contraseña, código de 9 dígitos y la casilla de aceptación. El backend vuelve a revisar todo; esto solo da avisos más rápidos.

---

## 4. Cómo abrirlo: Live Server en el puerto 5500

**Live Server** es una extensión de VS Code que "sirve" tus archivos HTML como si fueran una página web real, en una dirección como `http://127.0.0.1:5500/login.html`. (Instalarla: ver el [documento 03](03-backend-como-trabajar.md#1-instalar-lo-necesario-en-windows).)

Pasos:

1. Arranca primero el **backend** (pasos en el [documento 03](03-backend-como-trabajar.md#3-arrancar-el-backend-paso-a-paso)).
2. En VS Code, abre la carpeta del repositorio.
3. Clic derecho sobre `proyecto-escolar/frontend/login.html` → **Open with Live Server**.
4. Se abre el navegador. Revisa que la dirección diga **`:5500`**.

### ¿Por qué tiene que ser el puerto 5500? (CORS)

Un **puerto** es como el número de departamento dentro de un edificio: la computadora es el edificio (`127.0.0.1`), y cada programa atiende en su propio número. El backend vive en el 8000 y Live Server en el 5500.

Por seguridad, el navegador **bloquea** que una página le pida datos a otra dirección, salvo que esa otra dirección diga "a ti sí te atiendo". Esa regla se llama **CORS**. Nuestro backend solo da permiso a dos direcciones (en `backend/main.py`):

```python
allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
```

Si abres el frontend en otro puerto (o haciendo doble clic sobre el `.html`, que da una dirección `file:///...`), verás en la consola del navegador (F12) un error que menciona **CORS** y nada funcionará.

> Si Live Server elige otro puerto porque el 5500 está ocupado, cierra lo que lo esté usando, o fija el puerto en VS Code: Configuración → busca `liveServer.settings.port` → `5500`.

---

## 5. Qué falta o está incompleto (dicho tal cual)

- **El panel es mínimo:** `dashboard.html` solo muestra el perfil y el botón de cerrar sesión. Es igual para estudiante, docente y administrador.
- **No hay pantallas** para cursos, inscripción ni administración, aunque **el backend ya tiene esos endpoints** (crear curso, inscribirse con código, aprobar docentes, etc.). Es trabajo pendiente del frontend.
- **La carpeta `frontend/assets/` está vacía.** Como Git no guarda carpetas vacías, puede que en tu copia ni aparezca.
- **Sin internet no hay diseño:** Tailwind, la tipografía y los íconos se descargan de internet.
- **Textos del diseño original que se quitaron:** el diseño de registro venía de una herramienta de prototipos y traía enlaces (Inicio, Validación, Soporte, Ayuda) y un logo que no existen. Se quitaron.
- **Por confirmar:** el departamento del docente es **opcional** en el formulario porque así lo pide el backend, aunque el diseño original lo marcaba como obligatorio.

---

[Siguiente: 02 · El backend explicado desde cero →](02-backend-como-funciona.md)
