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
// Por ahora los tres usan dashboard.html; si después hay una página por rol,
// solo se cambia aquí.
const PAGINA_POR_PANEL = {
  estudiante: "dashboard.html",
  docente: "dashboard.html",
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
function mostrarAviso(texto, tipo = "error") {
  const aviso = document.getElementById("aviso");
  if (!aviso) return alert(texto);
  aviso.className = tipo === "error"
    ? "mb-space-lg p-space-md rounded-xl bg-error-container text-on-error-container flex items-start gap-space-sm animate-aparecer"
    : "mb-space-lg p-space-md rounded-xl bg-surface-container-low text-on-secondary-container flex items-start gap-space-sm animate-aparecer";
  aviso.querySelector("[data-aviso-icono]").textContent = tipo === "error" ? "error" : "info";
  aviso.querySelector("[data-aviso-texto]").textContent = texto;
}

function ocultarAviso() {
  document.getElementById("aviso")?.classList.add("hidden");
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

function limpiarErrores() {
  ocultarAviso();
  document.querySelectorAll(".campo-invalido").forEach(el => el.classList.remove("campo-invalido"));
  document.querySelectorAll('[id^="err-"]').forEach(el => el.classList.add("hidden"));
}

// Muestra un ErrorApi según su código:
//   0   -> sin conexión con el backend
//   401 -> en el login: código o contraseña incorrectos (si había sesión, pedir() ya mandó al login)
//   403 -> sin permiso, o cuenta pendiente/desactivada
//   422 -> campos en rojo (si viene la lista "errores") + aviso general
//   otros (404, 409, 500) -> aviso general con "detail"
function mostrarErrorApi(error) {
  if (!(error instanceof ErrorApi)) {
    console.error(error);
    mostrarAviso("Ocurrió un error inesperado. Intenta de nuevo.");
    return;
  }
  if (error.status === 422 && error.errores.length) {
    const sinCampo = [];
    for (const e of error.errores) {
      if (!marcarCampo(e.campo, e.mensaje)) sinCampo.push(e.mensaje);
    }
    mostrarAviso(sinCampo.length ? sinCampo.join(" · ") : "Revisa los campos marcados en rojo.");
    return;
  }
  mostrarAviso(error.detail);
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
