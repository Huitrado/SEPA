// ============================================================
// auth.js: lógica de las tres pantallas.
//   - registro.html  -> POST /usuarios/registro (+ catálogos de carreras y ciclo)
//   - login.html     -> POST /usuarios/login
//   - dashboard.html -> GET /usuarios/yo y POST /usuarios/logout
// Usa las herramientas de app.js (pedir, mostrarAviso, marcarCampo...).
// Cada página indica quién es con <body data-pagina="...">.
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  activarBotonesVerContrasena();
  const pagina = document.body.dataset.pagina;
  if (pagina === "registro") iniciarRegistro();
  if (pagina === "login") iniciarLogin();
  if (pagina === "panel") iniciarPanel();
});

// ==================== REGISTRO ====================

// El backend decide el rol por el dominio del correo (config.py -> DOMINIOS_ROL).
// La pestaña solo cambia qué campos se ven; abajo revisamos que coincidan.
const DOMINIO_POR_ROL = {
  estudiante: "alumnos.udg.mx",
  docente: "academicos.udg.mx"
};

let rolElegido = "estudiante";

function iniciarRegistro() {
  document.getElementById("tab-estudiante").addEventListener("click", () => elegirRol("estudiante"));
  document.getElementById("tab-docente").addEventListener("click", () => elegirRol("docente"));
  document.getElementById("input-contrasena").addEventListener("input", e => revisarReglasContrasena(e.target.value));
  document.getElementById("form-registro").addEventListener("submit", enviarRegistro);
  document.querySelectorAll("[data-cerrar-modal]").forEach(boton =>
    boton.addEventListener("click", () => document.getElementById(boton.dataset.cerrarModal).classList.add("hidden")));

  elegirRol("estudiante");
  revisarReglasContrasena("");
  cargarCatalogos();
}

// Llena la lista de carreras y el ciclo con lo que tiene el backend.
async function cargarCatalogos() {
  const lista = document.getElementById("select-carrera");
  try {
    const carreras = await pedir("/catalogos/carreras");
    lista.innerHTML = '<option value="">Selecciona tu programa académico...</option>';
    for (const c of carreras) {
      const opcion = document.createElement("option");
      opcion.value = c.clave;
      opcion.textContent = `${c.nombre} (${c.clave})`;
      lista.appendChild(opcion);
    }
  } catch (error) {
    lista.innerHTML = '<option value="">No se pudieron cargar las carreras</option>';
    mostrarErrorApi(error);
  }

  const ciclo = document.getElementById("input-ciclo");
  try {
    const actual = await pedir("/catalogos/ciclo-actual");
    ciclo.value = actual.nombreOficial;
  } catch (error) {
    ciclo.value = "Sin ciclo en curso";
    // 404 = el administrador no ha registrado un ciclo vigente
    if (error.status === 404) {
      mostrarAviso("No hay un ciclo escolar en curso registrado; los estudiantes no podrán registrarse hasta que un administrador lo dé de alta.");
    } else {
      mostrarErrorApi(error);
    }
  }
}

function elegirRol(rol) {
  rolElegido = rol;
  const activa = "w-1/2 flex items-center justify-center gap-space-xs py-2.5 px-4 rounded-lg font-label-lg text-label-lg transition-all bg-surface-container-lowest text-primary shadow-sm font-semibold";
  const inactiva = "w-1/2 flex items-center justify-center gap-space-xs py-2.5 px-4 rounded-lg font-label-lg text-label-lg transition-all text-on-surface-variant hover:text-on-surface";
  const esEstudiante = rol === "estudiante";

  document.getElementById("tab-estudiante").className = esEstudiante ? activa : inactiva;
  document.getElementById("tab-docente").className = esEstudiante ? inactiva : activa;
  document.getElementById("campos-estudiante").classList.toggle("hidden", !esEstudiante);
  document.getElementById("campos-docente").classList.toggle("hidden", esEstudiante);
  document.getElementById("aviso-docente").classList.toggle("hidden", esEstudiante);
  document.getElementById("dominio-correo").textContent = "@" + DOMINIO_POR_ROL[rol];
  document.getElementById("input-correo").placeholder = "nombre.apellido@" + DOMINIO_POR_ROL[rol];
  limpiarErrores();
}

// Reglas de contraseña del backend (RF-03, docs/backend/04-seguridad.md).
const REGLAS_CONTRASENA = {
  largo: v => v.length >= 8,
  mayuscula: v => /[A-Z]/.test(v),
  minuscula: v => /[a-z]/.test(v),
  numero: v => /[0-9]/.test(v)
};

function revisarReglasContrasena(valor) {
  for (const [nombre, cumple] of Object.entries(REGLAS_CONTRASENA)) {
    const fila = document.getElementById("regla-" + nombre);
    const icono = fila.querySelector(".material-symbols-outlined");
    const ok = cumple(valor);
    fila.className = ok
      ? "flex items-center gap-1.5 text-secondary font-helper-sm text-helper-sm font-medium"
      : "flex items-center gap-1.5 text-on-surface-variant font-helper-sm text-helper-sm";
    icono.classList.toggle("icono-relleno", ok);
    icono.classList.toggle("text-secondary", ok);
    icono.classList.toggle("text-outline", !ok);
  }
}

