// ============================================================
// curso.js: detalle de un curso del docente (curso.html?id=N).
//   Ficha del curso y pestañas. Cada pestaña vive en su archivo:
//     Matrícula y seguimiento (aquí)        -> GET .../alumnos, GET .../seguimiento
//                                              PATCH .../alumnos/{matricula}/estado (RF-16)
//     Asistencia (curso-asistencia.js)      -> RF-19 a RF-28
//     Actividades, encuadre y calificaciones (curso-evaluacion.js) -> RF-29 a RF-47
//   Configurar curso (aquí)                 -> PATCH /docente/cursos/{id} y .../estado
// RF-95: el backend responde 403 si el curso no es del docente.
// ============================================================

document.addEventListener("DOMContentLoaded", iniciarCurso);

const CURSO_ID = Number(new URLSearchParams(location.search).get("id"));

// Datos del curso que comparten las pestañas
const C = {
  curso: null,
  ciclo: null,
  materias: [],
  alumnos: [],        // GET .../alumnos (todos, incluidos los de baja)
  seguimiento: null,  // GET .../seguimiento (solo activos)
  asistencia: null,   // GET .../asistencia
  categorias: null,   // GET .../categorias
  actividades: [],    // GET .../actividades
  calificaciones: null
};

const PESTANAS = [
  ["matricula", "Matrícula", "groups"],
  ["asistencia", "Asistencia", "event_available"],
  ["actividades", "Actividades", "assignment"],
  ["encuadre", "Encuadre", "balance"],
  ["calificaciones", "Calificaciones", "grading"]
];

let filtroSemaforo = "todos";

function rutaCurso(resto = "") {
  return `/docente/cursos/${CURSO_ID}${resto}`;
}

async function iniciarCurso() {
  const perfil = await protegerPagina(["docente"]);
  if (!perfil) return;
  if (!CURSO_ID) {
    window.location.replace("docente.html");
    return;
  }
  activarModales();
  pintarPestanas();
  document.getElementById("btn-copiar-codigo").addEventListener("click", e => copiarCodigo(e.currentTarget));
  document.getElementById("btn-configurar").addEventListener("click", abrirConfigurar);
  document.getElementById("form-configurar").addEventListener("submit", guardarConfiguracion);
  document.getElementById("btn-cambiar-estado").addEventListener("click", cambiarEstadoCurso);
  document.getElementById("btn-pasar-lista").addEventListener("click", pasarListaHoy);
  document.getElementById("buscar-alumno").addEventListener("input", pintarMatricula);
  window.addEventListener("hashchange", () => mostrarPestana(location.hash.slice(1), false));
  iniciarAsistencia();
  iniciarEvaluacion();

  try {
    const [curso, ciclos] = await Promise.all([pedir(rutaCurso(), { conToken: true }), pedir("/catalogos/ciclos")]);
    C.curso = curso;
    C.ciclo = ciclos.find(c => c.id === curso.cicloEscolar_id) || null;
  } catch (error) {
    document.getElementById("curso-cargando").classList.add("hidden");
    if (error.status !== 401) mostrarErrorApi(error);
    return;
  }
  pintarFicha();
  document.getElementById("curso-cargando").classList.add("hidden");
  document.getElementById("curso-contenido").classList.remove("hidden");
  mostrarPestana(location.hash.slice(1) || "matricula", false);

  await Promise.all([cargarMatricula(), cargarAsistencia(), cargarEvaluacion()]);
  pintarMetricas();
  pedir("/catalogos/materias").then(m => { C.materias = m; }).catch(() => {});
}

// Muestra el error de una carga sin romper la página
function avisarError(error) {
  if (error.status !== 401) mostrarErrorApi(error);
}

// ==================== FICHA Y RESUMEN ====================

