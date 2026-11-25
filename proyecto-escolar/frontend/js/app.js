// ============================================================
// app.js: herramientas que comparten todas las páginas.
//   - La dirección del backend (en UN solo lugar).
//   - Guardar y leer la sesión (token).
//   - pedir(): la única función que habla con el backend.
//   - Mostrar errores en pantalla.
// ============================================================

// Dirección del backend FastAPI. Si cambia el puerto o el servidor,
// solo se modifica esta línea.
const API_URL = "http://127.0.0.1:8000";

// Página a la que se manda a cada usuario según el "panel" que devuelve el login (RF-90).
// dashboard.html queda como "Mi perfil" para estudiante y administrador.
const PAGINA_POR_PANEL = {
  estudiante: "estudiante.html",
  docente: "docente.html",
  administrador: "admin.html"
};

// ---------------- Sesión ----------------
// Se guarda en sessionStorage: dura mientras la pestaña esté abierta
// y se borra sola al cerrarla.

const CLAVE_SESION = "sepa_sesion";

function guardarSesion(datosLogin) {
  const sesion = {
    token: datosLogin.access_token,
    panel: datosLogin.panel,
    nombre: datosLogin.nombre,
    roles: datosLogin.roles
  };
  sessionStorage.setItem(CLAVE_SESION, JSON.stringify(sesion));
  marcarActividad();  // RNF-02: la sesión nueva empieza activa
}

function leerSesion() {
  try {
    return JSON.parse(sessionStorage.getItem(CLAVE_SESION));
  } catch {
    return null;
  }
}

function borrarSesion() {
  sessionStorage.removeItem(CLAVE_SESION);
  sessionStorage.removeItem(CLAVE_ACTIVIDAD);
}

// Manda al login. "motivo" es un texto que el login mostrará al abrir.
function irALogin(motivo) {
  borrarSesion();
  if (motivo) sessionStorage.setItem("sepa_aviso", motivo);
  window.location.href = "login.html";
}

// ---------------- Peticiones al backend ----------------

// Error con la información que manda el backend:
//   status  -> código HTTP (401, 403, 409, 422...). 0 = no hubo conexión.
//   detail  -> mensaje principal (siempre viene).
//   errores -> lista [{campo, mensaje}] (solo en algunos 422).
class ErrorApi extends Error {
  constructor(status, detail, errores) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.errores = errores || [];
  }
}

// Hace una petición al backend.
//   ruta:     por ejemplo "/usuarios/login"
//   opciones: { metodo: "POST", datos: {...}, conToken: true }
//   Si "datos" es un FormData (subir archivos, RF-36), se manda tal cual y el
//   navegador arma el Content-Type multipart; si no, se manda como JSON.
// Devuelve el JSON de la respuesta o lanza un ErrorApi.
async function pedir(ruta, { metodo = "GET", datos, conToken = false } = {}) {
  const encabezados = {};
  const esArchivo = datos instanceof FormData;
  if (datos !== undefined && !esArchivo) encabezados["Content-Type"] = "application/json";

  if (conToken) {
    const sesion = leerSesion();
    if (!sesion) {
      irALogin("Inicia sesión para continuar.");
      throw new ErrorApi(401, "No hay sesión iniciada");
    }
    encabezados["Authorization"] = `Bearer ${sesion.token}`;
  }

  let respuesta;
  try {
    respuesta = await fetch(API_URL + ruta, {
      method: metodo,
      headers: encabezados,
      body: datos === undefined ? undefined : esArchivo ? datos : JSON.stringify(datos)
    });
  } catch {
    throw new ErrorApi(0, `No se pudo conectar con el servidor (${API_URL}). Revisa que el backend esté encendido.`);
  }

  let cuerpo = null;
  try {
    cuerpo = await respuesta.json();
  } catch {
    // La respuesta no traía JSON: se queda en null
  }

  if (respuesta.ok) {
    if (conToken) ultimaPeticionConToken = Date.now();  // RNF-02: el backend ya contó esta actividad
    return cuerpo;
  }

  const error = new ErrorApi(respuesta.status, cuerpo?.detail || `Error ${respuesta.status}`, cuerpo?.errores);

  // 401 en una petición con token = la sesión expiró o se cerró: volver al login.
  // Si el backend la cerró por inactividad (RNF-02), se muestra su mensaje.
  if (respuesta.status === 401 && conToken) {
    irALogin(/inactividad/i.test(error.detail)
      ? MENSAJE_INACTIVIDAD
      : "Tu sesión expiró o ya no es válida. Inicia sesión de nuevo.");
  }
  throw error;
}

