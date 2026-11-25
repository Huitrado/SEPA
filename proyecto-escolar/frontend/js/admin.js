// ============================================================
// admin.js: panel del administrador (admin.html). Secciones por pestaña:
//   Inicio     resumen y docentes pendientes de aprobar      -> GET /admin/usuarios, PATCH .../estado
//   Usuarios   RF-93 registrar, modificar y desactivar       -> POST /admin/docentes, /admin/administradores
//                                                              PATCH /admin/usuarios/{id}, .../estado
//              RF-73 asignar el rol de asesor a estudiantes  -> PATCH /admin/usuarios/{id}/asesor
//              RF-07 restablecer la contraseña               -> PATCH /admin/usuarios/{id}/contrasena
//   Ciclos y Catálogos viven en admin-catalogos.js.
// ============================================================

document.addEventListener("DOMContentLoaded", iniciarAdmin);

const SECCIONES = [
  ["inicio", "Inicio", "dashboard"],
  ["usuarios", "Usuarios y roles", "manage_accounts"],
  ["ciclos", "Ciclos escolares", "event"],
  ["catalogos", "Carreras y materias", "menu_book"],
  ["planes", "Planes de estudio", "account_tree"]
];

const ETIQUETA_ROL = {
  estudiante: ["Estudiante", "bg-surface-container text-on-surface-variant"],
  asesor: ["Asesor", "bg-tertiary-fixed text-on-tertiary-fixed-variant"],
  docente: ["Docente", "bg-surface-container-high text-on-secondary-container"],
  administrador: ["Administrador", "bg-primary-container text-on-primary"]
};

const ETIQUETA_ESTADO = {
  activo: ["Activa", "bg-semaforo-verde-fondo text-semaforo-verde"],
  pendiente: ["Pendiente de aprobación", "bg-semaforo-amarillo-fondo text-semaforo-amarillo"],
  inactivo: ["Desactivada", "bg-surface-container text-on-surface-variant"]
};

let miId = null;
let usuarios = [];
let carreras = [];
let editado = null;

async function iniciarAdmin() {
  const perfil = await protegerPagina(["administrador"]);
  if (!perfil) return;
  miId = perfil.id;
  activarModales();
  pintarSecciones();
  window.addEventListener("hashchange", () => mostrarSeccion(location.hash.slice(1), false));
  ["buscar-usuario", "filtro-rol", "filtro-estado"].forEach(id =>
    document.getElementById(id).addEventListener("input", pintarUsuarios));
  document.getElementById("btn-nuevo-usuario").addEventListener("click", abrirNuevo);
  document.getElementById("form-nuevo").addEventListener("submit", registrarUsuario);
  document.querySelectorAll('input[name="tipoCuenta"]').forEach(r => r.addEventListener("change", ajustarTipoCuenta));
  document.getElementById("form-editar").addEventListener("submit", guardarUsuario);
  document.getElementById("form-contrasena").addEventListener("submit", restablecerContrasena);
  document.getElementById("form-rechazo").addEventListener("submit", rechazarSolicitud);
  iniciarCatalogos();
  mostrarSeccion(location.hash.slice(1) || "inicio", false);
  await Promise.all([cargarUsuarios(), cargarCatalogos(), cargarSolicitudes()]);
}

// ==================== SOLICITUDES PARA SER ASESOR ====================
// GET /admin/solicitudes-asesor?estado=pendiente · PATCH /admin/solicitudes-asesor/{id}
// Aceptar le da el rol de asesor (igual que en "Editar usuario"); rechazar admite un comentario.
let solicitudes = [];
let solicitudEnRechazo = null;

async function cargarSolicitudes() {
  try {
    solicitudes = await pedir("/admin/solicitudes-asesor?estado=pendiente", { conToken: true });
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
    return;
  }
  pintarSolicitudes();
}