function pintarFicha() {
  const c = C.curso;
  document.title = `${c.nombreMateria} · SEPA CUCEI`;
  document.getElementById("miga-curso").textContent = `${c.nombreMateria} · ${c.seccion}`;
  document.getElementById("curso-titulo").textContent = `${c.nombreMateria} — Sección ${c.seccion}`;
  document.getElementById("curso-descripcion").textContent = c.descripcion || "";

  const etiquetas = document.getElementById("curso-etiquetas");
  etiquetas.innerHTML = "";
  const chip = (texto, clases) => el("span", `font-label-md text-label-md px-2.5 py-0.5 rounded-full ${clases}`, texto);
  if (C.ciclo) etiquetas.appendChild(chip(`Ciclo ${C.ciclo.nombreOficial}`, "bg-surface-container-high text-primary"));
  etiquetas.appendChild(chip(ETIQUETA_EVALUACION[c.tipoEvaluacion] || c.tipoEvaluacion, "bg-surface-container text-on-secondary-container"));
  if (c.tipoEvaluacion === "numerica") {
    etiquetas.appendChild(chip(`Mínimo aprobatorio: ${Math.round(c.umbralNumerico)}/100`, "bg-tertiary-fixed text-on-tertiary-fixed-variant"));
  }
  if (c.estado === "archivado") etiquetas.appendChild(chip("Archivado", "bg-surface-container text-on-surface-variant"));

  const horario = document.getElementById("curso-horario");
  horario.innerHTML = "";
  const dato = (nombreIcono, texto) => {
    const span = el("span", "inline-flex items-center gap-space-xs");
    span.append(icono(nombreIcono, "text-[18px] text-on-surface-variant"), el("span", "", texto));
    return span;
  };
  horario.append(dato("calendar_month", diasCortos(c.diasSemana)), dato("schedule", `${c.horaInicio} – ${c.horaFin}`));

  document.getElementById("curso-codigo").textContent = c.codigoCurso;
  document.getElementById("btn-copiar-codigo").dataset.copiar = c.codigoCurso;
  // En un curso archivado no se generan sesiones ni se crean actividades
  const archivado = c.estado === "archivado";
  document.getElementById("btn-crear-actividad").classList.toggle("hidden", archivado);
  document.getElementById("btn-pasar-lista").classList.toggle("hidden", archivado);
  document.getElementById("btn-lista-hoy").classList.toggle("hidden", archivado);
}

// Lo que antes era el resumen de la ficha ya vive en su pestaña: los conteos por color y las bajas
// en los filtros de Matrícula, la suma del encuadre en Encuadre. Aquí solo queda el promedio de
// asistencia del grupo, que se muestra en la pestaña Asistencia.
function pintarMetricas() {
  const seg = C.seguimiento?.alumnos || [];
  const promedio = seg.length ? seg.reduce((s, a) => s + a.porcentajeAsistencia, 0) / seg.length : null;
  document.getElementById("asistencia-promedio").textContent =
    promedio === null ? "" : `Promedio del grupo: ${numero(promedio, 1)} %`;
}

// ==================== PESTAÑAS ====================

function pintarPestanas() {
  const barra = document.getElementById("pestanas");
  for (const [clave, texto, nombreIcono] of PESTANAS) {
    const b = el("button", "");
    b.type = "button";
    b.setAttribute("role", "tab");
    b.dataset.pestana = clave;
    b.append(icono(nombreIcono), el("span", "", texto));
    b.addEventListener("click", () => mostrarPestana(clave));
    barra.appendChild(b);
  }
}

function mostrarPestana(clave, cambiarHash = true) {
  if (!PESTANAS.some(([k]) => k === clave)) clave = "matricula";
  const base = "flex items-center gap-space-xs py-2 px-space-md rounded-lg font-label-lg text-label-lg whitespace-nowrap transition-all";
  document.querySelectorAll("[data-pestana]").forEach(b => {
    const activa = b.dataset.pestana === clave;
    b.className = activa ? `${base} bg-surface-container-lowest text-primary shadow-sm` : `${base} text-on-surface-variant hover:text-on-surface`;
    b.setAttribute("aria-selected", String(activa));
  });
  document.querySelectorAll("[data-panel]").forEach(p => p.classList.toggle("hidden", p.id !== `panel-${clave}`));
  if (cambiarHash && location.hash !== `#${clave}`) history.replaceState(null, "", `#${clave}`);
}

// ==================== MATRÍCULA Y SEGUIMIENTO ====================

async function cargarMatricula() {
  try {
    const [alumnos, seguimiento] = await Promise.all([
      pedir(rutaCurso("/alumnos"), { conToken: true }),
      pedir(rutaCurso("/seguimiento"), { conToken: true })
    ]);
    C.alumnos = alumnos;
    C.seguimiento = seguimiento;
  } catch (error) {
    avisarError(error);
  }
  pintarFiltrosSemaforo();
  pintarMatricula();
}