// ---------------- Mostrar errores en pantalla ----------------

// Aviso general arriba del formulario. tipo: "error" (rojo) o "info" (azul).
// idAviso permite usar otro recuadro (por ejemplo, uno dentro de una ventana).
function mostrarAviso(texto, tipo = "error", idAviso = "aviso") {
  const aviso = document.getElementById(idAviso);
  if (!aviso) return mostrarToast(texto, tipo);
  aviso.className = tipo === "error"
    ? "mb-space-lg p-space-md rounded-xl bg-error-container text-on-error-container flex items-start gap-space-sm animate-aparecer"
    : "mb-space-lg p-space-md rounded-xl bg-surface-container-low text-on-secondary-container flex items-start gap-space-sm animate-aparecer";
  aviso.querySelector("[data-aviso-icono]").textContent = tipo === "error" ? "error" : "info";
  aviso.querySelector("[data-aviso-texto]").textContent = texto;
}

function ocultarAviso(idAviso = "aviso") {
  document.getElementById(idAviso)?.classList.add("hidden");
}

// Marca un campo en rojo con su mensaje. "campo" es el mismo nombre que usa
// el backend (nombre, correoInstitucional, codigo...), que coincide con el
// atributo name del <input>. Devuelve false si no hay un campo con ese nombre.
function marcarCampo(campo, mensaje) {
  const entrada = document.querySelector(`[name="${campo}"]`);
  const textoError = document.getElementById(`err-${campo}`);
  if (entrada) entrada.classList.add("campo-invalido");
  if (textoError) {
    textoError.querySelector("[data-texto]").textContent = mensaje;
    textoError.classList.remove("hidden");
  }
  return Boolean(entrada || textoError);
}

function limpiarErrores(idAviso = "aviso") {
  ocultarAviso(idAviso);
  document.querySelectorAll(".campo-invalido").forEach(el => el.classList.remove("campo-invalido"));
  document.querySelectorAll('[id^="err-"]').forEach(el => el.classList.add("hidden"));
}

// Muestra un ErrorApi según su código:
//   0   -> sin conexión con el backend
//   401 -> en el login: código o contraseña incorrectos (si había sesión, pedir() ya mandó al login)
//   403 -> sin permiso, o cuenta pendiente/desactivada
//   422 -> campos en rojo (si viene la lista "errores") + aviso general
//   otros (404, 409, 500) -> aviso general con "detail"
function mostrarErrorApi(error, idAviso = "aviso") {
  if (!(error instanceof ErrorApi)) {
    console.error(error);
    mostrarAviso("Ocurrió un error inesperado. Intenta de nuevo.", "error", idAviso);
    return;
  }
  if (error.status === 422 && error.errores.length) {
    const sinCampo = [];
    for (const e of error.errores) {
      if (!marcarCampo(e.campo, e.mensaje)) sinCampo.push(e.mensaje);
    }
    mostrarAviso(sinCampo.length ? sinCampo.join(" · ") : "Revisa los campos marcados en rojo.", "error", idAviso);
    return;
  }
  mostrarAviso(error.detail, "error", idAviso);
}

// Botón de "ojo" para ver u ocultar una contraseña.
// Funciona en cualquier botón con data-ver-contrasena="id-del-input".
function activarBotonesVerContrasena() {
  document.querySelectorAll("[data-ver-contrasena]").forEach(boton => {
    boton.addEventListener("click", () => {
      const entrada = document.getElementById(boton.dataset.verContrasena);
      const icono = boton.querySelector(".material-symbols-outlined");
      const oculta = entrada.type === "password";
      entrada.type = oculta ? "text" : "password";
      icono.textContent = oculta ? "visibility_off" : "visibility";
    });
  });
}

