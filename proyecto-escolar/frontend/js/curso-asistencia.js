// ============================================================
// curso-asistencia.js: pestaña "Asistencia" de curso.html.
//   RF-19, RF-27  Generar la sesión de hoy          -> POST .../sesiones
//   RF-26, RF-28  Cuadrícula alumnos × fechas con desplazamiento horizontal
//                                                     -> GET .../asistencia
//   RF-24         Indicador de lista pendiente en cada fecha
//   RF-20 a RF-23 Pasar lista y guardarla             -> GET .../sesiones/{id}
//   RF-25         Corregir una sesión pasada          -> PUT .../sesiones/{id}/lista
//   RF-21         Al abrir la lista, los pendientes aparecen como "Asistencia"
// Usa C, rutaCurso() y avisarError() de curso.js.
// ============================================================

const ESTADOS_ASISTENCIA = {
  asistencia: { letra: "A", texto: "Asistencia", clases: "bg-semaforo-verde-fondo text-semaforo-verde" },
  retardo: { letra: "R", texto: "Retardo", clases: "bg-semaforo-amarillo-fondo text-semaforo-amarillo" },
  falta: { letra: "F", texto: "Falta", clases: "bg-semaforo-rojo-fondo text-semaforo-rojo" },
  pendiente: { letra: "·", texto: "Lista sin guardar", clases: "bg-surface-container text-on-surface-variant" }
};

let sesionAbierta = null;       // detalle de la sesión en la ventana de lista
const listaEditada = new Map(); // matricula_id -> { estado, observaciones }

function iniciarAsistencia() {
  document.getElementById("btn-generar-sesion").addEventListener("click", generarSesion);
  document.getElementById("btn-guardar-lista").addEventListener("click", guardarLista);
  document.getElementById("btn-todos-asistencia").addEventListener("click", () => {
    for (const registro of listaEditada.values()) registro.estado = "asistencia";
    pintarListaAlumnos();
  });
  pintarLeyenda();
}

function pintarLeyenda() {
  const leyenda = document.getElementById("leyenda-asistencia");
  for (const e of Object.values(ESTADOS_ASISTENCIA)) {
    const item = el("span", "inline-flex items-center gap-1.5");
    item.append(el("span", `w-6 h-6 rounded-md flex items-center justify-center font-label-md text-label-md ${e.clases}`, e.letra), el("span", "", e.texto));
    leyenda.appendChild(item);
  }
  const pendiente = el("span", "inline-flex items-center gap-1.5");
  pendiente.append(icono("pending", "text-[18px] text-on-tertiary-container"), el("span", "", "Fecha con lista pendiente"));
  leyenda.appendChild(pendiente);
}

async function cargarAsistencia() {
  try {
    C.asistencia = await pedir(rutaCurso("/asistencia"), { conToken: true });
  } catch (error) {
    avisarError(error);
  }
  pintarCuadricula();
}

// ==================== CUADRÍCULA (RF-24, RF-26, RF-28) ====================

