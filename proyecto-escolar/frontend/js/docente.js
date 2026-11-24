// ============================================================
// docente.js: dashboard del docente (docente.html).
//   RF-11  cursos activos por defecto y pestaña "Archivados"  -> GET /docente/cursos?estado=
//   RF-14  código de cada curso visible y con botón de copiar
//   Crear curso                                               -> POST /cursos
//     RF-12 materia (del catálogo GET /catalogos/materias), sección y descripción
//     RF-09 ciclo obligatorio, de GET /catalogos/ciclos
//     RF-13 días y horario de inicio y fin
//     RF-17 solo dos tipos de evaluación
//     RF-18 "Mínimo aprobatorio: 60" como texto fijo, no como campo
// La sesión, el rol y el logout los resuelve protegerPagina() de app.js.
// ============================================================

document.addEventListener("DOMContentLoaded", iniciarDocente);

// DIAS, ETIQUETA_EVALUACION, el(), icono() y copiarCodigo() vienen de app.js.

let estadoActual = "activo";
let ciclos = [];          // todos los ciclos, para mostrar su nombre en las tarjetas
let materias = [];        // catálogo de materias (RF-12)

async function iniciarDocente() {
  const perfil = await protegerPagina(["docente"]);
  if (!perfil) return;

  document.getElementById("tab-activo").addEventListener("click", () => cambiarPestana("activo"));
  document.getElementById("tab-archivado").addEventListener("click", () => cambiarPestana("archivado"));
  document.getElementById("btn-crear-curso").addEventListener("click", abrirCrearCurso);
  document.getElementById("form-curso").addEventListener("submit", enviarCurso);
  document.getElementById("input-descripcion").addEventListener("input", actualizarContador);
  document.querySelectorAll('input[name="tipoEvaluacion"]').forEach(r =>
    r.addEventListener("change", actualizarTextoMinimo));
  document.querySelectorAll("[data-cerrar-modal]").forEach(boton =>
    boton.addEventListener("click", () => document.getElementById(boton.dataset.cerrarModal).classList.add("hidden")));
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") document.querySelectorAll("#modal-crear-curso, #modal-curso-creado")
      .forEach(m => m.classList.add("hidden"));
  });
  document.getElementById("btn-copiar-creado").addEventListener("click", e => copiarCodigo(e.currentTarget));

  pintarDias();
  pintarPestanas();
  await cargarCiclos();   // antes de los cursos, para mostrar el nombre del ciclo
  cargarCursos();
  cargarMaterias();
}

// ==================== LISTA DE CURSOS (RF-11) ====================

function cambiarPestana(estado) {
  if (estado === estadoActual) return;
  estadoActual = estado;
  pintarPestanas();
  cargarCursos();
}

function pintarPestanas() {
  const base = "flex items-center gap-space-xs py-2 px-space-md rounded-lg font-label-lg text-label-lg transition-all";
  const activa = `${base} bg-surface-container-lowest text-primary shadow-sm`;
  const inactiva = `${base} text-on-surface-variant hover:text-on-surface`;
  const pestanas = { activo: ["Activos", "menu_book"], archivado: ["Archivados", "inventory_2"] };
  for (const [estado, [texto, icono]] of Object.entries(pestanas)) {
    const boton = document.getElementById("tab-" + estado);
    boton.className = estado === estadoActual ? activa : inactiva;
    boton.setAttribute("aria-selected", String(estado === estadoActual));
    boton.innerHTML = `<span class="material-symbols-outlined text-[18px]">${icono}</span><span>${texto}</span>`;
  }
}

async function cargarCursos() {
  const cargando = document.getElementById("cursos-cargando");
  const lista = document.getElementById("cursos-lista");
  const vacio = document.getElementById("cursos-vacio");
  cargando.classList.remove("hidden");
  lista.classList.add("hidden");
  vacio.classList.add("hidden");
  ocultarAviso();

  const pedido = estadoActual;
  try {
    const cursos = await pedir(`/docente/cursos?estado=${pedido}`, { conToken: true });
    if (pedido !== estadoActual) return; // el usuario ya cambió de pestaña
    pintarCursos(cursos);
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  } finally {
    if (pedido === estadoActual) cargando.classList.add("hidden");
  }
}