// Pone un botón en "cargando" (spinner) y lo desactiva mientras se espera al backend.
function botonCargando(boton, cargando) {
  boton.disabled = cargando;
  boton.classList.toggle("opacity-80", cargando);
  boton.classList.toggle("cursor-wait", cargando);
  boton.querySelector("[data-texto-boton]").classList.toggle("hidden", cargando);
  boton.querySelector("[data-spinner]").classList.toggle("hidden", !cargando);
}

// ---------------- Páginas protegidas (base común) ----------------
// Toda página que requiere sesión llama a protegerPagina() al cargar:
//   RF-05: valida el token con GET /usuarios/yo; si falla, manda al login.
//   RF-06: si el navegador muestra la página desde su caché con "atrás"
//          (pageshow con event.persisted), la vuelve a validar.
//   RF-90: si el rol del usuario no corresponde a la página, lo manda a la suya.
//   RF-91: llena el nombre del encabezado y activa "Cerrar sesión".
// La página empieza oculta (<html class="validando-sesion">) y solo se muestra
// cuando la sesión es válida, para que no "parpadee" el contenido.
//
// panelesPermitidos: lista de paneles que pueden ver la página, p. ej. ["docente"].
// Devuelve el perfil (o null si se redirigió a otra página).
async function protegerPagina(panelesPermitidos) {
  document.getElementById("btn-logout")?.addEventListener("click", cerrarSesion);
  pintarBarraEstudiante();
  vigilarInactividad();
  window.addEventListener("pageshow", evento => {
    if (evento.persisted) validarSesionDePagina(panelesPermitidos);
  });
  return validarSesionDePagina(panelesPermitidos);
}

// ---------------- Barra del estudiante (igual en todas sus páginas) ----------------
// Las páginas del estudiante ponen <div id="barra-estudiante" data-actual="cursos|asesorias|reglamento|historial">
// en el encabezado. Aquí se llena: en pantallas medianas, los enlaces van en el encabezado;
// en el celular, abajo, cada uno con su ícono y su texto.
const ENLACES_ESTUDIANTE = [
  ["cursos", "estudiante.html", "menu_book", "Mis cursos"],
  ["asesorias", "asesorias.html", "support_agent", "Asesorías"],
  ["reglamento", "normatividad.html", "gavel", "Reglamento"],
  ["historial", "dashboard.html", "history_edu", "Mi historial"]
];

function pintarBarraEstudiante() {
  const barra = document.getElementById("barra-estudiante");
  if (!barra) return;
  const actual = barra.dataset.actual;
  barra.className = "flex items-center gap-space-sm";

  const nav = el("nav", "hidden sm:flex items-center gap-1");
  nav.setAttribute("aria-label", "Secciones del estudiante");
  const abajo = el("nav", "sm:hidden fixed bottom-0 inset-x-0 z-40 bg-surface-container-lowest border-t border-surface-container grid grid-cols-4");
  abajo.setAttribute("aria-label", "Secciones del estudiante");
  for (const [clave, href, nombreIcono, texto] of ENLACES_ESTUDIANTE) {
    const activo = clave === actual;
    const arriba = el("a", `inline-flex items-center gap-1 font-label-md text-label-md px-space-sm py-space-sm rounded-lg transition-colors ${activo ? "bg-secondary-container text-on-secondary-container" : "text-on-surface-variant hover:text-primary"}`);
    arriba.href = href;
    arriba.append(icono(nombreIcono), el("span", "", texto));
    const movil = el("a", `flex flex-col items-center justify-center gap-0.5 py-2 font-caption text-caption ${activo ? "text-primary font-semibold" : "text-on-surface-variant"}`);
    movil.href = href;
    movil.append(icono(nombreIcono, "text-[22px]"), el("span", "", texto));
    if (activo) { arriba.setAttribute("aria-current", "page"); movil.setAttribute("aria-current", "page"); }
    nav.appendChild(arriba);
    abajo.appendChild(movil);
  }

  const nombre = el("span", "hidden lg:inline font-label-lg text-label-lg text-on-surface ml-space-sm");
  nombre.id = "header-nombre";
  const salir = el("button", "inline-flex items-center gap-space-xs font-label-md text-label-md px-space-md py-space-sm rounded-lg text-secondary bg-surface-container-low hover:bg-surface-container transition-colors disabled:opacity-60");
  salir.type = "button";
  salir.id = "btn-logout";
  salir.append(icono("logout"), el("span", "", "Salir"));
  salir.title = "Cerrar sesión";
  salir.addEventListener("click", cerrarSesion);

  barra.replaceChildren(nav, nombre, salir);
  document.body.appendChild(abajo);
  document.body.classList.add("pb-16", "sm:pb-0");  // que la barra de abajo no tape el pie de página
}

