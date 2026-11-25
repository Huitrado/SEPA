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
├── dashboard.html       Panel de estudiante y administrador (por ahora, solo el perfil)
├── docente.html         Dashboard del docente: sus cursos y "Crear curso"
├── curso.html           Detalle de un curso del docente (curso.html?id=N), con pestañas
├── actividad.html       Revisar entregas y calificar una actividad (actividad.html?curso=N&actividad=M)
├── estudiante.html      Panel del estudiante: sus cursos del ciclo activo y "Unirse a un curso"
├── curso-alumno.html    Panel consolidado de un curso para el alumno (curso-alumno.html?id=N)
├── entrega.html         Detalle de una actividad y entrega del alumno (entrega.html?curso=N&actividad=M)
├── admin.html           Panel del administrador: inicio, usuarios y roles, ciclos, carreras y materias
├── asesorias.html       Tablero de asesorías para los estudiantes (acepta ?materia=...)
├── mis-asesorias.html   Publicaciones del asesor: crear, editar, ocultar y eliminar
├── normatividad.html    Reglamento: extractos, guía de SIATCE, directorio y "¿Por dónde empiezo?"
├── css/
│   └── style.css        Estilos que Tailwind no trae (campo en rojo, animación)
└── js/
    ├── tailwind-config.js  Colores y tipografía del diseño (para Tailwind)
    ├── app.js              Herramientas comunes: URL del backend, sesión, pedir(), errores,
    │                       protegerPagina(), cerrarSesion(), descargarArchivo(), el(), fechas,
    │                       chipSemaforo() y ventanas (abrirModal, confirmar)
    ├── auth.js             Registro, login y dashboard.html
    ├── docente.js          Dashboard del docente
    ├── curso.js            curso.html: ficha, resumen, pestañas, matrícula y configurar curso
    ├── curso-asistencia.js curso.html: pestaña Asistencia
    ├── curso-evaluacion.js curso.html: pestañas Actividades, Encuadre y Calificaciones
    ├── actividad.js        actividad.html
    ├── estudiante.js       estudiante.html
    ├── curso-alumno.js     curso-alumno.html
    ├── entrega.js          entrega.html
    ├── admin.js            admin.html: secciones, inicio y usuarios
    ├── admin-catalogos.js  admin.html: ciclos, carreras y materias
    ├── asesorias.js        asesorias.html
    ├── mis-asesorias.js    mis-asesorias.html
    ├── normatividad.js     normatividad.html (solo pinta)
    └── normatividad-contenido.js  TEXTO del reglamento: el único archivo que se edita
