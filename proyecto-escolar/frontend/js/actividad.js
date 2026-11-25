// ============================================================
// actividad.js: revisar entregas y calificar una actividad (actividad.html?curso=N&actividad=M).
//   RF-40  Tabla de alumnos activos con su estatus de entrega -> GET .../actividades/{id}/entregas
//   RF-41  Descargar el archivo entregado                       -> GET /entregas/{id}/archivo
//   RF-42, RF-43  Calificación de 0 a la puntuación máxima      -> PUT .../entregas/{id}/calificacion
//   RF-44  Retroalimentación opcional
//   RF-47  Sin entrega y vencida: cuenta como 0 automáticamente (no se califica a mano)
//   La calificación actual de cada alumno sale de GET .../calificaciones.
// ============================================================

document.addEventListener("DOMContentLoaded", iniciarActividad);

const PARAMS = new URLSearchParams(location.search);
const CURSO = Number(PARAMS.get("curso"));
const ACTIVIDAD = Number(PARAMS.get("actividad"));

const ESTADO_ENTREGA = {
  entregada: ["Entregada", "bg-semaforo-verde-fondo text-semaforo-verde", "task_alt"],
  entregada_con_retraso: ["Con retraso", "bg-semaforo-amarillo-fondo text-semaforo-amarillo", "schedule"],
  pendiente: ["Pendiente", "bg-surface-container text-on-surface-variant", "hourglass_empty"],
  vencida: ["Sin entrega", "bg-semaforo-rojo-fondo text-semaforo-rojo", "block"]
};

const FILTROS = [
  ["todos", "Todos"],
  ["por_calificar", "Por calificar"],
  ["calificadas", "Calificadas"],
  ["sin_entrega", "Sin entrega"]
];

let actividad = null;
let filas = [];          // un registro por alumno: datos + entrega + calificación
let filtro = "todos";
let elegido = null;      // matricula_id del alumno en el panel

function ruta(resto = "") {
  return `/docente/cursos/${CURSO}${resto}`;
}

async function iniciarActividad() {
  const perfil = await protegerPagina(["docente"]);
  if (!perfil) return;
  if (!CURSO || !ACTIVIDAD) return window.location.replace("docente.html");
  document.getElementById("miga-curso").href = `curso.html?id=${CURSO}#actividades`;
  document.getElementById("form-calificar").addEventListener("submit", e => { e.preventDefault(); guardarNota(false); });
  document.getElementById("btn-guardar-siguiente").addEventListener("click", () => guardarNota(true));

  try {
    const [curso, act] = await Promise.all([
      pedir(ruta(), { conToken: true }),
      pedir(ruta(`/actividades/${ACTIVIDAD}`), { conToken: true })
    ]);
    actividad = act;
    document.getElementById("miga-curso").textContent = `${curso.nombreMateria} · ${curso.seccion}`;
    pintarActividad();
    await cargarFilas();
  } catch (error) {
    document.getElementById("actividad-cargando").classList.add("hidden");
    if (error.status !== 401) mostrarErrorApi(error);
    return;
  }
  document.getElementById("actividad-cargando").classList.add("hidden");
  document.getElementById("actividad-contenido").classList.remove("hidden");
}

function pintarActividad() {
  const a = actividad;
  document.title = `${a.titulo} · SEPA CUCEI`;
  document.getElementById("miga-actividad").textContent = a.titulo;
  document.getElementById("act-categoria").textContent = `${a.categoria} · vale ${numero(a.valorEnCurso)} % del curso`;
  document.getElementById("act-titulo").textContent = a.titulo;
  document.getElementById("act-descripcion").textContent = a.descripcion || "";
  const datos = document.getElementById("act-datos");
  datos.innerHTML = "";
  const dato = (nombreIcono, texto) => {
    const s = el("span", "inline-flex items-center gap-space-xs");
    s.append(icono(nombreIcono, "text-[18px] text-on-surface-variant"), el("span", "", texto));
    return s;
  };
  datos.append(dato("event", `Fecha límite: ${fechaHora(a.fechaHoraLimite)}`), dato("star", `Puntuación máxima: ${numero(a.puntuacionMaxima)}`));
  const acciones = document.getElementById("act-acciones");
  acciones.innerHTML = "";
  if (a.tieneArchivo) {
    const b = boton("Archivo de la actividad", "download", "suave");
    b.addEventListener("click", () => descargarArchivo(`/actividades/${a.id}/archivo`).catch(mostrarErrorApi));
    acciones.appendChild(b);
  }
  document.getElementById("label-nota").textContent = `Calificación (0 a ${numero(a.puntuacionMaxima)})`;
  document.getElementById("input-nota").max = a.puntuacionMaxima;
}

