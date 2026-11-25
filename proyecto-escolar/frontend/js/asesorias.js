// ============================================================
// asesorias.js: tablero de asesorías para el estudiante (asesorias.html).
//   RF-78  Cartelera de tarjetas con las asesorías disponibles -> GET /asesorias
//   RF-79  Filtros por materia, modalidad, tópico u horario (en el navegador)
//   RF-80  Detalle con el lugar o el enlace para presentarse o conectarse
//   RF-72  Llega desde el panel del curso con ?materia=... ya filtrado
//   RF-92  Si el alumno también es asesor, ve el acceso a sus publicaciones
// ============================================================

document.addEventListener("DOMContentLoaded", iniciarAsesorias);

let publicaciones = [];
let modalidad = "";

async function iniciarAsesorias() {
  const perfil = await protegerPagina(["estudiante"]);
  if (!perfil) return;
  activarModales();
  if (perfil.roles.includes("asesor")) {
    const enlace = document.getElementById("link-mis-asesorias");
    enlace.classList.remove("hidden");
    enlace.classList.add("inline-flex");
  } else {
    document.getElementById("form-solicitud").addEventListener("submit", enviarSolicitud);
    cargarSolicitud();
  }
  document.getElementById("filtro-materia").addEventListener("change", pintar);
  document.getElementById("filtro-texto").addEventListener("input", pintar);
  pintarModalidades();
  try {
    publicaciones = await pedir("/asesorias", { conToken: true });
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  }
  document.getElementById("cargando").classList.add("hidden");
  llenarMaterias(new URLSearchParams(location.search).get("materia"));
  pintar();
}

// ---------- Solicitud para ser asesor (solo quien aún no lo es) ----------
// Sin solicitud o rechazada: botón "Quiero ser asesor" · pendiente: aviso "en revisión".
let solicitud = null;

async function cargarSolicitud() {
  try {
    solicitud = await pedir("/asesorias/solicitud", { conToken: true });
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
    return;
  }
  pintarSolicitud();
}

function pintarSolicitud() {
  const zona = document.getElementById("zona-solicitud");
  zona.innerHTML = "";
  zona.classList.remove("hidden");
  zona.classList.add("flex");
  if (solicitud?.estado === "pendiente") {
    const chip = el("span", "inline-flex items-center gap-space-xs py-2.5 px-space-lg rounded-lg bg-surface-container-low text-on-surface-variant font-label-lg text-label-lg");
    chip.append(icono("hourglass_top", "text-[20px]"), el("span", "", "Solicitud de asesor en revisión"));
    zona.appendChild(chip);
    return;
  }
  const b = boton("Quiero ser asesor", "volunteer_activism", "suave");
  b.addEventListener("click", abrirSolicitud);
  zona.appendChild(b);
  if (solicitud?.estado === "rechazada") {
    zona.appendChild(el("span", "font-helper-sm text-helper-sm text-on-surface-variant", "Tu solicitud anterior no fue aceptada."));
  }
}

function abrirSolicitud() {
  document.getElementById("form-solicitud").reset();
  limpiarErrores("aviso-solicitud");
  const rechazo = document.getElementById("solicitud-rechazo");
  const comentario = solicitud?.estado === "rechazada" ? solicitud.comentarioAdmin : null;
  rechazo.textContent = comentario ? `Respuesta a tu solicitud anterior: "${comentario}"` : "";
  rechazo.classList.toggle("hidden", !comentario);
  abrirModal("modal-solicitud");
  document.getElementById("input-motivo").focus();
}

async function enviarSolicitud(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-solicitud");
  const motivo = document.getElementById("input-motivo").value.trim();
  const materias = document.getElementById("input-materias").value.trim() || null;
  if (!motivo) return marcarCampo("motivo", "Cuéntanos por qué quieres ser asesor");
  if (motivo.length < 20) return marcarCampo("motivo", "Debe tener al menos 20 caracteres");
  const b = document.getElementById("btn-enviar-solicitud");
  botonCargando(b, true);
  try {
    solicitud = await pedir("/asesorias/solicitud", { metodo: "POST", datos: { motivo, materias }, conToken: true });
    cerrarModal("modal-solicitud");
    mostrarToast("Solicitud enviada. Te avisaremos aquí cuando la revisen.");
    pintarSolicitud();
  } catch (error) {
    // 409: ya tiene una pendiente o ya es asesor
    if (error.status !== 401) mostrarErrorApi(error, "aviso-solicitud");
  } finally {
    botonCargando(b, false);
  }
}

function pintarModalidades() {
  const contenedor = document.getElementById("filtro-modalidad");
  contenedor.innerHTML = "";
  for (const [valor, texto] of [["", "Todas"], ["presencial", "Presencial"], ["virtual", "Virtual"]]) {
    const b = el("button", `flex-1 py-1.5 rounded-md font-label-md text-label-md transition-colors ${valor === modalidad ? "bg-surface-container-lowest text-primary shadow-sm" : "text-on-surface-variant hover:text-on-surface"}`, texto);
    b.type = "button";
    b.addEventListener("click", () => {
      modalidad = valor;
      pintarModalidades();
      pintar();
    });
    contenedor.appendChild(b);
  }
}