function pintarCursos(cursos) {
  const lista = document.getElementById("cursos-lista");
  const vacio = document.getElementById("cursos-vacio");
  lista.innerHTML = "";

  if (!cursos.length) {
    const archivados = estadoActual === "archivado";
    document.getElementById("vacio-icono").textContent = archivados ? "inventory_2" : "menu_book";
    document.getElementById("vacio-titulo").textContent = archivados ? "No tienes cursos archivados" : "Aún no tienes cursos activos";
    document.getElementById("vacio-texto").textContent = archivados
      ? "Cuando archives un curso aparecerá aquí, con sus datos intactos."
      : "Crea tu primer curso y comparte su código con tus alumnos para que se inscriban.";
    vacio.classList.remove("hidden");
    return;
  }
  cursos.forEach(curso => lista.appendChild(tarjetaCurso(curso)));
  lista.classList.remove("hidden");
}

function tarjetaCurso(curso) {
  const archivado = curso.estado === "archivado";
  const tarjeta = el("article", "bg-surface-container-lowest rounded-xl shadow-md p-space-lg flex flex-col gap-space-md" +
    (archivado ? " opacity-90" : ""));

  // Encabezado: materia, sección y ciclo
  const cabeza = el("div", "flex items-start justify-between gap-space-sm");
  const titulos = el("div", "min-w-0");
  titulos.appendChild(el("h2", "font-title-lg text-title-lg text-primary leading-snug", curso.nombreMateria));
  const ciclo = ciclos.find(c => c.id === curso.cicloEscolar_id);
  titulos.appendChild(el("p", "font-body-md text-body-md text-on-surface-variant mt-0.5",
    `Sección ${curso.seccion}${ciclo ? " · Ciclo " + ciclo.nombreOficial : ""}`));
  cabeza.appendChild(titulos);
  if (archivado) {
    cabeza.appendChild(el("span", "shrink-0 font-label-md text-label-md px-2.5 py-0.5 rounded-full bg-surface-container text-on-surface-variant", "Archivado"));
  }
  tarjeta.appendChild(cabeza);

  // El horario, el tipo de evaluación y el código de inscripción (RF-14) se ven dentro del curso.
  // Detalle del curso: matrícula, asistencia, actividades, encuadre y calificaciones
  const abrir = el("a", "mt-auto inline-flex items-center justify-center gap-space-xs py-2.5 px-space-md rounded-lg font-label-lg text-label-lg bg-primary-container text-on-primary hover:bg-primary transition-colors");
  abrir.href = `curso.html?id=${curso.id}`;
  abrir.append(el("span", "", "Abrir curso"), icono("arrow_forward"));
  tarjeta.appendChild(abrir);

  return tarjeta;
}

// ==================== CATÁLOGOS ====================

async function cargarCiclos() {
  try {
    ciclos = await pedir("/catalogos/ciclos");
  } catch (error) {
    ciclos = [];
    mostrarErrorApi(error);
  }
}

// RF-12: la materia sale del plan de estudios. Si el catálogo no responde,
// se puede escribir a mano y el backend la acepta como texto.
async function cargarMaterias() {
  try {
    materias = await pedir("/catalogos/materias");
  } catch {
    materias = [];
  }
  const lista = document.getElementById("lista-materias");
  lista.innerHTML = "";
  for (const m of materias) {
    const opcion = el("option");
    opcion.value = m.nombre;
    opcion.label = m.clave;
    lista.appendChild(opcion);
  }
}

function llenarSelectCiclos() {
  const select = document.getElementById("select-ciclo");
  // RF-09: solo se crean cursos en ciclos que no han terminado
  const disponibles = ciclos.filter(c => c.estado !== "cerrado");
  select.innerHTML = "";
  if (!disponibles.length) {
    select.appendChild(new Option("No hay ciclos disponibles; pide a un administrador que registre uno", ""));
    return;
  }
  select.appendChild(new Option("Selecciona el ciclo escolar...", ""));
  const etiqueta = { activo: "en curso", proximo: "próximo" };
  for (const c of disponibles) {
    select.appendChild(new Option(`${c.nombreOficial} (${etiqueta[c.estado] || c.estado})`, c.id));
  }
  const enCurso = disponibles.find(c => c.estado === "activo");
  if (enCurso) select.value = String(enCurso.id);
}

function pintarDias() {
  const contenedor = document.getElementById("dias-semana");
  for (const [valor, , largo] of DIAS) {
    const opcion = el("label", "cursor-pointer");
    const casilla = el("input", "peer sr-only");
    casilla.type = "checkbox";
    casilla.name = "diasSemana";
    casilla.value = valor;
    const chip = el("span", "inline-flex items-center px-space-md py-space-sm rounded-full font-label-lg text-label-lg bg-surface-container-low text-on-surface-variant transition-colors peer-checked:bg-secondary peer-checked:text-on-secondary peer-focus-visible:ring-2 peer-focus-visible:ring-secondary", largo);
    opcion.append(casilla, chip);
    contenedor.appendChild(opcion);
  }
}

