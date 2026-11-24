// ============================================================
// curso-alumno.js: panel consolidado de un curso para el alumno (curso-alumno.html?id=N).
//   RF-62  Bloques de asistencia, evaluación y tareas pendientes
//   RF-63  Encuadre: categorías y porcentajes            -> GET /alumno/cursos/{id}/encuadre
//   RF-64 a RF-66  % de asistencia, estatus UdeG y color  -> GET /alumno/cursos/{id}/seguimiento
//   RF-67, RF-68  Acumulada real y puntos perdidos
//   RF-69, RF-70  Pendientes por fecha, con enlace a la entrega -> GET /alumno/cursos/{id}/actividades
//   RF-71  Historial con calificación y retroalimentación -> GET /alumno/cursos/{id}/calificaciones
//   RF-72  Botón para buscar asesoría si el semáforo es amarillo o rojo
// ============================================================

document.addEventListener("DOMContentLoaded", iniciarCursoAlumno);

const ID_CURSO = Number(new URLSearchParams(location.search).get("id"));
const COLORES_ENCUADRE = ["#0f2c59", "#305ea1", "#de7b0e", "#8ab4fd", "#6e3900", "#7c94c8", "#465e8e", "#ffb77d"];

const TEXTO_SEMAFORO = {
  verde: "Vas bien en asistencia y calificación.",
  amarillo: "Atención: estás cerca del límite en asistencia o calificación.",
  rojo: "En riesgo: revisa tu asistencia y tus calificaciones."
};

async function iniciarCursoAlumno() {
  const perfil = await protegerPagina(["estudiante"]);
  if (!perfil) return;
  if (!ID_CURSO) return window.location.replace("estudiante.html");
  const ruta = resto => `/alumno/cursos/${ID_CURSO}${resto}`;
  let datos;
  try {
    const [curso, seguimiento, calificaciones, encuadre, actividades] = await Promise.all([
      pedir(ruta(""), { conToken: true }),
      pedir(ruta("/seguimiento"), { conToken: true }),
      pedir(ruta("/calificaciones"), { conToken: true }),
      pedir(ruta("/encuadre"), { conToken: true }),
      pedir(ruta("/actividades"), { conToken: true })
    ]);
    datos = { curso, seguimiento, calificaciones, encuadre, actividades };
  } catch (error) {
    document.getElementById("curso-cargando").classList.add("hidden");
    if (error.status !== 401) mostrarErrorApi(error);
    return;
  }
  pintarFicha(datos.curso, datos.seguimiento);
  pintarAlertas(datos.seguimiento);
  pintarCalificacion(datos.seguimiento);
  pintarAsistencia(datos.seguimiento);
  pintarEncuadre(datos.encuadre, datos.actividades);
  pintarPendientes(datos.actividades);
  pintarHistorial(datos.actividades, datos.calificaciones);
  document.getElementById("curso-cargando").classList.add("hidden");
  document.getElementById("curso-contenido").classList.remove("hidden");
}

function pintarFicha(c, seg) {
  document.title = `${c.nombreMateria} · SEPA CUCEI`;
  document.getElementById("miga-curso").textContent = c.nombreMateria;
  document.getElementById("curso-ciclo").textContent = c.ciclo ? `Ciclo ${c.ciclo}` : "";
  document.getElementById("curso-titulo").textContent = `${c.nombreMateria} — Sección ${c.seccion}`;
  const datos = document.getElementById("curso-datos");
  const dato = (nombreIcono, texto) => {
    const s = el("span", "inline-flex items-center gap-space-xs");
    s.append(icono(nombreIcono, "text-[18px] text-on-surface-variant"), el("span", "", texto));
    return s;
  };
  datos.append(dato("person", `Profesor: ${c.profesor || "sin asignar"}`),
    dato("calendar_month", `${diasCortos(c.diasSemana)} · ${c.horaInicio} – ${c.horaFin}`));
  if (c.tipoEvaluacion === "numerica") datos.appendChild(dato("grading", `Mínimo aprobatorio: ${Math.round(c.umbralNumerico)}`));

  const color = seg.semaforoGeneral;
  document.getElementById("franja-semaforo").className = `h-1.5 ${SEMAFORO[color].punto}`;
  document.getElementById("curso-semaforo").appendChild(chipSemaforo(color, `Semáforo: ${SEMAFORO[color].texto}`));
  document.getElementById("curso-semaforo-texto").textContent = TEXTO_SEMAFORO[color];
  // RF-72: en amarillo o rojo se invita a buscar asesoría (el tablero aún no existe)
  document.getElementById("btn-asesoria").classList.toggle("hidden", color === "verde");
}