```

| Pantalla | Qué hace | Lógica en |
|----------|----------|-----------|
| `registro.html` | Formulario con dos pestañas: **Soy estudiante** (código de 9 dígitos, carrera y ciclo de ingreso: el vigente o uno anterior) y **Soy docente** (número de empleado, departamento opcional). | `auth.js → iniciarRegistro`, `enviarRegistro` |
| `login.html` | Pide **código** (de estudiante o número de empleado) y **contraseña**. No se entra con el correo. | `auth.js → iniciarLogin`, `enviarLogin` |
| `dashboard.html` | "Mi perfil" de estudiante y administrador. Al estudiante le muestra además la insignia de **riesgo por historial** (RF-55), su semestre según el ingreso, su plan de estudios y su historial en SEPA, con filtro por ciclo escolar (Todos o un ciclo; solo aparece si hay más de un ciclo). | `auth.js → iniciarPanel`, `mostrarPerfil`, `mostrarTrayectoria`, `pintarHistorialMaterias` |
| `docente.html` | Cursos activos y archivados del docente. Cada tarjeta muestra solo materia, sección, ciclo y **Abrir curso** (el horario y el código están dentro del curso). Ventana **Crear curso**. | `docente.js` |
| `curso.html` | Ficha del curso con su código y cinco pestañas (sin recuadros de resumen: cada dato está en su pestaña, y el promedio de asistencia del grupo aparece en **Asistencia**): **Matrícula** (seguimiento con semáforo y una insignia por cada causa de alerta: **Alerta por asistencia** en amarillo o rojo según su semáforo, **Alerta por calificación**, riesgo de artículos, rezago e historial; dar de baja y reactivar), **Asistencia** (cuadrícula, botón **Pasar lista** para la clase de hoy y corregir listas anteriores tocando su fecha), **Actividades** (por categoría; crear, editar, adjuntar archivo, eliminar), **Encuadre** (categorías y barra del 100 %) y **Calificaciones** (cuadrícula con la acumulada). Botón **Pasar lista**: abre directo la lista de hoy (la genera si no existe; si hoy no hay clase, dice por qué). Botón **Configurar curso** para editarlo, archivarlo o reactivarlo. | `curso.js`, `curso-asistencia.js`, `curso-evaluacion.js` |
| `estudiante.html` | Tarjetas de los cursos del ciclo activo con **solo** materia, profesor y semáforo (el resto está dentro del curso); filtro por color y ventana **Unirse a un curso** con el código. | `estudiante.js` |
| `curso-alumno.html` | Panel del curso, en este orden: semáforo general, alertas, **tareas pendientes** (enlazan a la entrega) e historial de entregas con filtro **Todas · Por calificar · Calificadas**, y debajo calificación acumulada con puntos obtenidos/perdidos, anillo de asistencia con estatus UdeG y encuadre. Sin calificaciones o sin listas guardadas muestra "Aún sin calificaciones" o "Sin clases registradas" en lugar de cifras. Si el semáforo **por calificación** está en amarillo o rojo aparece el botón "Buscar asesoría para esta materia", que abre el tablero ya filtrado (RF-72); si el riesgo es solo por asistencia no aparece. | `curso-alumno.js` |
| `entrega.html` | Instrucciones de la actividad (arriba solo la categoría, sin el porcentaje que vale), archivo del profesor, subir el archivo (arrastrar o elegir), cancelar y volver a subir antes de la fecha límite, y la calificación con retroalimentación. | `entrega.js` |
| `admin.html` | Cuatro secciones: **Inicio** (conteos, docentes por aprobar y **solicitudes para ser asesor**, con Aceptar y Rechazar; al rechazar se puede escribir un comentario que verá el alumno), **Usuarios y roles** (buscar y filtrar; registrar docente o administrador; editar datos; rol de asesor; restablecer contraseña; aprobar, desactivar y reactivar), **Ciclos escolares** (lista con estado y alta con fechas oficiales) y **Carreras y materias** (catálogos; las materias se filtran por plan de estudios, con su semestre, o por "Sin plan de estudios") y **Planes de estudio** (materias por semestre, base del rezago; botón **Nuevo plan** para crear uno vacío o copiando otro: carrera, generación y nombre). En Inicio, el botón **Ejecutar análisis** relanza el análisis de riesgo. | `admin.js`, `admin-catalogos.js` |
| `asesorias.html` | Tarjetas de las asesorías disponibles con filtros por materia, modalidad y texto, y ventana de detalle con el lugar o enlace. Si el alumno es asesor, ve el acceso a "Mis publicaciones". Si no lo es, ve el botón **¿Eres asesor?**, que abre la solicitud y solo pide de qué materias imparte asesorías; con una pendiente ve "Solicitud de asesor en revisión", y si se la rechazaron puede volver a pedirlo y ve el comentario del administrador. | `asesorias.js` |
| `mis-asesorias.html` | Solo para asesores: formulario para publicar o editar (materia del catálogo, horario, modalidad, lugar o enlace, temas) y lista de sus publicaciones con ocultar/volver a publicar y eliminar. | `mis-asesorias.js` |
| `normatividad.html` | Solo estudiantes. Reglamento en seis secciones con índice: **Criterios de evaluación**, **Reglas de asistencia** (`#asistencia`), **Condiciones de permanencia** (`#permanencia`, artículos 33 a 35), **Trámite en SIATCE** (pasos y enlaces), **Directorio de coordinaciones** y **¿Por dónde empiezo?** (`#que-hago`). Lo que aún no tiene texto oficial sale como recuadro punteado "Pendiente" (RF-81 a RF-88). | `normatividad.js`, `normatividad-contenido.js` |
| `actividad.html` | Lista de alumnos con su entrega (filtros: por calificar, calificadas, sin entrega) y panel para descargar la entrega, calificar de 0 al máximo y dejar retroalimentación. "Guardar y siguiente" salta al próximo pendiente. | `actividad.js` |