function pintarSolicitudes() {
  const contenedor = document.getElementById("inicio-solicitudes");
  contenedor.innerHTML = "";
  if (!solicitudes.length) {
    contenedor.appendChild(el("p", "px-space-lg pb-space-lg text-on-surface-variant", "No hay solicitudes por revisar."));
    return;
  }
  for (const s of solicitudes) {
    const fila = el("div", "px-space-lg py-space-md border-t border-surface-container flex flex-col md:flex-row md:items-start justify-between gap-space-sm");
    const datos = el("div", "min-w-0 space-y-1");
    datos.append(el("p", "font-label-lg text-label-lg text-primary", s.nombre),
      el("p", "font-helper-sm text-helper-sm text-on-surface-variant",
        `${s.codigo} · ${s.carrera ? nombreCarrera(s.carrera) : "Sin carrera"} · enviada ${fechaHora(s.fechaSolicitud)}`),
      el("p", "font-body-md text-body-md text-on-surface", `Imparte asesorías de: ${s.materias || "sin indicar"}`));
    if (s.motivo) datos.appendChild(el("p", "font-helper-sm text-helper-sm text-on-surface-variant whitespace-pre-line", s.motivo));
    const acciones = el("div", "flex gap-1 shrink-0");
    const aceptar = boton("Aceptar", "verified", "primario");
    aceptar.addEventListener("click", () => aceptarSolicitud(s, aceptar));
    const rechazar = boton("Rechazar", "block", "peligro");
    rechazar.addEventListener("click", () => abrirRechazo(s));
    acciones.append(aceptar, rechazar);
    fila.append(datos, acciones);
    contenedor.appendChild(fila);
  }
}

async function aceptarSolicitud(s, b) {
  if (!await confirmar(`¿Hacer asesor a ${s.nombre}?`, "Podrá publicar asesorías en el tablero. Puedes quitarle el rol después desde Usuarios y roles.", "Aceptar")) return;
  b.disabled = true;
  try {
    await pedir(`/admin/solicitudes-asesor/${s.id}`, { metodo: "PATCH", datos: { decision: "aceptada" }, conToken: true });
    mostrarToast(`${s.nombre} ahora es asesor.`);
    await Promise.all([cargarSolicitudes(), cargarUsuarios()]);
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
    b.disabled = false;
  }
}

function abrirRechazo(s) {
  solicitudEnRechazo = s;
  document.getElementById("form-rechazo").reset();
  limpiarErrores("aviso-rechazo");
  document.getElementById("rechazo-para").textContent = s.nombre;
  abrirModal("modal-rechazo");
}

async function rechazarSolicitud(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-rechazo");
  const comentario = document.getElementById("input-comentario").value.trim() || null;
  const b = document.getElementById("btn-confirmar-rechazo");
  botonCargando(b, true);
  try {
    await pedir(`/admin/solicitudes-asesor/${solicitudEnRechazo.id}`,
      { metodo: "PATCH", datos: { decision: "rechazada", comentario }, conToken: true });
    cerrarModal("modal-rechazo");
    mostrarToast("Solicitud rechazada.");
    await cargarSolicitudes();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error, "aviso-rechazo");
  } finally {
    botonCargando(b, false);
  }
}

// ==================== SECCIONES ====================

function pintarSecciones() {
  const barra = document.getElementById("pestanas");
  for (const [clave, texto, nombreIcono] of SECCIONES) {
    const b = el("button");
    b.type = "button";
    b.setAttribute("role", "tab");
    b.dataset.seccion = clave;
    b.append(icono(nombreIcono), el("span", "", texto));
    b.addEventListener("click", () => mostrarSeccion(clave));
    barra.appendChild(b);
  }
}

function mostrarSeccion(clave, cambiarHash = true) {
  const seccion = SECCIONES.find(([k]) => k === clave) || SECCIONES[0];
  const base = "flex items-center gap-space-xs py-2 px-space-md rounded-lg font-label-lg text-label-lg whitespace-nowrap transition-all";
  document.querySelectorAll("[data-seccion]").forEach(b => {
    const activa = b.dataset.seccion === seccion[0];
    b.className = activa ? `${base} bg-surface-container-lowest text-primary shadow-sm` : `${base} text-on-surface-variant hover:text-on-surface`;
    b.setAttribute("aria-selected", String(activa));
  });
  document.querySelectorAll("[data-panel]").forEach(p => p.classList.toggle("hidden", p.id !== `panel-${seccion[0]}`));
  document.getElementById("titulo-seccion").textContent = seccion[1];
  if (cambiarHash && location.hash !== `#${seccion[0]}`) history.replaceState(null, "", `#${seccion[0]}`);
}

function chip(texto, clases) {
  return el("span", `inline-flex items-center px-2.5 py-0.5 rounded-full font-label-md text-label-md whitespace-nowrap ${clases}`, texto);
}

// ==================== USUARIOS ====================

async function cargarUsuarios() {
  try {
    usuarios = await pedir("/admin/usuarios", { conToken: true });
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  }
  pintarInicio();
  pintarUsuarios();
}

function nombreCarrera(clave) {
  return carreras.find(c => c.clave === clave)?.nombre || clave;
}