function tarjetaAlerta(nombreIcono, titulo, texto, clases) {
  const t = el("div", `p-space-md rounded-xl flex items-start gap-space-sm ${clases}`);
  const textos = el("div");
  textos.append(el("p", "font-label-lg text-label-lg", titulo), el("p", "font-body-md text-body-md", texto));
  t.append(icono(nombreIcono, "text-[22px]"), textos);
  return t;
}

function pintarAlertas(seg) {
  const contenedor = document.getElementById("alertas");
  if (seg.alertaCalificacion) {
    contenedor.appendChild(tarjetaAlerta("notification_important", "Alerta por calificación",
      `Llevas ${numero(seg.desempenoProporcional, 1)} % de los puntos que se han evaluado hasta hoy; el mínimo aprobatorio es 60 %. Habla con tu profesor y busca asesoría.`,
      "bg-semaforo-rojo-fondo text-semaforo-rojo"));
  }
  // RF-83: aviso por asistencia en amarillo o rojo (la biblioteca de normatividad se enlazará aquí)
  if (seg.semaforoAsistencia !== "verde") {
    contenedor.appendChild(tarjetaAlerta("event_busy", "Tu asistencia está en riesgo",
      `Tienes ${numero(seg.porcentajeAsistencia, 1)} % de asistencia (${seg.estatusNormativo}). Con menos de 80 % pierdes el derecho a la evaluación ordinaria y con menos de 65 %, también a la extraordinaria.`,
      seg.semaforoAsistencia === "rojo" ? "bg-semaforo-rojo-fondo text-semaforo-rojo" : "bg-semaforo-amarillo-fondo text-semaforo-amarillo"));
  }
}

// RF-67, RF-68
function pintarCalificacion(seg) {
  const bloque = document.getElementById("bloque-calificacion");
  const principal = el("div", "p-space-md rounded-xl bg-surface-container-low text-center mb-space-md");
  principal.append(
    el("p", "font-caption text-caption uppercase tracking-wider text-on-surface-variant", "Calificación acumulada real"),
    el("p", "text-[40px] leading-tight font-bold text-primary mt-1", numero(seg.calificacionAcumulada)),
    el("p", "font-body-md text-body-md text-on-surface-variant", "de 100 puntos del curso")
  );
  bloque.appendChild(principal);

  const fila = (texto, valor, clases = "text-on-surface") => {
    const f = el("div", "flex items-center justify-between py-1.5 border-b border-surface-container last:border-0");
    f.append(el("span", "font-body-md text-body-md text-on-surface-variant", texto), el("span", `font-label-lg text-label-lg ${clases}`, valor));
    return f;
  };
  bloque.append(
    fila("Puntos evaluados hasta hoy", numero(seg.puntosPosibles)),
    fila("Puntos obtenidos", numero(seg.calificacionAcumulada), "text-semaforo-verde"),
    fila("Puntos perdidos", numero(seg.puntosPerdidos), seg.puntosPerdidos ? "text-error" : "text-on-surface"),
    fila("Desempeño en lo evaluado", seg.desempenoProporcional === null ? "Sin evaluaciones aún" : `${numero(seg.desempenoProporcional, 1)} %`,
      seg.alertaCalificacion ? "text-error" : "text-primary")
  );
  if (seg.puntosPosibles > 0) {
    const barra = el("div", "h-2.5 w-full rounded-full bg-surface-container overflow-hidden flex mt-space-md");
    const ganados = el("div", "h-full bg-semaforo-verde");
    ganados.style.width = `${seg.calificacionAcumulada}%`;
    const perdidos = el("div", "h-full bg-semaforo-rojo");
    perdidos.style.width = `${seg.puntosPerdidos}%`;
    barra.append(ganados, perdidos);
    bloque.append(barra, el("p", "font-caption text-caption text-on-surface-variant mt-1", "Verde: obtenidos · Rojo: perdidos · Gris: por evaluar"));
  }
}