async function cargarFilas() {
  const [entregas, cuadricula] = await Promise.all([
    pedir(ruta(`/actividades/${ACTIVIDAD}/entregas`), { conToken: true }),
    pedir(ruta("/calificaciones"), { conToken: true })
  ]);
  const columna = cuadricula.actividades.findIndex(a => a.id === ACTIVIDAD);
  const celdas = new Map(cuadricula.alumnos.map(f => [f.matricula_id, f.celdas[columna]]));
  filas = entregas.map(e => ({ ...e, celda: celdas.get(e.matricula_id) }));
  pintarMetricas();
  pintarFiltros();
  pintarTabla();
  if (elegido) mostrarPanel(elegido);
}

function pintarMetricas() {
  const contenedor = document.getElementById("act-metricas");
  contenedor.innerHTML = "";
  const conEntrega = filas.filter(f => f.entrega);
  const tarjeta = (nombreIcono, valor, texto) => {
    const t = el("div", "p-space-md rounded-xl bg-surface-container-low flex items-center gap-space-md");
    const caja = el("span", "w-11 h-11 rounded-lg bg-surface-container-lowest flex items-center justify-center text-secondary shrink-0");
    caja.appendChild(icono(nombreIcono, "text-[22px]"));
    const textos = el("div");
    textos.append(el("p", "font-headline-md text-headline-md text-primary", valor), el("p", "font-helper-sm text-helper-sm text-on-surface-variant", texto));
    t.append(caja, textos);
    return t;
  };
  contenedor.append(
    tarjeta("inbox", `${conEntrega.length} / ${filas.length}`, "entregaron"),
    tarjeta("schedule", String(filas.filter(f => f.estadoEntrega === "entregada_con_retraso").length), "con retraso"),
    tarjeta("fact_check", String(filas.filter(f => f.celda?.calificacion).length), "calificadas"),
    tarjeta("block", String(filas.filter(f => f.estadoEntrega === "vencida").length), "vencidas sin entrega (cuentan 0)")
  );
}

function coincideFiltro(f) {
  if (filtro === "por_calificar") return f.entrega && !f.celda?.calificacion;
  if (filtro === "calificadas") return Boolean(f.celda?.calificacion);
  if (filtro === "sin_entrega") return !f.entrega;
  return true;
}

function pintarFiltros() {
  const contenedor = document.getElementById("filtros-entrega");
  contenedor.innerHTML = "";
  for (const [clave, texto] of FILTROS) {
    const anterior = filtro;
    filtro = clave;
    const cuantos = filas.filter(coincideFiltro).length;
    filtro = anterior;
    const b = el("button", `px-space-md py-1.5 rounded-lg font-label-md text-label-md transition-colors ${clave === filtro ? "bg-primary-container text-on-primary" : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container"}`, `${texto} (${cuantos})`);
    b.type = "button";
    b.addEventListener("click", () => {
      filtro = clave;
      pintarFiltros();
      pintarTabla();
    });
    contenedor.appendChild(b);
  }
}

function pintarTabla() {
  const cuerpo = document.getElementById("tabla-entregas");
  const vacia = document.getElementById("entregas-vacia");
  cuerpo.innerHTML = "";
  const visibles = filas.filter(coincideFiltro);
  vacia.classList.toggle("hidden", visibles.length > 0);
  vacia.textContent = filas.length ? "Ningún alumno en este filtro." : "No hay alumnos activos en el curso.";

  for (const f of visibles) {
    const seleccionada = f.matricula_id === elegido;
    const tr = el("tr", `border-t border-surface-container cursor-pointer transition-colors ${seleccionada ? "bg-surface-container-high" : "hover:bg-surface-container-low"}`);
    tr.tabIndex = 0;
    tr.addEventListener("click", () => mostrarPanel(f.matricula_id));
    tr.addEventListener("keydown", e => { if (e.key === "Enter") mostrarPanel(f.matricula_id); });

    const alumno = el("td", "py-space-md px-space-lg");
    alumno.append(el("p", "font-label-lg text-label-lg text-primary", `${f.apellidos} ${f.nombre}`),
      el("p", "font-helper-sm text-helper-sm text-on-surface-variant font-mono", f.codigoEstudiante));

    const entrega = el("td", "py-space-md px-space-md");
    const [texto, clases, nombreIcono] = ESTADO_ENTREGA[f.estadoEntrega];
    const chip = el("span", `inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-label-md text-label-md ${clases}`);
    chip.append(icono(nombreIcono, "text-[14px]"), el("span", "", texto));
    entrega.appendChild(chip);
    if (f.entrega) entrega.appendChild(el("p", "font-helper-sm text-helper-sm text-on-surface-variant mt-1", fechaHora(f.entrega.fechaHoraEntrega)));

    const nota = el("td", "py-space-md px-space-md text-right");
    if (f.celda?.calificacion) {
      nota.appendChild(el("span", "font-label-lg text-label-lg text-primary", `${numero(f.celda.calificacion.calificacionObtenida)} / ${numero(actividad.puntuacionMaxima)}`));
    } else if (f.entrega) {
      nota.appendChild(el("span", "font-label-md text-label-md text-on-tertiary-container", "Por calificar"));
    } else if (f.celda?.cuentaComoCero) {
      nota.appendChild(el("span", "font-label-lg text-label-lg text-error", "0"));
    } else {
      nota.appendChild(el("span", "text-outline", "—"));
    }
    tr.append(alumno, entrega, nota);
    cuerpo.appendChild(tr);
  }
}