// Las materias del filtro son las que tienen asesorías publicadas (más la que llegó por la URL)
function llenarMaterias(elegida) {
  const select = document.getElementById("filtro-materia");
  const nombres = [...new Set(publicaciones.map(p => p.materia))];
  const coincide = elegida && nombres.find(n => n.toLowerCase() === elegida.toLowerCase());
  if (elegida && !coincide) nombres.push(elegida);
  nombres.sort((a, b) => a.localeCompare(b, "es"));
  for (const n of nombres) select.appendChild(new Option(n, n));
  if (elegida) select.value = coincide || elegida;
}

function pintar() {
  const materia = document.getElementById("filtro-materia").value.toLowerCase();
  const texto = document.getElementById("filtro-texto").value.trim().toLowerCase();
  const visibles = publicaciones.filter(p =>
    (!materia || p.materia.toLowerCase() === materia) && (!modalidad || p.modalidad === modalidad) &&
    (!texto || `${p.topico || ""} ${p.horario} ${p.lugarOMedio} ${p.asesor}`.toLowerCase().includes(texto)));
  const contenedor = document.getElementById("tarjetas");
  contenedor.innerHTML = "";
  visibles.forEach(p => contenedor.appendChild(tarjeta(p)));
  document.getElementById("vacio").classList.toggle("hidden", visibles.length > 0);
  document.getElementById("contador").textContent = `${visibles.length} de ${publicaciones.length} asesoría${publicaciones.length === 1 ? "" : "s"} disponible${publicaciones.length === 1 ? "" : "s"}`;
}

function etiquetaModalidad(p) {
  const virtual = p.modalidad === "virtual";
  const chip = el("span", `inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-label-md text-label-md ${virtual ? "bg-surface-container-high text-on-secondary-container" : "bg-tertiary-fixed text-on-tertiary-fixed-variant"}`);
  chip.append(icono(virtual ? "videocam" : "location_on", "text-[14px]"), el("span", "", virtual ? "Virtual" : "Presencial"));
  return chip;
}

// RF-78
function tarjeta(p) {
  const t = el("article", "bg-surface-container-lowest rounded-xl shadow-md p-space-lg flex flex-col gap-space-md");
  const cabeza = el("div", "flex items-start justify-between gap-space-sm");
  cabeza.append(el("h2", "font-title-lg text-title-lg text-primary leading-snug", p.materia), etiquetaModalidad(p));
  t.appendChild(cabeza);
  if (p.topico) t.appendChild(el("p", "font-body-md text-body-md text-on-surface line-clamp-3", p.topico));
  const datos = el("div", "space-y-1.5 font-body-md text-body-md text-on-surface-variant");
  const fila = (nombreIcono, texto) => {
    const f = el("p", "flex items-start gap-space-sm");
    f.append(icono(nombreIcono, "text-[18px] mt-0.5"), el("span", "", texto));
    return f;
  };
  datos.append(fila("schedule", p.horario), fila("person", `${p.asesor}${p.carreraAsesor ? ` · ${p.carreraAsesor}` : ""}`));
  t.appendChild(datos);
  const ver = boton("Ver detalles", "info", "secundario");
  ver.classList.add("mt-auto");
  ver.addEventListener("click", () => mostrarDetalle(p));
  t.appendChild(ver);
  return t;
}

// RF-80: todos los datos y el lugar o enlace exacto
function mostrarDetalle(p) {
  document.getElementById("detalle-materia").textContent = p.materia;
  document.getElementById("detalle-modalidad").textContent = p.modalidad === "virtual" ? "Asesoría virtual" : "Asesoría presencial";
  const cuerpo = document.getElementById("detalle-cuerpo");
  cuerpo.innerHTML = "";
  const bloque = (nombreIcono, titulo, contenido) => {
    const b = el("div", "p-space-md rounded-xl bg-surface-container-low flex items-start gap-space-sm");
    const textos = el("div", "min-w-0");
    textos.appendChild(el("p", "font-caption text-caption uppercase tracking-wider text-on-surface-variant", titulo));
    textos.appendChild(typeof contenido === "string" ? el("p", "font-body-md text-body-md text-on-surface whitespace-pre-line break-words", contenido) : contenido);
    b.append(icono(nombreIcono, "text-[22px] text-secondary"), textos);
    return b;
  };
  if (p.topico) cuerpo.appendChild(bloque("topic", "Temas", p.topico));
  cuerpo.appendChild(bloque("schedule", "Horario", p.horario));
  // El enlace solo se vuelve clic si es una dirección web (http o https)
  let lugar = p.lugarOMedio;
  if (/^https?:\/\/\S+$/i.test(p.lugarOMedio)) {
    lugar = el("a", "font-body-md text-body-md text-secondary underline break-all", p.lugarOMedio);
    lugar.href = p.lugarOMedio;
    lugar.target = "_blank";
    lugar.rel = "noopener noreferrer";
  }
  cuerpo.appendChild(bloque(p.modalidad === "virtual" ? "videocam" : "location_on", p.modalidad === "virtual" ? "Enlace o medio" : "Lugar", lugar));
  const contacto = el("p", "font-body-md text-body-md text-on-surface", "");
  contacto.append(el("span", "", `${p.asesor} · `));
  const correo = el("a", "text-secondary underline", p.correoAsesor);
  correo.href = `mailto:${p.correoAsesor}`;
  contacto.appendChild(correo);
  cuerpo.appendChild(bloque("person", "Asesor", contacto));
  cuerpo.appendChild(el("p", "font-helper-sm text-helper-sm text-on-surface-variant", "No necesitas inscribirte: preséntate o conéctate en el horario indicado."));
  abrirModal("modal-detalle");
}