// RF-64 a RF-66: porcentaje, estatus normativo y color del semáforo de asistencia
function pintarAsistencia(seg) {
  const bloque = document.getElementById("bloque-asistencia");
  const color = { verde: "#1b6e3a", amarillo: "#de7b0e", rojo: "#ba1a1a" }[seg.semaforoAsistencia];
  const anillo = el("div", "relative w-36 h-36 mx-auto rounded-full flex items-center justify-center");
  anillo.style.background = `conic-gradient(${color} ${seg.porcentajeAsistencia}%, #e5eeff 0)`;
  const centro = el("div", "w-28 h-28 rounded-full bg-surface-container-lowest flex flex-col items-center justify-center");
  centro.append(el("span", "text-[28px] font-bold text-primary leading-none", `${numero(seg.porcentajeAsistencia, 1)}%`),
    el("span", "font-caption text-caption text-on-surface-variant mt-1", "asistencia"));
  anillo.appendChild(centro);
  const estatus = el("div", "mt-space-md flex items-center justify-between p-space-sm rounded-lg bg-surface-container-low");
  estatus.append(el("span", "font-body-md text-body-md text-on-surface-variant", "Estatus UdeG"), chipSemaforo(seg.semaforoAsistencia, seg.estatusNormativo));
  bloque.append(anillo, estatus,
    el("p", "font-helper-sm text-helper-sm text-on-surface-variant mt-space-sm", "Ordinario ≥ 80 % · Extraordinario ≥ 65 % · Sin Derecho < 65 %. Un retardo cuenta como asistencia."));
}

// RF-63
function pintarEncuadre(encuadre, actividades) {
  const bloque = document.getElementById("bloque-encuadre");
  if (!encuadre.categorias.length) {
    bloque.appendChild(el("p", "text-on-surface-variant", "Tu profesor aún no publica el encuadre de evaluación."));
    return;
  }
  const barra = el("div", "h-3 w-full rounded-full bg-surface-container overflow-hidden flex mb-space-md");
  const lista = el("div", "space-y-space-xs");
  encuadre.categorias.forEach((c, i) => {
    const colorCat = COLORES_ENCUADRE[i % COLORES_ENCUADRE.length];
    const seg = el("div", "h-full");
    seg.style.width = `${c.porcentajePeso}%`;
    seg.style.backgroundColor = colorCat;
    barra.appendChild(seg);
    const cuantas = actividades.filter(a => a.categoria === c.nombre).length;
    const fila = el("div", "flex items-center justify-between gap-space-sm p-space-sm rounded-lg bg-surface-container-low");
    const nombre = el("span", "flex items-center gap-space-sm min-w-0");
    const punto = el("span", "w-2.5 h-2.5 rounded-full shrink-0");
    punto.style.backgroundColor = colorCat;
    const textos = el("span", "min-w-0");
    textos.append(el("span", "block font-label-lg text-label-lg text-on-surface truncate", c.nombre),
      el("span", "block font-caption text-caption text-on-surface-variant", cuantas ? `${cuantas} actividad${cuantas === 1 ? "" : "es"}` : "Sin actividades aún"));
    nombre.append(punto, textos);
    fila.append(nombre, el("span", "font-title-lg text-title-lg text-primary", `${numero(c.porcentajePeso)} %`));
    lista.appendChild(fila);
  });
  bloque.append(barra, lista);
  if (encuadre.advertencia) bloque.appendChild(el("p", "font-helper-sm text-helper-sm text-on-tertiary-container mt-space-sm", "El encuadre aún no suma 100 %."));
}

function diasRestantes(fechaLimite) {
  const horas = (new Date(fechaLimite) - new Date()) / 36e5;
  if (horas < 0) return null;
  if (horas < 24) return `vence en ${Math.max(1, Math.round(horas))} h`;
  const dias = Math.round(horas / 24);
  return `vence en ${dias} día${dias === 1 ? "" : "s"}`;
}