async function validarSesionDePagina(panelesPermitidos) {
  const raiz = document.documentElement;
  raiz.classList.add("validando-sesion");

  if (!leerSesion()) {
    irALogin("Inicia sesión para continuar.");
    return null;
  }
  try {
    // Si el token ya no sirve, pedir() responde 401 y manda al login.
    const perfil = await pedir("/usuarios/yo", { conToken: true });
    if (panelesPermitidos && !panelesPermitidos.includes(perfil.panel)) {
      const destino = PAGINA_POR_PANEL[perfil.panel];
      if (destino) window.location.replace(destino);
      else irALogin("Tu cuenta no tiene un rol asignado. Contacta a un administrador.");
      return null;
    }
    const nombre = document.getElementById("header-nombre");
    if (nombre) nombre.textContent = `${perfil.nombre} ${perfil.apellidos}`;
    raiz.classList.remove("validando-sesion");
    return perfil;
  } catch (error) {
    if (error.status !== 401) {
      // Sin conexión u otro error: se muestra la página con el aviso.
      raiz.classList.remove("validando-sesion");
      mostrarErrorApi(error);
    }
    return null;
  }
}

// ---------------- Cierre por inactividad (RNF-02) ----------------
// Mismo tiempo que config.py -> MINUTOS_INACTIVIDAD. El backend también lo revisa:
// aunque esta página se quede abierta sin moverse, el token deja de servir.
//   - Mover el ratón, teclear o tocar cuenta como actividad. Para que el backend también
//     lo sepa, con actividad se le avisa (GET /usuarios/yo) como mucho una vez por minuto.
//   - 2 minutos antes del cierre aparece un aviso con "Seguir conectado".
//   - El cierre ocurre un minuto antes que en el backend, para no chocar con su reloj.
const MINUTOS_INACTIVIDAD = 30;
const MS_CIERRE = (MINUTOS_INACTIVIDAD - 1) * 60 * 1000;
const MS_AVISO = MS_CIERRE - 2 * 60 * 1000;
const MENSAJE_INACTIVIDAD = "Tu sesión se cerró por inactividad. Inicia sesión de nuevo.";
const CLAVE_ACTIVIDAD = "sepa_ultima_actividad";
let ultimaPeticionConToken = Date.now();  // la actualiza pedir()

function marcarActividad() {
  try { sessionStorage.setItem(CLAVE_ACTIVIDAD, String(Date.now())); } catch { /* sin almacenamiento */ }
}

function avisarActividadAlServidor() {
  if (Date.now() - ultimaPeticionConToken < 60 * 1000 || !leerSesion()) return;
  ultimaPeticionConToken = Date.now();
  pedir("/usuarios/yo", { conToken: true }).catch(() => { /* si ya expiró, pedir() manda al login */ });
}

function vigilarInactividad() {
  // Al recargar o cambiar de página se conserva la última actividad de esta pestaña.
  if (!sessionStorage.getItem(CLAVE_ACTIVIDAD)) marcarActividad();
  let ultimoMovimiento = 0;
  const alMoverse = () => {          // como mucho una vez cada 5 s
    const t = Date.now();
    if (t - ultimoMovimiento < 5000) return;
    ultimoMovimiento = t;
    marcarActividad();
    avisarActividadAlServidor();
    ocultarAvisoInactividad();
  };
  for (const evento of ["mousemove", "mousedown", "keydown", "scroll", "touchstart", "wheel"]) {
    window.addEventListener(evento, alMoverse, { passive: true });
  }
  const revisar = async () => {
    const inactivo = Date.now() - (Number(sessionStorage.getItem(CLAVE_ACTIVIDAD)) || Date.now());
    if (inactivo < MS_AVISO) return ocultarAvisoInactividad();
    if (inactivo < MS_CIERRE) return mostrarAvisoInactividad(Math.ceil((MS_CIERRE - inactivo) / 1000));
    clearInterval(reloj);
    const sesion = leerSesion();
    if (sesion) {
      // Se avisa al backend para invalidar el token; si ya no servía, da igual.
      try {
        await fetch(API_URL + "/usuarios/logout", {
          method: "POST", headers: { Authorization: `Bearer ${sesion.token}` }
        });
      } catch { /* sin conexión: el backend lo cerrará solo */ }
    }
    sessionStorage.removeItem(CLAVE_ACTIVIDAD);
    irALogin(MENSAJE_INACTIVIDAD);
  };
  const reloj = setInterval(revisar, 1000);
  // Si la pestaña estuvo en segundo plano (el navegador frena los relojes), revisar al volver.
  document.addEventListener("visibilitychange", () => { if (!document.hidden) revisar(); });
  revisar();
}

