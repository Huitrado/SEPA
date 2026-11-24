// ============================================================
// entrega.js: detalle de una actividad y entrega del alumno (entrega.html?curso=N&actividad=M).
//   RF-35  Título, descripción, categoría, puntuación máxima y fecha límite
//   RF-36  Descargar el archivo del profesor y subir el propio   -> POST /alumno/actividades/{id}/entrega
//   RF-37  La fecha y hora de entrega las pone el servidor
//   RF-38  Cancelar y volver a subir antes de la fecha límite     -> DELETE /alumno/actividades/{id}/entrega
//   RF-39  Después de la fecha se acepta, marcada con retraso
//   RF-45  Calificación y retroalimentación del profesor          -> GET /alumno/cursos/{id}/calificaciones
// RNF-8: máximo 10 MB; se revisa aquí para avisar antes y el backend lo vuelve a revisar.
// ============================================================

document.addEventListener("DOMContentLoaded", iniciarEntrega);

const Q = new URLSearchParams(location.search);
const CURSO_ID = Number(Q.get("curso"));
const ACTIVIDAD_ID = Number(Q.get("actividad"));
const LIMITE_BYTES = 10 * 1024 * 1024;
const EXTENSIONES = [".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".zip"];

const ESTADOS = {
  pendiente: ["Pendiente", "bg-surface-container text-on-surface-variant"],
  vencida: ["Sin entregar", "bg-semaforo-rojo-fondo text-semaforo-rojo"],
  entregada: ["Entregada", "bg-semaforo-verde-fondo text-semaforo-verde"],
  entregada_con_retraso: ["Entregada con retraso", "bg-semaforo-amarillo-fondo text-semaforo-amarillo"]
};

let actividad = null;

async function iniciarEntrega() {
  const perfil = await protegerPagina(["estudiante"]);
  if (!perfil) return;
  if (!CURSO_ID || !ACTIVIDAD_ID) return window.location.replace("estudiante.html");
  document.getElementById("miga-curso").href = `curso-alumno.html?id=${CURSO_ID}`;
  document.getElementById("input-archivo").addEventListener("change", mostrarArchivoElegido);
  document.getElementById("form-entrega").addEventListener("submit", enviarEntrega);
  document.getElementById("btn-cancelar-entrega").addEventListener("click", cancelarEntrega);
  document.getElementById("btn-descargar-guia").addEventListener("click",
    () => descargarArchivo(`/actividades/${ACTIVIDAD_ID}/archivo`).catch(e => mostrarErrorApi(e)));
  document.getElementById("btn-descargar-mia").addEventListener("click",
    () => descargarArchivo(`/entregas/${actividad.entrega.id}/archivo`).catch(e => mostrarErrorApi(e, "aviso-entrega")));
  activarArrastrar();
  await cargar();
}

async function cargar() {
  try {
    const [curso, actividades, calificaciones] = await Promise.all([
      pedir(`/alumno/cursos/${CURSO_ID}`, { conToken: true }),
      pedir(`/alumno/cursos/${CURSO_ID}/actividades`, { conToken: true }),
      pedir(`/alumno/cursos/${CURSO_ID}/calificaciones`, { conToken: true })
    ]);
    actividad = actividades.find(a => a.id === ACTIVIDAD_ID);
    if (!actividad) throw new ErrorApi(404, "La actividad no existe en este curso");
    document.getElementById("miga-curso").textContent = curso.nombreMateria;
    pintar(calificaciones.celdas.find(c => c.actividad_id === ACTIVIDAD_ID));
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  } finally {
    document.getElementById("entrega-cargando").classList.add("hidden");
  }
}

function pintar(celda) {
  const a = actividad;
  document.title = `${a.titulo} · SEPA CUCEI`;
  document.getElementById("miga-actividad").textContent = a.titulo;
  document.getElementById("act-categoria").textContent = `${a.categoria} · vale ${numero(a.valorEnCurso)} % del curso`;
  document.getElementById("act-titulo").textContent = a.titulo;
  document.getElementById("act-descripcion").textContent = a.descripcion || "Sin instrucciones adicionales.";
  const datos = document.getElementById("act-datos");
  datos.innerHTML = "";
  const dato = (nombreIcono, titulo, texto) => {
    const d = el("div", "p-space-sm rounded-lg bg-surface-container-low flex items-center gap-space-sm");
    const t = el("div");
    t.append(el("p", "font-caption text-caption uppercase tracking-wider text-on-surface-variant", titulo), el("p", "font-label-lg text-label-lg text-on-surface", texto));
    d.append(icono(nombreIcono, "text-[22px] text-secondary"), t);
    return d;
  };
  datos.append(dato("event", "Fecha límite", fechaHora(a.fechaHoraLimite)), dato("star", "Puntuación máxima", `${numero(a.puntuacionMaxima)} puntos`));
  const archivo = document.getElementById("act-archivo");
  archivo.classList.toggle("hidden", !a.tieneArchivo);
  archivo.classList.toggle("flex", a.tieneArchivo);

  const [texto, clases] = ESTADOS[a.estadoEntrega];
  const estado = document.getElementById("estado-entrega");
  estado.innerHTML = "";
  estado.appendChild(el("span", `inline-flex px-2.5 py-0.5 rounded-full font-label-md text-label-md ${clases}`, texto));

  const entregado = Boolean(a.entrega);
  document.getElementById("bloque-entregado").classList.toggle("hidden", !entregado);
  document.getElementById("form-entrega").classList.toggle("hidden", entregado);
  if (entregado) {
    document.getElementById("texto-entregado").textContent =
      `Entregaste el ${fechaHora(a.entrega.fechaHoraEntrega)}${a.entrega.entregadoConRetraso ? ", después de la fecha límite" : ""}.`;
    // RF-38: solo antes de la fecha límite y si aún no la califican
    const calificada = Boolean(celda?.calificacion);
    const cancelar = document.getElementById("btn-cancelar-entrega");
    cancelar.classList.toggle("hidden", !a.puedeCancelar || calificada);
    document.getElementById("texto-cancelar").textContent = calificada
      ? "Tu entrega ya fue calificada, así que no puedes cancelarla."
      : a.puedeCancelar ? `Puedes cancelarla y subir otra hasta el ${fechaHora(a.fechaHoraLimite)}.` : "La fecha límite ya pasó: tu entrega quedó fija.";
  } else {
    document.getElementById("aviso-tarde").classList.toggle("hidden", a.estadoEntrega !== "vencida");
    document.getElementById("aviso-tarde").classList.toggle("flex", a.estadoEntrega === "vencida");
  }

  const bloqueNota = document.getElementById("bloque-calificacion");
  const calif = celda?.calificacion;
  bloqueNota.classList.toggle("hidden", !calif && !celda?.cuentaComoCero);
  if (calif) {
    document.getElementById("texto-nota").textContent = `${numero(calif.calificacionObtenida)} / ${numero(a.puntuacionMaxima)}`;
    document.getElementById("texto-retro").textContent = calif.retroalimentacion ? `“${calif.retroalimentacion}”` : "Sin comentarios del profesor.";
  } else if (celda?.cuentaComoCero) {
    document.getElementById("texto-nota").textContent = `0 / ${numero(a.puntuacionMaxima)}`;
    document.getElementById("texto-retro").textContent = "Venció sin entrega: por ahora cuenta como 0. Si entregas tarde, tu profesor podrá calificarla.";
  }
  document.getElementById("entrega-contenido").classList.remove("hidden");
}

// ==================== SUBIR (RF-36, RF-37, RF-39) ====================

function archivoValido(archivo) {
  const extension = archivo.name.includes(".") ? archivo.name.slice(archivo.name.lastIndexOf(".")).toLowerCase() : "";
  if (!EXTENSIONES.includes(extension)) return "Tipo no permitido: solo PDF, Word, imágenes (PNG, JPG, GIF) o ZIP";
  if (archivo.size > LIMITE_BYTES) return "El archivo supera el tamaño máximo de 10 MB";
  if (!archivo.size) return "El archivo está vacío";
  return null;
}

function mostrarArchivoElegido() {
  limpiarErrores("aviso-entrega");
  const archivo = document.getElementById("input-archivo").files[0];
  document.getElementById("nombre-archivo").textContent = archivo
    ? `${archivo.name} (${numero(archivo.size / 1024 / 1024, 2)} MB)`
    : "Elige o arrastra tu archivo";
  if (archivo) {
    const problema = archivoValido(archivo);
    if (problema) marcarCampo("archivo", problema);
  }
}

function activarArrastrar() {
  const zona = document.getElementById("zona-archivo");
  const entrada = document.getElementById("input-archivo");
  ["dragenter", "dragover"].forEach(e => zona.addEventListener(e, ev => { ev.preventDefault(); zona.classList.add("ring-2", "ring-secondary"); }));
  ["dragleave", "drop"].forEach(e => zona.addEventListener(e, ev => { ev.preventDefault(); zona.classList.remove("ring-2", "ring-secondary"); }));
  zona.addEventListener("drop", ev => {
    if (!ev.dataTransfer.files.length) return;
    entrada.files = ev.dataTransfer.files;
    mostrarArchivoElegido();
  });
}

async function enviarEntrega(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-entrega");
  const archivo = document.getElementById("input-archivo").files[0];
  if (!archivo) return marcarCampo("archivo", "Elige el archivo que vas a entregar");
  const problema = archivoValido(archivo);
  if (problema) return marcarCampo("archivo", problema);

  const datos = new FormData();
  datos.append("archivo", archivo);
  const b = document.getElementById("btn-enviar");
  botonCargando(b, true);
  try {
    await pedir(`/alumno/actividades/${ACTIVIDAD_ID}/entrega`, { metodo: "POST", datos, conToken: true });
    document.getElementById("form-entrega").reset();
    mostrarArchivoElegido();
    await cargar();
    mostrarAviso("¡Entrega enviada!", "info", "aviso-entrega");
  } catch (error) {
    // 409 ya entregada o curso archivado · 413 / 415 / 422 archivo inválido
    if (error.status !== 401) mostrarErrorApi(error, "aviso-entrega");
  } finally {
    botonCargando(b, false);
  }
}

// ==================== CANCELAR (RF-38) ====================

async function cancelarEntrega() {
  if (!await confirmar("¿Cancelar tu entrega?", "Se borrará el archivo que subiste. Podrás subir otro antes de la fecha límite.", "Cancelar entrega")) return;
  try {
    await pedir(`/alumno/actividades/${ACTIVIDAD_ID}/entrega`, { metodo: "DELETE", conToken: true });
    await cargar();
    mostrarAviso("Entrega cancelada. Ya puedes subir otro archivo.", "info", "aviso-entrega");
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error, "aviso-entrega");
  }
}