function pintarCuadricula() {
  const tabla = document.getElementById("tabla-asistencia");
  const vacia = document.getElementById("asistencia-vacia");
  tabla.innerHTML = "";
  const datos = C.asistencia;
  if (!datos) return;

  if (!datos.sesiones.length || !datos.alumnos.length) {
    vacia.textContent = !datos.alumnos.length
      ? "No hay alumnos activos en el curso todavía."
      : "Aún no hay sesiones. En un día de clase, usa \"Generar sesión de hoy\" para pasar lista.";
    vacia.classList.remove("hidden");
    if (!datos.alumnos.length) return;
  } else {
    vacia.classList.add("hidden");
  }

  // Columnas fijas a la izquierda: alumno y porcentaje
  const fijaAlumno = "sticky left-0 z-10 bg-surface-container-lowest min-w-[150px] max-w-[150px] sm:min-w-[220px] sm:max-w-[220px]";
  const fijaPorcentaje = "sticky left-[150px] sm:left-[220px] z-10 bg-surface-container-lowest min-w-[120px] shadow-[4px_0_6px_-4px_rgba(0,0,0,0.12)]";

  const thead = el("thead");
  const encabezado = el("tr", "font-label-md text-label-md text-on-surface-variant uppercase tracking-wider");
  encabezado.append(
    el("th", `${fijaAlumno} !bg-surface-container py-3 px-space-md`, "Alumno"),
    el("th", `${fijaPorcentaje} !bg-surface-container py-3 px-space-md`, "Asistencia")
  );
  for (const s of datos.sesiones) {
    const th = el("th", "bg-surface-container py-2 px-1 text-center min-w-[64px]");
    const b = el("button", `w-full flex flex-col items-center gap-0.5 px-1 py-1 rounded-md hover:bg-surface-container-high transition-colors ${s.listaGuardada ? "text-on-surface-variant" : "text-on-tertiary-container"}`);
    b.type = "button";
    b.title = `${s.listaGuardada ? "Corregir la lista" : "Pasar lista"} del ${fechaCorta(s.fecha)}${s.tema ? ` · ${s.tema}` : ""}`;
    b.append(el("span", "normal-case whitespace-nowrap", fechaCorta(s.fecha)));
    b.appendChild(icono(s.listaGuardada ? "check_circle" : "pending", "text-[16px]"));
    b.addEventListener("click", () => abrirLista(s.id));
    th.appendChild(b);
    encabezado.appendChild(th);
  }
  thead.appendChild(encabezado);

  const tbody = el("tbody", "font-body-md text-body-md");
  for (const a of datos.alumnos) {
    const fila = el("tr", "hover:bg-surface-container-low");
    const celdaNombre = el("td", `${fijaAlumno} py-space-sm px-space-md border-t border-surface-container`);
    celdaNombre.append(
      el("p", "font-label-lg text-label-lg text-primary truncate", `${a.apellidos} ${a.nombre}`),
      el("p", "font-helper-sm text-helper-sm text-on-surface-variant font-mono", a.codigoEstudiante)
    );
    const celdaPorcentaje = el("td", `${fijaPorcentaje} py-space-sm px-space-md border-t border-surface-container`);
    celdaPorcentaje.append(chipSemaforo(a.semaforo, `${numero(a.porcentajeAsistencia, 1)} %`),
      el("p", "font-helper-sm text-helper-sm text-on-surface-variant mt-1", a.estatusNormativo));
    fila.append(celdaNombre, celdaPorcentaje);

    a.estados.forEach(registro => {
      const td = el("td", "py-space-sm px-1 text-center border-t border-surface-container");
      const e = ESTADOS_ASISTENCIA[registro.estado];
      if (e) {
        const marca = el("span", `inline-flex w-8 h-8 rounded-md items-center justify-center font-label-lg text-label-lg ${e.clases}`, e.letra);
        marca.title = e.texto + (registro.observaciones ? ` · ${registro.observaciones}` : "");
        td.appendChild(marca);
      } else {
        const sin = el("span", "text-outline", "—");
        sin.title = "Aún no estaba inscrito en esta fecha";
        td.appendChild(sin);
      }
      fila.appendChild(td);
    });
    tbody.appendChild(fila);
  }
  tabla.append(thead, tbody);

  // Mostrar primero las fechas más recientes (RF-28: se desplaza hacia atrás)
  const contenedor = document.getElementById("contenedor-asistencia");
  contenedor.scrollLeft = contenedor.scrollWidth;
}

// ==================== GENERAR SESIÓN (RF-19, RF-27) ====================

async function generarSesion() {
  const b = document.getElementById("btn-generar-sesion");
  const tema = document.getElementById("input-tema").value.trim();
  ocultarAviso();
  botonCargando(b, true);
  try {
    const sesion = await pedir(rutaCurso("/sesiones"), { metodo: "POST", datos: tema ? { tema } : undefined, conToken: true });
    document.getElementById("input-tema").value = "";
    await cargarAsistencia();
    mostrarLista(sesion);
  } catch (error) {
    // 409: hoy no hay clase, ya existe la sesión, curso archivado o ciclo no vigente
    avisarError(error);
    window.scrollTo({ top: 0, behavior: "smooth" });
  } finally {
    botonCargando(b, false);
  }
}

// Botón "Pasar lista" de la ficha: abre directo la lista de hoy (la crea si aún no existe).
// Si hoy no hay clase, se queda en la pestaña Asistencia con el motivo.
async function pasarListaHoy() {
  mostrarPestana("asistencia");
  const b = document.getElementById("btn-pasar-lista");
  b.disabled = true;
  try {
    if (!C.asistencia) await cargarAsistencia();
    const d = new Date();
    const hoy = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const deHoy = C.asistencia?.sesiones.find(s => s.fecha === hoy);
    if (deHoy) {
      await abrirLista(deHoy.id);
    } else {
      mostrarLista(await pedir(rutaCurso("/sesiones"), { metodo: "POST", conToken: true }));
      cargarAsistencia();
    }
  } catch (error) {
    // 409: hoy no hay clase, curso archivado o ciclo no vigente
    avisarError(error);
    window.scrollTo({ top: 0, behavior: "smooth" });  // el aviso está arriba
  } finally {
    b.disabled = false;
  }
}