### Páginas protegidas: `protegerPagina()`

Toda página que requiere sesión empieza con `<html class="validando-sesion">` (se ve en blanco) y al cargar llama a `protegerPagina(["docente"])` de `app.js`, que:

1. Valida el token con `GET /usuarios/yo`; si no sirve, manda al login (RF-05).
2. Si el rol no corresponde a la página, manda al usuario a la suya (RF-90).
3. Llena `#header-nombre` y activa `#btn-logout` (RF-91).
4. Al volver con el botón "atrás" desde la caché del navegador, valida otra vez (RF-06).
5. Vigila la inactividad (RNF-02, `vigilarInactividad`): a los 27 min sin mover el ratón ni teclear avisa "¿Sigues ahí?" con el botón **Seguir conectado**; a los 29 cierra la sesión y manda al login.
6. En las páginas del estudiante, pinta su barra (`pintarBarraEstudiante`).

### Barra del estudiante

Todas las páginas del estudiante (`estudiante`, `curso-alumno`, `entrega`, `asesorias`, `mis-asesorias` y `dashboard` cuando entra un alumno) tienen la **misma** barra: **Mis cursos**, **Asesorías**, **Reglamento** (`normatividad.html`) y **Mi historial** (`dashboard.html`), su nombre y **Salir**. En el HTML solo va un hueco:

```html
<div id="barra-estudiante" data-actual="cursos"></div>   <!-- cursos | asesorias | reglamento | historial -->
```

`app.js → pintarBarraEstudiante` lo llena y marca la sección actual. En pantallas chicas, los cuatro enlaces pasan a una barra fija abajo, cada uno con ícono **y texto**. Para agregar una sección, se agrega una fila a `ENLACES_ESTUDIANTE`.

### Mensajes que se cierran solos

`app.js → mostrarToast(texto, tipo)` muestra un mensaje abajo que desaparece a los 4 s. Se usa para confirmar algo que el usuario acaba de hacer ("Lista guardada", "¡Entrega enviada!", "Te inscribiste…"). Lo que el usuario tiene que leer con calma (un error, un código para compartir) sigue en el recuadro `#aviso` con `mostrarAviso`. Si una página no tiene `#aviso`, `mostrarAviso` usa un toast en lugar de `alert()`.

Solo cuando todo está bien quita `validando-sesion` y la página se muestra.

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