function pintarFiltrosSemaforo() {
  const contenedor = document.getElementById("filtros-semaforo");
  contenedor.innerHTML = "";
  const resumen = C.seguimiento?.resumen || { verde: 0, amarillo: 0, rojo: 0 };
  const bajas = C.alumnos.filter(a => a.estado !== "activo").length;
  const opciones = [
    ["todos", `Todos (${C.alumnos.length})`],
    ["verde", `Verde (${resumen.verde})`],
    ["amarillo", `Amarillo (${resumen.amarillo})`],
    ["rojo", `Rojo (${resumen.rojo})`],
    ["baja", `Bajas (${bajas})`]
  ];
  for (const [clave, texto] of opciones) {
    const b = el("button", `px-space-md py-1.5 rounded-lg font-label-md text-label-md transition-colors ${clave === filtroSemaforo ? "bg-primary-container text-on-primary" : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container"}`, texto);
    b.type = "button";
    b.addEventListener("click", () => {
      filtroSemaforo = clave;
      pintarFiltrosSemaforo();
      pintarMatricula();
    });
    contenedor.appendChild(b);
  }
}

function pintarMatricula() {
  const cuerpo = document.getElementById("tabla-matricula");
  const vacia = document.getElementById("matricula-vacia");
  cuerpo.innerHTML = "";
  const indicadores = new Map((C.seguimiento?.alumnos || []).map(a => [a.matricula_id, a]));
  const busqueda = document.getElementById("buscar-alumno").value.trim().toLowerCase();

  const filas = C.alumnos.filter(a => {
    const seg = indicadores.get(a.matricula_id);
    if (filtroSemaforo === "baja" && a.estado === "activo") return false;
    if (["verde", "amarillo", "rojo"].includes(filtroSemaforo) && seg?.semaforoGeneral !== filtroSemaforo) return false;
    const texto = `${a.nombre} ${a.apellidos} ${a.codigoEstudiante} ${a.correoInstitucional}`.toLowerCase();
    return !busqueda || texto.includes(busqueda);
  });

  vacia.classList.toggle("hidden", filas.length > 0);
  vacia.textContent = C.alumnos.length
    ? "Ningún alumno coincide con el filtro."
    : `Aún no hay alumnos inscritos. Comparte el código ${C.curso.codigoCurso} para que se inscriban.`;

  for (const a of filas) cuerpo.appendChild(filaAlumno(a, indicadores.get(a.matricula_id)));
}

