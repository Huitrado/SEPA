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
// Devuelve el JSON de la respuesta o lanza un ErrorApi.
async function pedir(ruta, { metodo = "GET", datos, conToken = false } = {}) {
  const encabezados = {};
  if (datos !== undefined) encabezados["Content-Type"] = "application/json";

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
      body: datos !== undefined ? JSON.stringify(datos) : undefined
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
