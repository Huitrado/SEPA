// ============================================================
// estudiante.js: panel principal del estudiante (estudiante.html).
//   RF-60  Solo los cursos del ciclo activo en los que está inscrito -> GET /alumno/cursos
//   RF-61  Cada tarjeta: materia, profesor y semáforo de riesgo general
//   RF-15  Unirse a un curso con su código                           -> POST /inscripcion
// ============================================================

document.addEventListener("DOMContentLoaded", iniciarEstudiante);

let cursos = [];
let filtroRiesgo = "todos";

async function iniciarEstudiante() {
  const perfil = await protegerPagina(["estudiante"]);
  if (!perfil) return;
  document.getElementById("saludo").textContent = `¡Hola, ${perfil.nombre}!`;
  activarModales();
  document.getElementById("btn-unirse").addEventListener("click", abrirUnirse);
  document.getElementById("form-unirse").addEventListener("submit", unirse);
  pedir("/catalogos/ciclo-actual")
    .then(c => { document.getElementById("texto-ciclo").textContent = `Ciclo ${c.nombreOficial}`; })
    .catch(() => {});
  cargarCursos();
}

async function cargarCursos() {
  const cargando = document.getElementById("cursos-cargando");
  cargando.classList.remove("hidden");
  try {
    cursos = await pedir("/alumno/cursos", { conToken: true });
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
    cursos = [];
  } finally {
    cargando.classList.add("hidden");
  }
  pintarFiltros();
  pintarCursos();
}

function pintarFiltros() {
  const contenedor = document.getElementById("filtros-riesgo");
  contenedor.innerHTML = "";
  if (!cursos.length) return;
  const cuenta = color => cursos.filter(c => c.semaforoGeneral === color).length;
  const opciones = [["todos", `Todos (${cursos.length})`], ["verde", `Verde (${cuenta("verde")})`],
    ["amarillo", `Amarillo (${cuenta("amarillo")})`], ["rojo", `Rojo (${cuenta("rojo")})`]];
  for (const [clave, texto] of opciones) {
    const b = el("button", `px-space-md py-1.5 rounded-lg font-label-md text-label-md transition-colors ${clave === filtroRiesgo ? "bg-primary-container text-on-primary" : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container"}`, texto);
    b.type = "button";
    b.addEventListener("click", () => {
      filtroRiesgo = clave;
      pintarFiltros();
      pintarCursos();
    });
    contenedor.appendChild(b);
  }
}

function pintarCursos() {
  const lista = document.getElementById("cursos-lista");
  const vacio = document.getElementById("cursos-vacio");
  lista.innerHTML = "";
  vacio.classList.toggle("hidden", cursos.length > 0);
  const visibles = cursos.filter(c => filtroRiesgo === "todos" || c.semaforoGeneral === filtroRiesgo);
  lista.classList.toggle("hidden", !cursos.length);
  visibles.forEach(c => lista.appendChild(tarjeta(c)));
}

// RF-61: materia, profesor y semáforo. Solo lo necesario para reconocer el curso y entrar;
// el horario, la asistencia, la calificación y las alertas se ven dentro del curso.
function tarjeta(c) {
  const enlace = el("a", "group bg-surface-container-lowest rounded-xl shadow-md overflow-hidden flex flex-col hover:shadow-lg transition-shadow");
  enlace.href = `curso-alumno.html?id=${c.id}`;
  const franja = el("div", `h-1.5 ${SEMAFORO[c.semaforoGeneral].punto}`);
  const cuerpo = el("div", "p-space-lg flex items-center justify-between gap-space-md flex-1");

  const titulos = el("div", "min-w-0");
  titulos.append(el("h2", "font-title-lg text-title-lg text-primary leading-snug group-hover:underline", c.nombreMateria),
    el("p", "font-body-md text-body-md text-on-surface-variant mt-1", c.profesor || "Sin profesor asignado"));
  const derecha = el("div", "shrink-0 flex items-center gap-space-sm");
  derecha.append(chipSemaforo(c.semaforoGeneral), icono("chevron_right", "text-[22px] text-on-surface-variant"));

  cuerpo.append(titulos, derecha);
  enlace.append(franja, cuerpo);
  return enlace;
}

// ==================== UNIRSE A UN CURSO (RF-15) ====================

function abrirUnirse() {
  document.getElementById("form-unirse").reset();
  limpiarErrores("aviso-unirse");
  abrirModal("modal-unirse");
  document.getElementById("input-codigo-curso").focus();
}

async function unirse(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-unirse");
  const codigoCurso = document.getElementById("input-codigo-curso").value.trim().toUpperCase();
  if (!codigoCurso) return marcarCampo("codigoCurso", "Escribe el código del curso");
  const b = document.getElementById("btn-confirmar-unirse");
  botonCargando(b, true);
  try {
    const r = await pedir("/inscripcion", { metodo: "POST", datos: { codigoCurso }, conToken: true });
    cerrarModal("modal-unirse");
    mostrarToast(`${r.mensaje}: ${r.curso}.`);
    await cargarCursos();
  } catch (error) {
    // 404 código inexistente · 409 curso archivado o ya inscrito
    if (error.status !== 401) mostrarErrorApi(error, "aviso-unirse");
  } finally {
    botonCargando(b, false);
  }
}