// Revisión rápida en el navegador antes de molestar al backend.
// El backend vuelve a revisar todo; esto solo da avisos más rápidos.
function validarRegistro(datos) {
  const errores = [];
  const obligatorio = "Este campo es obligatorio";

  if (!datos.nombre) errores.push({ campo: "nombre", mensaje: obligatorio });
  if (!datos.apellidos) errores.push({ campo: "apellidos", mensaje: obligatorio });

  const dominio = DOMINIO_POR_ROL[rolElegido];
  if (!datos.correoInstitucional) {
    errores.push({ campo: "correoInstitucional", mensaje: obligatorio });
  } else if (!datos.correoInstitucional.endsWith("@" + dominio)) {
    errores.push({ campo: "correoInstitucional", mensaje: `Como ${rolElegido} debes usar un correo @${dominio}` });
  }

  const c = datos.contrasena;
  if (!Object.values(REGLAS_CONTRASENA).every(regla => regla(c))) {
    errores.push({ campo: "contrasena", mensaje: "La contraseña no cumple los requisitos de seguridad" });
  } else if (c.length > 72) {
    errores.push({ campo: "contrasena", mensaje: "La contraseña no puede tener más de 72 caracteres" });
  }
  if (c !== datos.confirmarContrasena) {
    errores.push({ campo: "confirmarContrasena", mensaje: "La contraseña y su confirmación no coinciden" });
  }

  if (rolElegido === "estudiante") {
    if (!/^\d{9}$/.test(datos.codigo)) errores.push({ campo: "codigo", mensaje: "El código debe tener exactamente 9 dígitos" });
    if (!datos.carrera) errores.push({ campo: "carrera", mensaje: "Selecciona un programa académico" });
  } else if (!/^[A-Za-z0-9-]{3,20}$/.test(datos.noEmpleado)) {
    errores.push({ campo: "noEmpleado", mensaje: "De 3 a 20 caracteres: letras, números o guiones" });
  }

  if (!document.getElementById("check-terminos").checked) {
    errores.push({ campo: "terminos", mensaje: "Debes aceptar el tratamiento de tus datos personales" });
  }
  return errores;
}

// Junta los datos del formulario con los nombres de campo que espera el backend (UsuarioCrear).
function leerFormularioRegistro() {
  const valor = id => document.getElementById(id).value.trim();
  const datos = {
    nombre: valor("input-nombre"),
    apellidos: valor("input-apellidos"),
    correoInstitucional: valor("input-correo").toLowerCase(),
    contrasena: document.getElementById("input-contrasena").value,
    confirmarContrasena: document.getElementById("input-confirmar").value
  };
  if (rolElegido === "estudiante") {
    datos.codigo = valor("input-codigo");
    datos.carrera = valor("select-carrera");
    datos.ciclo = valor("input-ciclo");
  } else {
    datos.noEmpleado = valor("input-no-empleado");
    const departamento = valor("select-departamento");
    if (departamento) datos.departamento = departamento; // opcional en el backend
  }
  return datos;
}

async function enviarRegistro(evento) {
  evento.preventDefault();
  limpiarErrores();

  const datos = leerFormularioRegistro();
  const errores = validarRegistro(datos);
  if (errores.length) {
    errores.forEach(e => marcarCampo(e.campo, e.mensaje));
    mostrarAviso("Revisa los campos marcados en rojo.");
    return;
  }

  const boton = document.getElementById("btn-registro");
  botonCargando(boton, true);
  try {
    const cuenta = await pedir("/usuarios/registro", { metodo: "POST", datos });
    mostrarRegistroExitoso(cuenta, datos);
  } catch (error) {
    mostrarErrorApi(error);
    window.scrollTo({ top: 0, behavior: "smooth" });
  } finally {
    botonCargando(boton, false);
  }
}

// Llena y abre la ventana de éxito con lo que respondió el backend (201).
function mostrarRegistroExitoso(cuenta, datos) {
  const texto = (id, valor) => { document.getElementById(id).textContent = valor; };
  if (cuenta.rol === "estudiante") {
    const carrera = document.getElementById("select-carrera");
    texto("exito-est-nombre", `${cuenta.nombre} ${cuenta.apellidos}`);
    texto("exito-est-codigo", datos.codigo);
    texto("exito-est-carrera", carrera.options[carrera.selectedIndex].textContent);
    texto("exito-est-mensaje", cuenta.mensaje);
    document.getElementById("modal-exito-estudiante").classList.remove("hidden");
  } else {
    const pendiente = cuenta.estado === "pendiente";
    texto("exito-doc-titulo", pendiente ? "Registro docente enviado" : "Cuenta docente creada");
    texto("exito-doc-etiqueta", pendiente ? "Solicitud en proceso" : "Registro concluido");
    texto("exito-doc-mensaje", cuenta.mensaje);
    texto("exito-doc-departamento", datos.departamento || "Sin especificar");
    texto("exito-doc-estado", pendiente ? "Pendiente de aprobación" : "Activa");
    document.getElementById("modal-exito-docente").classList.remove("hidden");
  }
  document.getElementById("form-registro").reset();
  revisarReglasContrasena("");
  cargarCatalogos();
}