// ==================== CREAR CURSO ====================

function abrirCrearCurso() {
  const form = document.getElementById("form-curso");
  form.reset();
  limpiarErrores("aviso-curso");
  llenarSelectCiclos();
  actualizarContador();
  actualizarTextoMinimo();
  document.getElementById("modal-crear-curso").classList.remove("hidden");
  document.getElementById("input-materia").focus();
}

function actualizarContador() {
  const largo = document.getElementById("input-descripcion").value.length;
  document.getElementById("contador-descripcion").textContent = `${largo} / 500`;
}

// RF-18: el mínimo es fijo; solo se informa cuando la evaluación es numérica.
function actualizarTextoMinimo() {
  const tipo = document.querySelector('input[name="tipoEvaluacion"]:checked')?.value;
  document.getElementById("texto-minimo").classList.toggle("hidden", tipo !== "numerica");
}

// Junta los datos con los nombres de campo que espera el backend (schemas.CursoCrear).
function leerFormularioCurso() {
  const valor = id => document.getElementById(id).value.trim();
  return {
    nombreMateria: valor("input-materia"),
    seccion: valor("input-seccion").toUpperCase(),
    descripcion: valor("input-descripcion"),
    cicloEscolar_id: Number(valor("select-ciclo")) || null,
    tipoEvaluacion: document.querySelector('input[name="tipoEvaluacion"]:checked')?.value,
    diasSemana: [...document.querySelectorAll('input[name="diasSemana"]:checked')].map(c => c.value),
    horaInicio: valor("input-hora-inicio"),
    horaFin: valor("input-hora-fin")
  };
}

// Revisión rápida en el navegador; el backend vuelve a revisar todo.
function validarCurso(datos) {
  const errores = [];
  const obligatorio = "Este campo es obligatorio";
  if (!datos.nombreMateria) {
    errores.push({ campo: "nombreMateria", mensaje: obligatorio });
  } else if (materias.length && !materias.some(m => m.nombre === datos.nombreMateria)) {
    errores.push({ campo: "nombreMateria", mensaje: "Elige una materia de la lista del plan de estudios" });
  }
  if (!datos.seccion) errores.push({ campo: "seccion", mensaje: obligatorio });
  if (!datos.descripcion) errores.push({ campo: "descripcion", mensaje: obligatorio });
  if (!datos.cicloEscolar_id) errores.push({ campo: "cicloEscolar_id", mensaje: "Selecciona el ciclo escolar" });
  if (!datos.diasSemana.length) errores.push({ campo: "diasSemana", mensaje: "Selecciona al menos un día" });
  if (!datos.horaInicio) errores.push({ campo: "horaInicio", mensaje: obligatorio });
  if (!datos.horaFin) errores.push({ campo: "horaFin", mensaje: obligatorio });
  if (datos.horaInicio && datos.horaFin && datos.horaFin <= datos.horaInicio) {
    errores.push({ campo: "horaFin", mensaje: "Debe ser posterior a la hora de inicio" });
  }
  if (!datos.tipoEvaluacion) errores.push({ campo: "tipoEvaluacion", mensaje: "Elige el tipo de evaluación" });
  return errores;
}

async function enviarCurso(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-curso");

  const datos = leerFormularioCurso();
  const errores = validarCurso(datos);
  if (errores.length) {
    errores.forEach(e => marcarCampo(e.campo, e.mensaje));
    mostrarAviso("Revisa los campos marcados en rojo.", "error", "aviso-curso");
    return;
  }

  const boton = document.getElementById("btn-guardar-curso");
  botonCargando(boton, true);
  try {
    const curso = await pedir("/cursos", { metodo: "POST", datos, conToken: true });
    document.getElementById("modal-crear-curso").classList.add("hidden");
    mostrarCursoCreado(curso);
    if (estadoActual !== "activo") {
      estadoActual = "activo";
      pintarPestanas();
    }
    cargarCursos();
  } catch (error) {
    // 404 ciclo inexistente · 409 ciclo cerrado o curso repetido · 422 datos inválidos
    if (error.status !== 401) mostrarErrorApi(error, "aviso-curso");
  } finally {
    botonCargando(boton, false);
  }
}

function mostrarCursoCreado(curso) {
  document.getElementById("creado-titulo").textContent = `${curso.nombreMateria} · ${curso.seccion}`;
  document.getElementById("creado-codigo").textContent = curso.codigoCurso;
  document.getElementById("btn-copiar-creado").dataset.copiar = curso.codigoCurso;
  document.getElementById("modal-curso-creado").classList.remove("hidden");
}