function mostrarAvisoInactividad(segundos) {
  let aviso = document.getElementById("aviso-inactividad");
  if (!aviso) {
    aviso = el("div", "fixed z-50 bottom-20 sm:bottom-6 inset-x-4 sm:inset-x-auto sm:right-6 sm:w-96 p-space-md rounded-xl shadow-lg bg-surface-container-lowest border border-surface-container flex items-start gap-space-sm animate-aparecer");
    aviso.id = "aviso-inactividad";
    aviso.setAttribute("role", "alertdialog");
    aviso.setAttribute("aria-live", "assertive");
    const textos = el("div", "flex-1");
    const texto = el("p", "font-body-md text-body-md text-on-surface");
    texto.dataset.texto = "";
    const seguir = boton("Seguir conectado", "touch_app", "primario");
    seguir.classList.add("mt-space-sm");
    seguir.addEventListener("click", () => {
      marcarActividad();
      ultimaPeticionConToken = 0;
      avisarActividadAlServidor();
      ocultarAvisoInactividad();
    });
    textos.append(el("p", "font-label-lg text-label-lg text-primary", "¿Sigues ahí?"), texto, seguir);
    aviso.append(icono("timer", "text-[24px] text-on-tertiary-container"), textos);
    document.body.appendChild(aviso);
  }
  const m = Math.floor(segundos / 60), s = segundos % 60;
  aviso.querySelector("[data-texto]").textContent =
    `Por seguridad, tu sesión se cerrará en ${m ? `${m} min ` : ""}${s} s si no hay actividad.`;
}

function ocultarAvisoInactividad() {
  document.getElementById("aviso-inactividad")?.remove();
}

// ---------------- Mensajes que se cierran solos ----------------
// Para confirmar algo ("Lista guardada") o cuando la página no tiene recuadro #aviso.
function mostrarToast(texto, tipo = "info", segundos = 4) {
  let pila = document.getElementById("pila-toasts");
  if (!pila) {
    pila = el("div", "fixed z-50 bottom-20 sm:bottom-6 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] sm:w-auto sm:max-w-md flex flex-col gap-space-sm pointer-events-none");
    pila.id = "pila-toasts";
    pila.setAttribute("aria-live", "polite");
    document.body.appendChild(pila);
  }
  const error = tipo === "error";
  const toast = el("div", `pointer-events-auto p-space-md rounded-xl shadow-lg flex items-start gap-space-sm animate-aparecer ${error ? "bg-error-container text-on-error-container" : "bg-primary-container text-on-primary"}`);
  toast.setAttribute("role", error ? "alert" : "status");
  toast.append(icono(error ? "error" : "check_circle", "text-[20px]"), el("p", "font-body-md text-body-md", texto));
  pila.appendChild(toast);
  setTimeout(() => toast.remove(), segundos * 1000);
}

async function cerrarSesion() {
  const boton = document.getElementById("btn-logout");
  if (boton) boton.disabled = true;
  try {
    await pedir("/usuarios/logout", { metodo: "POST", conToken: true });
    irALogin("Sesión cerrada correctamente.");
  } catch (error) {
    // 401 = el token ya no era válido; pedir() ya mandó al login.
    if (error.status !== 401) {
      mostrarErrorApi(error);
      if (boton) boton.disabled = false;
    }
  }
}