- Después del login, el backend responde con un campo `panel` (`estudiante`, `docente` o `administrador`). La tabla `PAGINA_POR_PANEL` en `js/app.js` dice a qué página mandar a cada uno. **El docente va a `docente.html`, el estudiante a `estudiante.html` y el administrador a `admin.html`.**
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
| Registro | `GET /catalogos/ciclo-actual` | Armar la lista de ciclos de ingreso: el vigente (p. ej. `2026-B`) y los anteriores |
| Registro | `POST /usuarios/registro` | Crear la cuenta |
| Login | `POST /usuarios/login` | Entrar; devuelve el token y el `panel` |
| Login | `GET /usuarios/recuperar-contrasena` | Enlace "¿Olvidaste tu contraseña?": solo muestra instrucciones |
| Panel | `GET /usuarios/yo` | Traer tu perfil (requiere token) |
| Panel | `POST /usuarios/logout` | Cerrar la sesión en el servidor (requiere token) |
| Docente | `GET /docente/cursos?estado=`, `POST /cursos`, `GET /catalogos/ciclos`, `GET /catalogos/materias` | Lista de cursos y crear curso |
| Curso | `GET /docente/cursos/{id}`, `PATCH /docente/cursos/{id}`, `PATCH .../estado` | Ficha, editar, archivar y reactivar |
| Curso · Matrícula | `GET .../alumnos`, `GET .../seguimiento`, `PATCH .../alumnos/{matricula}/estado` | Lista con semáforo, baja y reactivación |
| Curso · Asistencia | `GET .../asistencia`, `POST .../sesiones`, `GET .../sesiones/{id}`, `PUT .../sesiones/{id}/lista` | Cuadrícula y pase de lista |
| Curso · Encuadre | `GET/POST .../categorias`, `PATCH/DELETE .../categorias/{id}` | Categorías y pesos |
| Curso · Actividades | `GET/POST .../actividades`, `PATCH/DELETE .../actividades/{id}`, `PUT/DELETE .../actividades/{id}/archivo`, `GET /actividades/{id}/archivo` | Actividades y archivo adjunto |
| Estudiante | `GET /alumno/cursos`, `POST /inscripcion`, `GET /catalogos/ciclo-actual` | Tarjetas y unirse a un curso |
| Curso del alumno | `GET /alumno/cursos/{id}`, `.../seguimiento`, `.../calificaciones`, `.../encuadre`, `.../actividades` | Panel consolidado |
| Administración | `GET /admin/usuarios`, `POST /admin/docentes`, `POST /admin/administradores`, `PATCH /admin/usuarios/{id}` (y `/estado`, `/asesor`, `/contrasena`), `GET /catalogos/ciclos`, `POST /admin/ciclos`, `GET /catalogos/carreras`, `POST /admin/carreras`, `GET /catalogos/materias`, `POST/PATCH/DELETE /admin/materias` | Panel del administrador |
| Asesorías | `GET /asesorias`, `GET /asesorias/mias`, `POST /asesorias`, `PATCH/DELETE /asesorias/{id}`, `GET /catalogos/materias` | Tablero y publicaciones del asesor |
| Entrega | `POST/DELETE /alumno/actividades/{id}/entrega`, `GET /actividades/{id}/archivo`, `GET /entregas/{id}/archivo` | Subir, cancelar y descargar |
| Curso · Calificaciones y `actividad.html` | `GET .../calificaciones`, `GET .../actividades/{id}/entregas`, `GET /entregas/{id}/archivo`, `PUT .../entregas/{id}/calificacion` | Cuadrícula, revisar y calificar |

Los `...` significan `/docente/cursos/{id}`.

**Archivos:** para subir un archivo se pasa un `FormData` a `pedir()` (no se pone `Content-Type`; lo arma el navegador). Para descargar se usa `descargarArchivo(ruta)`, porque un enlace `<a href>` normal no manda el token.

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

El token dura **8 horas** como máximo, pero se cierra antes si pasan **30 minutos sin actividad** (RNF-02). Más detalle en [docs/backend/04-seguridad.md](../backend/04-seguridad.md).

### 3.5 Cómo se muestran los errores

Cuando algo sale mal, el backend responde con un **código de estado** (un número) y un JSON que **siempre** trae `detail` (el mensaje). Los errores de validación (422) además traen una lista `errores` con `campo` y `mensaje`. Formato completo en [docs/backend/06-errores.md](../backend/06-errores.md).

`app.js → mostrarErrorApi` decide qué hacer:

| Código | Significado | Qué ve el usuario |
|--------|-------------|-------------------|
| sin conexión | El backend está apagado | Aviso: "No se pudo conectar con el servidor…" |
| **401** | No sabemos quién eres | En el login: "Código o contraseña incorrectos". En el panel: te manda al login con "Tu sesión expiró…" |
| **429** | Demasiados intentos de login (RNF-03) | Aviso: "Demasiados intentos fallidos… intenta de nuevo en N minutos" |
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

### Sin VS Code: `servidor.py`

También se puede servir desde una terminal, en la carpeta `frontend`:

```powershell
..\backend\venv\Scripts\python.exe servidor.py
```

y abrir `http://127.0.0.1:5500/login.html`. Usen este en lugar de `python -m http.server`: ese no le dice al navegador que no guarde los archivos, así que al editar un `.js` el navegador sigue usando el viejo hasta borrar la caché. `servidor.py` manda `Cache-Control: no-store` y basta con recargar.

---

## 5. Qué falta o está incompleto (dicho tal cual)

