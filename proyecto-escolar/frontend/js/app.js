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

// Página a la que se manda a cada usuario según el "panel" que devuelve el login.
// El docente ya tiene su propia pantalla; estudiante y administrador siguen en
// dashboard.html hasta que tengan la suya (solo se cambia aquí).
const PAGINA_POR_PANEL = {
  estudiante: "dashboard.html",
  docente: "docente.html",
  administrador: "dashboard.html"
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

  if (respuesta.ok) return cuerpo;

  const error = new ErrorApi(respuesta.status, cuerpo?.detail || `Error ${respuesta.status}`, cuerpo?.errores);

  // 401 en una petición con token = la sesión expiró o se cerró: volver al login.
  if (respuesta.status === 401 && conToken) {
    irALogin("Tu sesión expiró o ya no es válida. Inicia sesión de nuevo.");
  }
  throw error;
}

// ---------------- Mostrar errores en pantalla ----------------

// Aviso general arriba del formulario. tipo: "error" (rojo) o "info" (azul).
// idAviso permite usar otro recuadro (por ejemplo, uno dentro de una ventana).
function mostrarAviso(texto, tipo = "error", idAviso = "aviso") {
  const aviso = document.getElementById(idAviso);
  if (!aviso) return alert(texto);
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
  window.addEventListener("pageshow", evento => {
    if (evento.persisted) validarSesionDePagina(panelesPermitidos);
  });
  return validarSesionDePagina(panelesPermitidos);
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