// ==================== LOGIN ====================

function iniciarLogin() {
  // Si ya hay sesión en esta pestaña, ir directo al panel.
  const sesion = leerSesion();
  if (sesion) {
    window.location.href = PAGINA_POR_PANEL[sesion.panel] || "dashboard.html";
    return;
  }

  // Mensaje que dejó otra página (sesión expirada, logout...).
  const aviso = sessionStorage.getItem("sepa_aviso");
  if (aviso) {
    mostrarAviso(aviso, "info");
    sessionStorage.removeItem("sepa_aviso");
  }

  document.getElementById("form-login").addEventListener("submit", enviarLogin);
  document.getElementById("link-recuperar").addEventListener("click", mostrarRecuperacion);
}

async function enviarLogin(evento) {
  evento.preventDefault();
  limpiarErrores();

  const datos = {
    codigo: document.getElementById("input-codigo").value.trim(),
    contrasena: document.getElementById("input-contrasena").value
  };
  if (!datos.codigo) marcarCampo("codigo", "Este campo es obligatorio");
  if (!datos.contrasena) marcarCampo("contrasena", "Este campo es obligatorio");
  if (!datos.codigo || !datos.contrasena) return;

  const boton = document.getElementById("btn-login");
  botonCargando(boton, true);
  try {
    const respuesta = await pedir("/usuarios/login", { metodo: "POST", datos });
    guardarSesion(respuesta);
    window.location.href = PAGINA_POR_PANEL[respuesta.panel] || "dashboard.html";
  } catch (error) {
    // 401: código o contraseña incorrectos · 403: cuenta pendiente o desactivada
    mostrarErrorApi(error);
    botonCargando(boton, false);
  }
}

// RF-07: no hay recuperación automática; el backend solo devuelve instrucciones.
async function mostrarRecuperacion(evento) {
  evento.preventDefault();
  try {
    const respuesta = await pedir("/usuarios/recuperar-contrasena");
    mostrarAviso(respuesta.mensaje, "info");
  } catch (error) {
    mostrarErrorApi(error);
  }
}

// ==================== PANEL ====================

const NOMBRE_PANEL = {
  estudiante: "Panel del estudiante",
  docente: "Panel del docente",
  administrador: "Panel de administración"
};

async function iniciarPanel() {
  if (!leerSesion()) {
    irALogin("Inicia sesión para continuar.");
    return;
  }
  document.getElementById("btn-logout").addEventListener("click", cerrarSesion);

  try {
    // Si el token ya no sirve, pedir() responde 401 y manda al login.
    const perfil = await pedir("/usuarios/yo", { conToken: true });
    mostrarPerfil(perfil);
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  }
}

function mostrarPerfil(perfil) {
  const texto = (id, valor) => { document.getElementById(id).textContent = valor; };
  const nombreCompleto = `${perfil.nombre} ${perfil.apellidos}`;

  texto("panel-titulo", NOMBRE_PANEL[perfil.panel] || "Panel");
  texto("panel-saludo", `Hola, ${perfil.nombre}`);
  texto("header-nombre", nombreCompleto);
  texto("perfil-nombre", nombreCompleto);
  texto("perfil-correo", perfil.correoInstitucional);
  texto("perfil-codigo-etiqueta", perfil.panel === "estudiante" ? "Código de estudiante" : "Número de empleado");
  texto("perfil-codigo", perfil.codigo ?? "—");

  const roles = document.getElementById("perfil-roles");
  roles.innerHTML = "";
  for (const rol of perfil.roles) {
    const etiqueta = document.createElement("span");
    etiqueta.className = "font-label-md text-label-md px-2.5 py-0.5 rounded-full bg-surface-container text-on-secondary-container capitalize";
    etiqueta.textContent = rol;
    roles.appendChild(etiqueta);
  }

  document.getElementById("panel-cargando").classList.add("hidden");
  document.getElementById("panel-contenido").classList.remove("hidden");
}

async function cerrarSesion() {
  const boton = document.getElementById("btn-logout");
  boton.disabled = true;
  try {
    await pedir("/usuarios/logout", { metodo: "POST", conToken: true });
    irALogin("Sesión cerrada correctamente.");
  } catch (error) {
    // 401 = el token ya no era válido; pedir() ya mandó al login.
    if (error.status !== 401) {
      mostrarErrorApi(error);
      boton.disabled = false;
    }
  }
}