function pintarUsuarios() {
  const cuerpo = document.getElementById("tabla-usuarios");
  cuerpo.innerHTML = "";
  const texto = document.getElementById("buscar-usuario").value.trim().toLowerCase();
  const rol = document.getElementById("filtro-rol").value;
  const estado = document.getElementById("filtro-estado").value;
  const visibles = usuarios.filter(u =>
    (!rol || u.roles.includes(rol)) && (!estado || u.estado === estado) &&
    (!texto || `${u.nombre} ${u.apellidos} ${u.codigo || ""} ${u.correoInstitucional}`.toLowerCase().includes(texto)));
  document.getElementById("usuarios-total").textContent = `${visibles.length} de ${usuarios.length}`;
  document.getElementById("usuarios-vacio").classList.toggle("hidden", visibles.length > 0);
  visibles.forEach(u => cuerpo.appendChild(filaUsuario(u)));
}

function filaUsuario(u) {
  const fila = el("tr", `border-t border-surface-container hover:bg-surface-container-low transition-colors ${u.estado === "inactivo" ? "opacity-70" : ""}`);
  const persona = el("td", "py-space-md px-space-lg");
  persona.append(el("p", "font-label-lg text-label-lg text-primary", `${u.nombre} ${u.apellidos}`),
    el("p", "font-helper-sm text-helper-sm text-on-surface-variant font-mono", u.codigo || "—"),
    el("p", "font-helper-sm text-helper-sm text-on-surface-variant", u.correoInstitucional));

  const area = el("td", "py-space-md px-space-md");
  if (u.carrera) area.append(el("p", "font-label-lg text-label-lg text-primary", u.carrera),
    el("p", "font-caption text-caption text-on-surface-variant", `${nombreCarrera(u.carrera)}${u.ciclo ? ` · ingreso ${u.ciclo}` : ""}`));
  else area.appendChild(el("p", "text-on-surface-variant", u.departamento || "—"));

  const roles = el("td", "py-space-md px-space-md");
  const lista = el("div", "flex flex-wrap gap-1");
  u.roles.forEach(r => lista.appendChild(chip(...(ETIQUETA_ROL[r] || [r, "bg-surface-container"]))));
  roles.appendChild(lista);

  const estado = el("td", "py-space-md px-space-md");
  estado.appendChild(chip(...ETIQUETA_ESTADO[u.estado]));

  const acciones = el("td", "py-space-md px-space-lg");
  const grupo = el("div", "flex justify-end flex-wrap gap-1");
  const accion = (titulo, nombreIcono, variante, alHacerClic) => {
    const b = boton("", nombreIcono, variante);
    b.title = titulo;
    b.setAttribute("aria-label", titulo);
    b.addEventListener("click", alHacerClic);
    grupo.appendChild(b);
  };
  if (u.estado === "pendiente") accion("Aprobar cuenta", "verified", "primario", () => cambiarEstado(u, "activo"));
  accion("Editar datos y roles", "edit", "suave", () => abrirEditar(u));
  accion("Restablecer contraseña", "lock_reset", "suave", () => abrirContrasena(u));
  if (u.id !== miId) {
    if (u.estado === "inactivo") accion("Reactivar cuenta", "check_circle", "secundario", () => cambiarEstado(u, "activo"));
    // Un administrador no puede desactivar a otro administrador (lo rechaza también el backend)
    else if (!u.roles.includes("administrador"))
      accion(u.estado === "pendiente" ? "Rechazar registro" : "Desactivar cuenta", "block", "peligro", () => cambiarEstado(u, "inactivo"));
  }
  acciones.appendChild(grupo);
  fila.append(persona, area, roles, estado, acciones);
  return fila;
}

async function cambiarEstado(u, estado) {
  const nombre = `${u.nombre} ${u.apellidos}`;
  const textos = {
    activo: u.estado === "pendiente"
      ? [`¿Aprobar a ${nombre}?`, "Podrá iniciar sesión como docente.", "Aprobar"]
      : [`¿Reactivar la cuenta de ${nombre}?`, "Podrá volver a iniciar sesión.", "Reactivar"],
    inactivo: u.estado === "pendiente"
      ? [`¿Rechazar el registro de ${nombre}?`, "La cuenta quedará desactivada y no podrá iniciar sesión.", "Rechazar"]
      : [`¿Desactivar la cuenta de ${nombre}?`, "No podrá iniciar sesión hasta que la reactives. Sus datos se conservan.", "Desactivar"]
  };
  if (!await confirmar(...textos[estado])) return;
  try {
    await pedir(`/admin/usuarios/${u.id}/estado`, { metodo: "PATCH", datos: { estado }, conToken: true });
    await cargarUsuarios();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  }
}

// ---------- Registrar docente o administrador (RF-93) ----------