// ==================== PASAR O CORREGIR LISTA (RF-20 a RF-25) ====================

async function abrirLista(sesionId) {
  try {
    mostrarLista(await pedir(rutaCurso(`/sesiones/${sesionId}`), { conToken: true }));
  } catch (error) {
    avisarError(error);
  }
}

function mostrarLista(sesion) {
  sesionAbierta = sesion;
  listaEditada.clear();
  for (const a of sesion.alumnos) {
    // RF-21: lo que aún no se guarda se muestra como "Asistencia", listo para cambiarse
    listaEditada.set(a.matricula_id, {
      estado: a.estado === "pendiente" ? "asistencia" : a.estado,
      observaciones: a.observaciones || ""
    });
  }
  limpiarErrores("aviso-lista");
  document.getElementById("lista-estado").textContent = sesion.listaGuardada ? "Lista guardada · puedes corregirla" : "Lista pendiente de guardar";
  document.getElementById("lista-titulo").textContent = `Sesión del ${fechaCorta(sesion.fecha)} · ${sesion.horaInicio} – ${sesion.horaFin}`;
  document.getElementById("lista-tema").textContent = sesion.tema ? `Tema: ${sesion.tema}` : "";
  pintarListaAlumnos();
  abrirModal("modal-lista");
}

function pintarListaAlumnos() {
  const contenedor = document.getElementById("lista-alumnos");
  contenedor.innerHTML = "";
  if (!sesionAbierta.alumnos.length) {
    contenedor.appendChild(el("p", "text-on-surface-variant py-space-md", "No hay alumnos activos en el curso."));
    return;
  }
  for (const a of sesionAbierta.alumnos) {
    const registro = listaEditada.get(a.matricula_id);
    const fila = el("div", "py-space-sm grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-space-sm items-center");
    const nombre = el("div", "min-w-0");
    nombre.append(el("p", "font-label-lg text-label-lg text-primary truncate", `${a.apellidos} ${a.nombre}`),
      el("p", "font-helper-sm text-helper-sm text-on-surface-variant font-mono", a.codigoEstudiante));

    const controles = el("div", "flex items-center gap-space-sm");
    const grupo = el("div", "inline-flex p-0.5 rounded-lg bg-surface-container-low");
    grupo.setAttribute("role", "radiogroup");
    grupo.setAttribute("aria-label", `Asistencia de ${a.nombre}`);
    for (const clave of ["asistencia", "retardo", "falta"]) {
      const e = ESTADOS_ASISTENCIA[clave];
      const elegido = registro.estado === clave;
      const b = el("button", `w-9 h-8 rounded-md font-label-lg text-label-lg transition-colors ${elegido ? e.clases + " shadow-sm" : "text-on-surface-variant hover:bg-surface-container"}`, e.letra);
      b.type = "button";
      b.title = e.texto;
      b.setAttribute("role", "radio");
      b.setAttribute("aria-checked", String(elegido));
      b.addEventListener("click", () => {
        registro.estado = clave;
        pintarListaAlumnos();
      });
      grupo.appendChild(b);
    }
    const nota = el("input", "w-40 bg-surface-container-low text-on-surface px-2.5 py-1.5 rounded-lg font-helper-sm text-helper-sm placeholder:text-outline focus:outline-none");
    nota.type = "text";
    nota.maxLength = 500;
    nota.placeholder = "Observaciones";
    nota.value = registro.observaciones;
    nota.addEventListener("input", () => { registro.observaciones = nota.value; });
    controles.append(grupo, nota);
    fila.append(nombre, controles);
    contenedor.appendChild(fila);
  }
}

// RF-23: solo cuenta cuando se guarda explícitamente
async function guardarLista() {
  const b = document.getElementById("btn-guardar-lista");
  limpiarErrores("aviso-lista");
  const asistencias = [...listaEditada.entries()].map(([matricula_id, r]) => ({
    matricula_id,
    estado: r.estado,
    observaciones: r.observaciones.trim() || null
  }));
  botonCargando(b, true);
  try {
    await pedir(rutaCurso(`/sesiones/${sesionAbierta.id}/lista`), { metodo: "PUT", datos: { asistencias }, conToken: true });
    cerrarModal("modal-lista");
    mostrarToast("Lista guardada");
    await Promise.all([cargarAsistencia(), cargarMatricula()]);
    pintarMetricas();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error, "aviso-lista");
  } finally {
    botonCargando(b, false);
  }
}