// RF-69, RF-70: lo que aún no envía, del vencimiento más próximo al más lejano
function pintarPendientes(actividades) {
  const lista = document.getElementById("lista-pendientes");
  const pendientes = actividades.filter(a => !a.entrega)
    .sort((x, y) => x.fechaHoraLimite.localeCompare(y.fechaHoraLimite));
  if (!pendientes.length) {
    lista.appendChild(el("p", "text-on-surface-variant", "No tienes tareas pendientes. ¡Al día!"));
    return;
  }
  for (const a of pendientes) {
    const vencida = a.estadoEntrega === "vencida";
    const item = el("a", `flex items-center gap-space-md p-space-md rounded-xl transition-colors ${vencida ? "bg-semaforo-rojo-fondo/60 hover:bg-semaforo-rojo-fondo" : "bg-surface-container-low hover:bg-surface-container"}`);
    item.href = `entrega.html?curso=${ID_CURSO}&actividad=${a.id}`;
    const textos = el("div", "flex-1 min-w-0");
    textos.append(el("p", "font-label-lg text-label-lg text-primary truncate", a.titulo),
      el("p", "font-helper-sm text-helper-sm text-on-surface-variant", `${a.categoria} · ${numero(a.puntuacionMaxima)} pts · límite ${fechaHora(a.fechaHoraLimite)}`));
    const estado = el("span", `shrink-0 font-label-md text-label-md ${vencida ? "text-semaforo-rojo" : "text-secondary"}`,
      vencida ? "Vencida: aún puedes entregar con retraso" : diasRestantes(a.fechaHoraLimite));
    item.append(textos, estado, icono("chevron_right", "text-[20px] text-on-surface-variant"));
    lista.appendChild(item);
  }
}

// RF-71: tareas entregadas o vencidas, con nota y retroalimentación
function pintarHistorial(actividades, calificaciones) {
  const lista = document.getElementById("lista-historial");
  const celdas = new Map(calificaciones.celdas.map(c => [c.actividad_id, c]));
  const pasadas = actividades.filter(a => a.entrega || a.estadoEntrega === "vencida")
    .sort((x, y) => y.fechaHoraLimite.localeCompare(x.fechaHoraLimite));
  if (!pasadas.length) {
    lista.appendChild(el("p", "text-on-surface-variant", "Aún no tienes entregas."));
    return;
  }
  for (const a of pasadas) {
    const celda = celdas.get(a.id);
    const calif = celda?.calificacion;
    const item = el("a", "block p-space-md rounded-xl bg-surface-container-low hover:bg-surface-container transition-colors");
    item.href = `entrega.html?curso=${ID_CURSO}&actividad=${a.id}`;
    const cabeza = el("div", "flex items-start justify-between gap-space-sm");
    const textos = el("div", "min-w-0");
    const detalle = a.entrega
      ? `Entregada ${fechaHora(a.entrega.fechaHoraEntrega)}${a.entrega.entregadoConRetraso ? " · con retraso" : ""}`
      : "No entregada: cuenta como 0";
    textos.append(el("p", "font-label-lg text-label-lg text-primary truncate", a.titulo),
      el("p", `font-helper-sm text-helper-sm ${a.entrega ? "text-on-surface-variant" : "text-error"}`, detalle));
    let nota;
    if (calif) nota = el("span", "font-title-lg text-title-lg text-primary shrink-0", `${numero(calif.calificacionObtenida)}/${numero(a.puntuacionMaxima)}`);
    else if (a.entrega) nota = el("span", "font-label-md text-label-md text-on-tertiary-container shrink-0", "Por calificar");
    else nota = el("span", "font-title-lg text-title-lg text-error shrink-0", `0/${numero(a.puntuacionMaxima)}`);
    cabeza.append(textos, nota);
    item.appendChild(cabeza);
    if (calif?.retroalimentacion) {
      const retro = el("p", "mt-space-sm p-space-sm rounded-lg bg-surface-container-lowest font-body-md text-body-md text-on-surface flex gap-space-xs");
      retro.append(icono("chat", "text-[18px] text-secondary"), el("span", "", calif.retroalimentacion));
      item.appendChild(retro);
    }
    lista.appendChild(item);
  }
}