function abrirNuevo() {
  document.getElementById("form-nuevo").reset();
  limpiarErrores("aviso-nuevo");
  ajustarTipoCuenta();
  abrirModal("modal-nuevo");
  document.getElementById("nuevo-nombre").focus();
}

function ajustarTipoCuenta() {
  const docente = document.querySelector('input[name="tipoCuenta"]:checked').value === "docente";
  document.getElementById("campo-departamento").classList.toggle("hidden", !docente);
  document.getElementById("nuevo-correo").placeholder = docente ? "usuario@academicos.udg.mx" : "usuario@udg.mx";
}

async function registrarUsuario(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-nuevo");
  const tipo = document.querySelector('input[name="tipoCuenta"]:checked').value;
  const valor = id => document.getElementById(id).value.trim();
  const datos = {
    nombre: valor("nuevo-nombre"), apellidos: valor("nuevo-apellidos"),
    correoInstitucional: valor("nuevo-correo"), noEmpleado: valor("nuevo-empleado").toUpperCase(),
    contrasena: document.getElementById("nuevo-contrasena").value
  };
  if (tipo === "docente" && valor("nuevo-departamento")) datos.departamento = valor("nuevo-departamento");
  const faltan = ["nombre", "apellidos", "correoInstitucional", "noEmpleado", "contrasena"].filter(c => !datos[c]);
  if (faltan.length) {
    faltan.forEach(c => marcarCampo(c, "Este campo es obligatorio"));
    mostrarAviso("Revisa los campos marcados en rojo.", "error", "aviso-nuevo");
    return;
  }
  const b = document.getElementById("btn-guardar-nuevo");
  botonCargando(b, true);
  try {
    await pedir(tipo === "docente" ? "/admin/docentes" : "/admin/administradores", { metodo: "POST", datos, conToken: true });
    cerrarModal("modal-nuevo");
    mostrarAviso(`Cuenta creada. ${datos.nombre} inicia sesión con el código ${datos.noEmpleado}.`, "info");
    await cargarUsuarios();
  } catch (error) {
    // 409 correo o número de empleado repetido · 422 datos inválidos (dominio, contraseña...)
    if (error.status !== 401) mostrarErrorApi(error, "aviso-nuevo");
  } finally {
    botonCargando(b, false);
  }
}

// ---------- Editar datos y rol de asesor (RF-73, RF-93) ----------

function abrirEditar(u) {
  editado = u;
  limpiarErrores("aviso-editar");
  document.getElementById("editar-codigo").textContent = `Código ${u.codigo || "—"}`;
  document.getElementById("editar-nombre").value = u.nombre;
  document.getElementById("editar-apellidos").value = u.apellidos;
  document.getElementById("editar-correo").value = u.correoInstitucional;
  const esEstudiante = u.roles.includes("estudiante");
  const esDocente = u.roles.includes("docente");
  document.getElementById("campo-editar-carrera").classList.toggle("hidden", !esEstudiante);
  document.getElementById("campo-editar-departamento").classList.toggle("hidden", !esDocente);
  document.getElementById("campo-asesor").classList.toggle("hidden", !esEstudiante);
  const select = document.getElementById("editar-carrera");
  select.innerHTML = "";
  carreras.forEach(c => select.appendChild(new Option(`${c.nombre} (${c.clave})`, c.clave)));
  select.value = u.carrera || "";
  document.getElementById("editar-departamento").value = u.departamento || "";
  document.getElementById("editar-asesor").checked = u.roles.includes("asesor");
  abrirModal("modal-editar");
}

async function guardarUsuario(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-editar");
  const u = editado;
  const valor = id => document.getElementById(id).value.trim();
  const datos = {};
  if (valor("editar-nombre") !== u.nombre) datos.nombre = valor("editar-nombre");
  if (valor("editar-apellidos") !== u.apellidos) datos.apellidos = valor("editar-apellidos");
  if (valor("editar-correo").toLowerCase() !== u.correoInstitucional) datos.correoInstitucional = valor("editar-correo");
  if (u.roles.includes("estudiante") && valor("editar-carrera") !== u.carrera) datos.carrera = valor("editar-carrera");
  if (u.roles.includes("docente") && valor("editar-departamento") !== (u.departamento || "")) datos.departamento = valor("editar-departamento");
  const asesor = document.getElementById("editar-asesor").checked;
  const cambiaAsesor = u.roles.includes("estudiante") && asesor !== u.roles.includes("asesor");

  const b = document.getElementById("btn-guardar-editar");
  botonCargando(b, true);
  try {
    if (Object.keys(datos).length) await pedir(`/admin/usuarios/${u.id}`, { metodo: "PATCH", datos, conToken: true });
    if (cambiaAsesor) await pedir(`/admin/usuarios/${u.id}/asesor`, { metodo: "PATCH", datos: { asesor }, conToken: true });
    cerrarModal("modal-editar");
    await cargarUsuarios();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error, "aviso-editar");
  } finally {
    botonCargando(b, false);
  }
}