function filaAlumno(a, seg) {
  const activo = a.estado === "activo";
  const fila = el("tr", `border-t border-surface-container hover:bg-surface-container-low transition-colors ${activo ? "" : "opacity-70"}`);

  const celdaAlumno = el("td", "py-space-md px-space-lg");
  celdaAlumno.append(
    el("p", "font-label-lg text-label-lg text-primary", `${a.apellidos} ${a.nombre}`),
    el("p", "font-helper-sm text-helper-sm text-on-surface-variant font-mono", a.codigoEstudiante),
    el("p", "font-helper-sm text-helper-sm text-on-surface-variant", a.correoInstitucional)
  );

  const celdaInscripcion = el("td", "py-space-md px-space-md");
  celdaInscripcion.append(
    el("p", "", fechaCorta(a.fechaInscripcion)),
    el("span", `inline-block mt-1 font-label-md text-label-md px-2 py-0.5 rounded-full ${activo ? "bg-surface-container text-on-secondary-container" : "bg-surface-container-high text-on-surface-variant"}`, activo ? "Activo" : "Baja")
  );

  const celdaAsistencia = el("td", "py-space-md px-space-md");
  const celdaCalificacion = el("td", "py-space-md px-space-md");
  const celdaRiesgo = el("td", "py-space-md px-space-md");
  if (seg) {
    celdaAsistencia.append(
      el("p", "font-label-lg text-label-lg", `${numero(seg.porcentajeAsistencia, 1)} %`),
      el("p", "font-helper-sm text-helper-sm text-on-surface-variant", seg.estatusNormativo)
    );
    celdaCalificacion.append(
      el("p", "font-label-lg text-label-lg", `${numero(seg.calificacionAcumulada)} / 100`),
      el("p", `font-helper-sm text-helper-sm ${seg.alertaCalificacion ? "text-error font-semibold" : "text-on-surface-variant"}`,
        seg.desempenoProporcional === null ? "Sin evaluaciones aún" : `${numero(seg.desempenoProporcional, 1)} % de lo evaluado`)
    );
    celdaRiesgo.appendChild(chipSemaforo(seg.semaforoGeneral));
    // Banderas: asistencia en amarillo o rojo (RF-50, RF-51), RF-48 calificación, RF-84 artículos 33 a 35,
    // RF-58/59 rezago crítico, RF-54 historial. Cada una es una insignia que dice la causa de la alerta.
    const ROJA = "bg-semaforo-rojo-fondo text-semaforo-rojo";
    const asistenciaEnRiesgo = seg.semaforoAsistencia && seg.semaforoAsistencia !== "verde";
    const banderas = [
      [asistenciaEnRiesgo, "event_busy", "Alerta por asistencia",
        `${numero(seg.porcentajeAsistencia, 1)} % de asistencia (${seg.estatusNormativo})`,
        seg.semaforoAsistencia === "rojo" ? ROJA : "bg-semaforo-amarillo-fondo text-semaforo-amarillo"],
      [seg.alertaCalificacion, "notification_important", "Alerta por calificación", null, ROJA],
      [seg.alertaArticulos, "gavel", "Riesgo art. 33-35", "Ya reprobó esta materia y hoy está en rojo", ROJA],
      [seg.rezagoCritico, "history_toggle_off", "Rezago crítico", seg.detalleRezago, ROJA],
      [seg.riesgoPorHistorial, "workspace_premium", "Riesgo por historial", "Reprobó en sus dos ciclos anteriores", ROJA]
    ];
    for (const [activa, nombreIcono, texto, detalle, clases] of banderas) {
      if (!activa) continue;
      const alerta = el("span", `mt-1 mr-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-helper-sm text-helper-sm font-semibold ${clases}`);
      if (detalle) alerta.title = detalle;
      alerta.append(icono(nombreIcono, "text-[14px]"), el("span", "", texto));
      celdaRiesgo.append(el("br"), alerta);
    }
  } else {
    for (const celda of [celdaAsistencia, celdaCalificacion, celdaRiesgo]) celda.appendChild(el("span", "text-on-surface-variant", "—"));
  }

  const celdaAcciones = el("td", "py-space-md px-space-lg text-right");
  const accion = activo ? boton("Dar de baja", "person_remove", "peligro") : boton("Reactivar", "person_add", "suave");
  accion.addEventListener("click", () => cambiarEstadoAlumno(a, activo ? "baja" : "activo", accion));
  celdaAcciones.appendChild(accion);

  fila.append(celdaAlumno, celdaInscripcion, celdaAsistencia, celdaCalificacion, celdaRiesgo, celdaAcciones);
  return fila;
}

// RF-16: un alumno de baja deja de aparecer en asistencia y calificaciones; se puede reactivar.
async function cambiarEstadoAlumno(alumno, estado, boton) {
  const nombre = `${alumno.nombre} ${alumno.apellidos}`;
  const ok = estado === "baja"
    ? await confirmar(`¿Dar de baja a ${nombre}?`, "Dejará de aparecer en la asistencia, las calificaciones y el seguimiento. Sus registros se conservan y puedes reactivarlo después.", "Dar de baja")
    : await confirmar(`¿Reactivar a ${nombre}?`, "Volverá a aparecer en la asistencia, las calificaciones y el seguimiento con sus registros anteriores.", "Reactivar");
  if (!ok) return;
  boton.disabled = true;
  try {
    await pedir(rutaCurso(`/alumnos/${alumno.matricula_id}/estado`), { metodo: "PATCH", datos: { estado }, conToken: true });
    await Promise.all([cargarMatricula(), cargarAsistencia(), cargarCalificaciones()]);
    pintarMetricas();
  } catch (error) {
    avisarError(error);
    boton.disabled = false;
  }
}

// ==================== CONFIGURAR CURSO (RF-10, RF-12, RF-13, RF-17) ====================