- **Administrador:** ya tiene `admin.html`, incluidos los planes de estudio; `dashboard.html` le sirve como "Mi perfil".
- **Estudiante:** ya tiene sus pantallas (`estudiante.html`, `curso-alumno.html`, `entrega.html`). `dashboard.html` le sirve como "Mi perfil". Ya tiene el tablero de asesorías; si es asesor, también sus publicaciones. La normatividad ya tiene su página, pero con texto pendiente (ver abajo).
- **Docente:** ya tiene sus pantallas completas (`docente.html`, `curso.html` y `actividad.html`).
- **Caché del navegador:** si cambias un `.js` y no ves el cambio, recarga con **Ctrl + Shift + R**.
- **La carpeta `frontend/assets/` está vacía.** Como Git no guarda carpetas vacías, puede que en tu copia ni aparezca.
- **Sin internet no hay diseño:** Tailwind, la tipografía y los íconos se descargan de internet.
- **Textos del diseño original que se quitaron:** el diseño de registro venía de una herramienta de prototipos y traía enlaces (Inicio, Validación, Soporte, Ayuda) y un logo que no existen. Se quitaron.
- **Por confirmar:** el departamento del docente es **opcional** en el formulario porque así lo pide el backend, aunque el diseño original lo marcaba como obligatorio.

---

[Siguiente: 02 · El backend explicado desde cero →](02-backend-como-funciona.md)

## Normatividad: cómo poner el texto del reglamento

La sección de normatividad (RF-81 a RF-88) es **estática**: no usa el backend ni la tabla `BibliotecaNormatividad`. Todo el texto está en **`js/normatividad-contenido.js`**, en la constante `NORMATIVIDAD`. `normatividad.js` solo lo pinta, así que para cambiar el contenido **no hay que tocar HTML ni lógica**.

**Fuentes del contenido actual:** el Reglamento General de Evaluación y Promoción de Alumnos de la UdeG (2017, [PDF oficial](https://secgral.udg.mx/sites/default/files/Normatividad_general/rgepa-oct-2017.pdf)) y las páginas del CUCEI sobre solicitudes de oportunidad por los artículos 33 a 35 y sobre SIATCE. Los artículos están **resumidos en lenguaje sencillo** con su número; el texto literal está en el PDF, que se enlaza desde la página. El directorio tiene los datos de las coordinaciones de ICOM e INFO (coordinador, teléfono, correo y dirección); el teléfono y el correo se pueden tocar para llamar o escribir. Solo falta el enlace del calendario de trámites.

Cada sección tiene `id`, `icono` (nombre de Material Symbols), `titulo`, `resumen` y una lista de `bloques`. Cada bloque puede ser:

| Bloque | Se ve como |
|--------|-----------|
| `"Un párrafo."` | Párrafo normal |
| `{ pendiente: "Qué falta" }` | Recuadro punteado *"Pendiente: Qué falta"* |
| `{ articulo: "Artículo 33", texto: "..." }` | Extracto con el número del artículo y una línea a la izquierda |
| `{ lista: ["...", "..."] }` | Lista con viñetas |
| `{ pasos: ["...", "..."] }` | Pasos numerados (guía de SIATCE) |
| `{ enlaces: [{ texto, url }] }` | Botones que abren otra pestaña; con `url: null` sale "(enlace pendiente)" |
| `{ contactos: [{ carrera, coordinador, correo, ubicacion, horario }] }` | Tarjetas del directorio; un dato en `null` sale como "pendiente" |
| `{ checklist: [{ texto, enlace?, textoEnlace? }] }` | Lista de acciones con un enlace opcional |

Para llenar un hueco, se cambia el `{ pendiente: "..." }` por el texto real. Ejemplo:

```js
// Antes
{ articulo: "Artículo 33", texto: { pendiente: "Texto del artículo 33" } },
// Después
{ articulo: "Artículo 33", texto: "El alumno que no acredite una materia en periodo ordinario..." },
```

**No cambies** los `id` `asistencia`, `permanencia` y `que-hago`: los avisos del panel del curso enlazan a ellos (`curso-alumno.js → pintarAlertas`):

- Aviso por asistencia en amarillo o rojo (RF-83) → **Lee las reglas de asistencia** (`normatividad.html#asistencia`).
- Aviso de artículos 33 a 35 (RF-84) → **Lee las condiciones de permanencia** (`#permanencia`) y **¿Por dónde empiezo?** (`#que-hago`, RF-88).