// ---------- Restablecer contraseña (RF-07) ----------

function abrirContrasena(u) {
  editado = u;
  document.getElementById("form-contrasena").reset();
  limpiarErrores("aviso-contrasena");
  document.getElementById("contrasena-para").textContent = `${u.nombre} ${u.apellidos} · ${u.codigo || ""}`;
  abrirModal("modal-contrasena");
  document.getElementById("input-nueva-contrasena").focus();
}

async function restablecerContrasena(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-contrasena");
  const nueva = document.getElementById("input-nueva-contrasena").value;
  if (!nueva) return marcarCampo("nueva_contrasena", "Escribe la nueva contraseña");
  const b = document.getElementById("btn-guardar-contrasena");
  botonCargando(b, true);
  try {
    const r = await pedir(`/admin/usuarios/${editado.id}/contrasena`, { metodo: "PATCH", datos: { nueva_contrasena: nueva }, conToken: true });
    cerrarModal("modal-contrasena");
    mostrarAviso(`${r.mensaje}. Compártela con ${editado.nombre} por un medio seguro.`, "info");
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error, "aviso-contrasena");
  } finally {
    botonCargando(b, false);
  }
}

// ==================== INICIO ====================

function pintarInicio() {
  const metricas = document.getElementById("inicio-metricas");
  metricas.innerHTML = "";
  const cuenta = f => usuarios.filter(f).length;
  const pendientes = usuarios.filter(u => u.estado === "pendiente");
  const tarjeta = (nombreIcono, valor, texto, destino, clasesValor = "text-primary") => {
    const t = el("button", "text-left p-space-md rounded-xl bg-surface-container-lowest shadow-sm flex items-center justify-between gap-space-md hover:shadow-md transition-shadow");
    t.type = "button";
    t.addEventListener("click", destino);
    const textos = el("div");
    textos.append(el("p", "font-headline-md text-headline-md " + clasesValor, String(valor)), el("p", "font-helper-sm text-helper-sm text-on-surface-variant", texto));
    const caja = el("span", "w-12 h-12 rounded-lg bg-surface-container flex items-center justify-center text-primary");
    caja.appendChild(icono(nombreIcono, "text-[24px]"));
    t.append(textos, caja);
    return t;
  };
  const verUsuarios = (rol, estado) => () => {
    document.getElementById("filtro-rol").value = rol;
    document.getElementById("filtro-estado").value = estado;
    pintarUsuarios();
    mostrarSeccion("usuarios");
  };
  metricas.append(
    tarjeta("group", cuenta(u => u.roles.includes("estudiante")), "estudiantes", verUsuarios("estudiante", "")),
    tarjeta("co_present", cuenta(u => u.roles.includes("docente")), "docentes", verUsuarios("docente", "")),
    tarjeta("school", cuenta(u => u.roles.includes("asesor")), "asesores", verUsuarios("asesor", "")),
    tarjeta("pending_actions", pendientes.length, "pendientes de aprobación", verUsuarios("", "pendiente"),
      pendientes.length ? "text-on-tertiary-container" : "text-primary")
  );

  const contenedor = document.getElementById("inicio-pendientes");
  contenedor.innerHTML = "";
  if (!pendientes.length) {
    contenedor.appendChild(el("p", "px-space-lg pb-space-lg text-on-surface-variant", "No hay docentes esperando aprobación."));
    return;
  }
  for (const u of pendientes) {
    const fila = el("div", "px-space-lg py-space-md border-t border-surface-container flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm");
    const datos = el("div");
    datos.append(el("p", "font-label-lg text-label-lg text-primary", `${u.nombre} ${u.apellidos}`),
      el("p", "font-helper-sm text-helper-sm text-on-surface-variant", `${u.correoInstitucional} · ${u.codigo || ""}${u.departamento ? ` · ${u.departamento}` : ""}`));
    const acciones = el("div", "flex gap-1");
    const aprobar = boton("Aprobar", "verified", "primario");
    aprobar.addEventListener("click", () => cambiarEstado(u, "activo"));
    const rechazar = boton("Rechazar", "block", "peligro");
    rechazar.addEventListener("click", () => cambiarEstado(u, "inactivo"));
    acciones.append(aprobar, rechazar);
    fila.append(datos, acciones);
    contenedor.appendChild(fila);
  }
}