// ---------------- Descargar archivos (RF-36, RF-41) ----------------
// Un <a href> no manda el token, así que se pide con fetch y se guarda como Blob.
// El nombre sale del encabezado Content-Disposition que pone el backend.
async function descargarArchivo(ruta) {
  const sesion = leerSesion();
  if (!sesion) return irALogin("Inicia sesión para continuar.");
  let respuesta;
  try {
    respuesta = await fetch(API_URL + ruta, { headers: { Authorization: `Bearer ${sesion.token}` } });
  } catch {
    throw new ErrorApi(0, `No se pudo conectar con el servidor (${API_URL}). Revisa que el backend esté encendido.`);
  }
  if (!respuesta.ok) {
    let detalle = `Error ${respuesta.status}`;
    try { detalle = (await respuesta.json()).detail || detalle; } catch { /* sin JSON */ }
    if (respuesta.status === 401) irALogin("Tu sesión expiró o ya no es válida. Inicia sesión de nuevo.");
    throw new ErrorApi(respuesta.status, detalle);
  }
  const disposicion = respuesta.headers.get("Content-Disposition") || "";
  const codificado = disposicion.match(/filename\*=utf-8''([^;]+)/i);
  const simple = disposicion.match(/filename="?([^";]+)"?/i);
  const nombre = codificado ? decodeURIComponent(codificado[1]) : simple ? simple[1] : "archivo";
  const url = URL.createObjectURL(await respuesta.blob());
  const enlace = Object.assign(document.createElement("a"), { href: url, download: nombre });
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------------- Construir la página con JavaScript ----------------

// Crea un elemento con clases y texto (textContent: nunca se interpreta como HTML).
function el(etiqueta, clases = "", texto) {
  const nodo = document.createElement(etiqueta);
  if (clases) nodo.className = clases;
  if (texto !== undefined && texto !== null) nodo.textContent = texto;
  return nodo;
}

function icono(nombre, clases = "text-[18px]") {
  return el("span", `material-symbols-outlined ${clases}`, nombre);
}

// Botón pequeño con ícono y texto. variante: "primario", "secundario", "peligro" o "suave".
function boton(texto, nombreIcono, variante = "suave") {
  const estilos = {
    primario: "bg-primary-container text-on-primary hover:bg-primary",
    secundario: "bg-surface-container-high text-primary hover:bg-surface-container",
    peligro: "bg-surface-container-low text-error hover:bg-error-container",
    suave: "bg-surface-container-low text-secondary hover:bg-surface-container"
  };
  const b = el("button", `inline-flex items-center justify-center gap-space-xs font-label-md text-label-md px-space-md py-space-sm rounded-lg transition-colors disabled:opacity-60 ${estilos[variante]}`);
  b.type = "button";
  if (nombreIcono) b.appendChild(icono(nombreIcono));
  if (texto) b.appendChild(el("span", "", texto));
  return b;
}

// Mismo orden y valores que config.py -> DIAS_SEMANA
const DIAS = [
  ["lunes", "Lun", "Lunes"],
  ["martes", "Mar", "Martes"],
  ["miercoles", "Mié", "Miércoles"],
  ["jueves", "Jue", "Jueves"],
  ["viernes", "Vie", "Viernes"],
  ["sabado", "Sáb", "Sábado"]
];

const ETIQUETA_EVALUACION = {
  numerica: "Calificación numérica",
  aprobado_no_aprobado: "Aprobado / No aprobado"
};

function diasCortos(dias) {
  return DIAS.filter(([valor]) => dias.includes(valor)).map(([, corto]) => corto).join(" · ");
}

// Botón de copiar (RF-14). El botón trae data-copiar con el texto y un <span data-etiqueta>.
async function copiarCodigo(boton) {
  const codigo = boton.dataset.copiar;
  let copiado = false;
  try {
    await navigator.clipboard.writeText(codigo);
    copiado = true;
  } catch {
    // Respaldo para navegadores que no permiten el portapapeles moderno
    const temporal = el("textarea");
    temporal.value = codigo;
    temporal.style.position = "fixed";
    temporal.style.opacity = "0";
    document.body.appendChild(temporal);
    temporal.select();
    try { copiado = document.execCommand("copy"); } catch { copiado = false; }
    temporal.remove();
  }
  const etiqueta = boton.querySelector("[data-etiqueta]");
  const icon = boton.querySelector(".material-symbols-outlined");
  etiqueta.textContent = copiado ? "Copiado" : "No se pudo copiar";
  icon.textContent = copiado ? "check" : "error";
  clearTimeout(boton._temporizador);
  boton._temporizador = setTimeout(() => {
    etiqueta.textContent = "Copiar";
    icon.textContent = "content_copy";
  }, 2000);
}