// ==================== PANEL DE EVALUACIÓN ====================

function mostrarPanel(matriculaId) {
  elegido = matriculaId;
  const f = filas.find(x => x.matricula_id === matriculaId);
  if (!f) return;
  pintarTabla();
  limpiarErrores("aviso-calificar");
  document.getElementById("panel-vacio").classList.add("hidden");
  document.getElementById("panel-alumno").classList.remove("hidden");
  document.getElementById("panel-nombre").textContent = `${f.nombre} ${f.apellidos}`;
  document.getElementById("panel-codigo").textContent = f.codigoEstudiante;

  const caja = document.getElementById("panel-entrega");
  caja.innerHTML = "";
  const form = document.getElementById("form-calificar");
  if (f.entrega) {
    const [texto] = ESTADO_ENTREGA[f.estadoEntrega];
    caja.append(
      el("p", "font-label-lg text-label-lg text-on-surface", texto),
      el("p", "font-body-md text-body-md text-on-surface-variant", `Entregó el ${fechaHora(f.entrega.fechaHoraEntrega)}`)
    );
    const descargar = boton("Descargar entrega", "download", "secundario");
    descargar.addEventListener("click", () => descargarArchivo(`/entregas/${f.entrega.id}/archivo`).catch(e => mostrarErrorApi(e, "aviso-calificar")));
    caja.appendChild(descargar);
    form.classList.remove("hidden");
    const actual = f.celda?.calificacion;
    document.getElementById("input-nota").value = actual ? actual.calificacionObtenida : "";
    document.getElementById("input-retro").value = actual?.retroalimentacion || "";
    if (actual) caja.appendChild(el("p", "font-helper-sm text-helper-sm text-on-surface-variant", `Calificada el ${fechaHora(actual.fecha)}. Puedes corregirla.`));
    document.getElementById("input-nota").focus();
  } else {
    caja.append(
      el("p", "font-label-lg text-label-lg text-on-surface", f.estadoEntrega === "vencida" ? "No entregó" : "Aún no entrega"),
      el("p", "font-body-md text-body-md text-on-surface-variant", f.estadoEntrega === "vencida"
        ? "La fecha límite ya pasó."
        : `Tiene hasta el ${fechaHora(actividad.fechaHoraLimite)}. Si no entrega, contará como 0.`)
    );
    form.classList.add("hidden");
  }
}

async function guardarNota(irASiguiente) {
  const f = filas.find(x => x.matricula_id === elegido);
  if (!f?.entrega) return;
  limpiarErrores("aviso-calificar");
  const texto = document.getElementById("input-nota").value.trim();
  const nota = Number(texto);
  if (texto === "" || !(nota >= 0 && nota <= actividad.puntuacionMaxima)) {
    marcarCampo("calificacionObtenida", `Debe estar entre 0 y ${numero(actividad.puntuacionMaxima)} (RF-43)`);
    return;
  }
  const datos = { calificacionObtenida: nota, retroalimentacion: document.getElementById("input-retro").value.trim() || null };
  const b = document.getElementById(irASiguiente ? "btn-guardar-siguiente" : "btn-guardar-nota");
  botonCargando(b, true);
  try {
    await pedir(ruta(`/entregas/${f.entrega.id}/calificacion`), { metodo: "PUT", datos, conToken: true });
    if (irASiguiente) {
      // El siguiente alumno que entregó y aún no tiene calificación
      const pendientes = filas.filter(x => x.entrega && !x.celda?.calificacion && x.matricula_id !== f.matricula_id);
      elegido = pendientes[0]?.matricula_id ?? f.matricula_id;
    }
    await cargarFilas();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error, "aviso-calificar");
  } finally {
    botonCargando(b, false);
  }
}