function abrirConfigurar() {
  const c = C.curso;
  limpiarErrores("aviso-configurar");
  document.getElementById("cfg-materia").value = c.nombreMateria;
  document.getElementById("cfg-seccion").value = c.seccion;
  document.getElementById("cfg-descripcion").value = c.descripcion || "";
  document.getElementById("cfg-hora-inicio").value = c.horaInicio;
  document.getElementById("cfg-hora-fin").value = c.horaFin;
  document.querySelectorAll('input[name="cfgTipoEvaluacion"]').forEach(r => { r.checked = r.value === c.tipoEvaluacion; });

  const lista = document.getElementById("cfg-lista-materias");
  lista.innerHTML = "";
  for (const m of C.materias) {
    const opcion = el("option");
    opcion.value = m.nombre;
    opcion.label = m.clave;
    lista.appendChild(opcion);
  }

  const dias = document.getElementById("cfg-dias");
  dias.innerHTML = "";
  for (const [valor, , largo] of DIAS) {
    const opcion = el("label", "cursor-pointer");
    const casilla = el("input", "peer sr-only");
    casilla.type = "checkbox";
    casilla.name = "cfgDias";
    casilla.value = valor;
    casilla.checked = c.diasSemana.includes(valor);
    opcion.append(casilla, el("span", "inline-flex items-center px-space-md py-space-sm rounded-full font-label-lg text-label-lg bg-surface-container-low text-on-surface-variant transition-colors peer-checked:bg-secondary peer-checked:text-on-secondary peer-focus-visible:ring-2 peer-focus-visible:ring-secondary", largo));
    dias.appendChild(opcion);
  }

  const archivado = c.estado === "archivado";
  document.getElementById("cfg-estado-titulo").textContent = archivado ? "El curso está archivado" : "Archivar el curso";
  document.getElementById("cfg-estado-texto").textContent = archivado
    ? "Reactívalo para que vuelva a aceptar inscripciones y aparezca en tus cursos activos."
    : "Al final del semestre: se oculta de tus cursos activos y deja de aceptar inscripciones. Nada se borra.";
  const b = document.getElementById("btn-cambiar-estado");
  b.className = `shrink-0 inline-flex items-center justify-center gap-space-xs font-label-md text-label-md px-space-md py-space-sm rounded-lg transition-colors ${archivado ? "bg-primary-container text-on-primary hover:bg-primary" : "bg-surface-container-lowest text-error hover:bg-error-container"}`;
  b.innerHTML = "";
  b.append(icono(archivado ? "unarchive" : "inventory_2"), el("span", "", archivado ? "Reactivar curso" : "Archivar curso"));
  abrirModal("modal-configurar");
}

async function guardarConfiguracion(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-configurar");
  const valor = id => document.getElementById(id).value.trim();
  const datos = {
    nombreMateria: valor("cfg-materia"),
    seccion: valor("cfg-seccion").toUpperCase(),
    descripcion: valor("cfg-descripcion"),
    diasSemana: [...document.querySelectorAll('input[name="cfgDias"]:checked')].map(c => c.value),
    horaInicio: valor("cfg-hora-inicio"),
    horaFin: valor("cfg-hora-fin"),
    tipoEvaluacion: document.querySelector('input[name="cfgTipoEvaluacion"]:checked')?.value
  };
  if (!datos.nombreMateria || !datos.seccion || !datos.descripcion || !datos.diasSemana.length || !datos.horaInicio || !datos.horaFin) {
    mostrarAviso("Completa materia, sección, descripción, al menos un día y el horario.", "error", "aviso-configurar");
    return;
  }
  if (datos.horaFin <= datos.horaInicio) {
    mostrarAviso("La hora de fin debe ser posterior a la hora de inicio.", "error", "aviso-configurar");
    return;
  }
  const b = document.getElementById("btn-guardar-configurar");
  botonCargando(b, true);
  try {
    C.curso = await pedir(rutaCurso(), { metodo: "PATCH", datos, conToken: true });
    pintarFicha();
    cerrarModal("modal-configurar");
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error, "aviso-configurar");
  } finally {
    botonCargando(b, false);
  }
}

// RF-10: archivar al final del semestre o reactivar
async function cambiarEstadoCurso() {
  const archivar = C.curso.estado === "activo";
  const ok = archivar
    ? await confirmar("¿Archivar este curso?", "Se ocultará de tus cursos activos y dejará de aceptar inscripciones. Podrás reactivarlo cuando quieras.", "Archivar")
    : await confirmar("¿Reactivar este curso?", "Volverá a tus cursos activos y aceptará inscripciones con su código.", "Reactivar");
  if (!ok) return;
  try {
    C.curso = await pedir(rutaCurso("/estado"), { metodo: "PATCH", datos: { estado: archivar ? "archivado" : "activo" }, conToken: true });
    pintarFicha();
    cerrarModal("modal-configurar");
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error, "aviso-configurar");
  }
}