// ---------------- Fechas ----------------
// El backend manda fechas como texto: "2026-10-26" o "2026-11-01T23:59:00" (hora local del servidor).

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function fechaCorta(texto) {            // "2026-10-26" -> "26 oct"
  const [, mes, dia] = texto.slice(0, 10).split("-").map(Number);
  return `${dia} ${MESES[mes - 1]}`;
}

function fechaHora(texto) {             // "2026-11-01T23:59:00" -> "1 nov 2026, 23:59"
  const [anio, mes, dia] = texto.slice(0, 10).split("-").map(Number);
  return `${dia} ${MESES[mes - 1]} ${anio}, ${texto.slice(11, 16)}`;
}

// Número sin ceros de sobra: 13.333 -> "13.33", 40 -> "40"
function numero(valor, decimales = 2) {
  return Number(valor).toLocaleString("es-MX", { maximumFractionDigits: decimales });
}

// ---------------- Semáforo (RF-50 a RF-52, RF-61) ----------------

const SEMAFORO = {
  verde: { texto: "Verde", clases: "bg-semaforo-verde-fondo text-semaforo-verde", punto: "bg-semaforo-verde" },
  amarillo: { texto: "Amarillo", clases: "bg-semaforo-amarillo-fondo text-semaforo-amarillo", punto: "bg-semaforo-amarillo" },
  rojo: { texto: "Rojo", clases: "bg-semaforo-rojo-fondo text-semaforo-rojo", punto: "bg-semaforo-rojo" }
};

// Etiqueta redonda con el color del semáforo. "texto" reemplaza al nombre del color.
function chipSemaforo(color, texto) {
  const s = SEMAFORO[color] || SEMAFORO.verde;
  const chip = el("span", `inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-label-md text-label-md whitespace-nowrap ${s.clases}`);
  chip.append(el("span", `w-2 h-2 rounded-full ${s.punto}`), el("span", "", texto || s.texto));
  return chip;
}

// ---------------- Ventanas (modales) ----------------
// Cualquier botón con data-cerrar-modal="id" cierra esa ventana; Escape cierra la que esté abierta.

function abrirModal(id) {
  document.getElementById(id).classList.remove("hidden");
}

function cerrarModal(id) {
  document.getElementById(id).classList.add("hidden");
}

function activarModales() {
  document.querySelectorAll("[data-cerrar-modal]").forEach(b =>
    b.addEventListener("click", () => cerrarModal(b.dataset.cerrarModal)));
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") document.querySelectorAll("[data-modal]:not(.hidden)").forEach(m => m.classList.add("hidden"));
  });
}

// Ventana de confirmación con promesa: if (await confirmar("¿Archivar?", "Texto")) {...}
// Usa la ventana #modal-confirmar si la página la tiene; si no, confirm() del navegador.
function confirmar(titulo, texto, textoAceptar = "Confirmar") {
  const modal = document.getElementById("modal-confirmar");
  if (!modal) return Promise.resolve(window.confirm(`${titulo}\n\n${texto}`));
  modal.querySelector("[data-confirmar-titulo]").textContent = titulo;
  modal.querySelector("[data-confirmar-texto]").textContent = texto;
  const aceptar = modal.querySelector("[data-confirmar-aceptar]");
  const cancelar = modal.querySelector("[data-confirmar-cancelar]");
  aceptar.textContent = textoAceptar;
  modal.classList.remove("hidden");
  return new Promise(resolver => {
    const terminar = valor => {
      modal.classList.add("hidden");
      aceptar.onclick = cancelar.onclick = null;
      resolver(valor);
    };
    aceptar.onclick = () => terminar(true);
    cancelar.onclick = () => terminar(false);
  });
}
