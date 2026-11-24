// ============================================================
// admin-catalogos.js: secciones "Ciclos escolares" y "Carreras y materias" de admin.html.
//   RF-08  Ciclos: solo el nombre (AAAA-A o AAAA-B); las fechas salen del calendario oficial
//          -> GET /catalogos/ciclos, POST /admin/ciclos
//   RF-02  Carreras del catálogo oficial  -> GET /catalogos/carreras, POST /admin/carreras
//   RF-94  Materias                       -> GET /catalogos/materias, POST/PATCH/DELETE /admin/materias
// Comparte con admin.js la variable "carreras".
// ============================================================

// Mismo calendario que config.py -> CALENDARIO_CICLOS (solo para mostrar las fechas antes de guardar)
const CALENDARIO = { A: [[1, 16], [7, 15]], B: [[7, 16], [12, 16]] };
const ESTADO_CICLO = {
  activo: ["En curso", "bg-semaforo-verde-fondo text-semaforo-verde"],
  proximo: ["Próximo", "bg-surface-container-high text-on-secondary-container"],
  cerrado: ["Cerrado", "bg-surface-container text-on-surface-variant"]
};

let ciclos = [];
let materias = [];
let materiaEditada = null;

let mallas = [];

function iniciarCatalogos() {
  document.getElementById("select-malla").addEventListener("change", pintarMalla);
  document.getElementById("form-malla").addEventListener("submit", guardarEnMalla);
  document.getElementById("btn-recalcular").addEventListener("click", recalcularRiesgo);
  document.getElementById("form-ciclo").addEventListener("submit", registrarCiclo);
  document.getElementById("input-ciclo-nombre").addEventListener("input", previsualizarCiclo);
  document.getElementById("form-carrera").addEventListener("submit", registrarCarrera);
  document.getElementById("btn-nueva-materia").addEventListener("click", () => abrirMateria(null));
  document.getElementById("form-materia").addEventListener("submit", guardarMateria);
  document.getElementById("buscar-materia").addEventListener("input", pintarMaterias);
}

async function cargarCatalogos() {
  await Promise.all([cargarCiclos(), cargarCarreras(), cargarMaterias(), cargarMallas()]);
  pintarMalla();  // la lista para agregar materias necesita el catálogo ya cargado
}

// ==================== PLANES DE ESTUDIO (RF-56) Y ANÁLISIS DE RIESGO (RF-53) ====================

async function cargarMallas() {
  try {
    mallas = await pedir("/admin/mallas", { conToken: true });
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  }
  const select = document.getElementById("select-malla");
  const elegido = select.value;
  select.innerHTML = "";
  mallas.forEach(m => select.appendChild(new Option(`${m.carrera} · ${m.nombrePlan} (generación ${m.generacion})`, m.id)));
  if (elegido) select.value = elegido;
  pintarMalla();
}

function pintarMalla() {
  const contenedor = document.getElementById("malla-semestres");
  contenedor.innerHTML = "";
  const malla = mallas.find(m => m.id === Number(document.getElementById("select-malla").value));
  if (!malla) {
    contenedor.appendChild(el("p", "text-on-surface-variant", "No hay planes de estudio cargados."));
    return;
  }
  const semestres = [...new Set(malla.materias.map(m => m.semestreBase))].sort((a, b) => a - b);
  for (const s of semestres) {
    const caja = el("div", "bg-surface-container-lowest rounded-xl shadow-sm p-space-md");
    caja.appendChild(el("h3", "font-label-lg text-label-lg text-primary mb-space-sm uppercase tracking-wider", `Semestre ${s}`));
    for (const m of malla.materias.filter(x => x.semestreBase === s)) {
      const fila = el("div", "flex items-center justify-between gap-space-sm py-1.5 border-t border-surface-container first-of-type:border-0");
      const textos = el("div", "min-w-0");
      textos.append(el("p", "font-body-md text-body-md text-on-surface truncate", m.nombre), el("p", "font-caption text-caption text-on-surface-variant font-mono", m.clave));
      const quitar = boton("", "close", "peligro");
      quitar.title = `Quitar ${m.nombre} del plan`;
      quitar.addEventListener("click", () => quitarDeMalla(malla, m));
      fila.append(textos, quitar);
      caja.appendChild(fila);
    }
    contenedor.appendChild(caja);
  }
  const lista = document.getElementById("lista-malla-materias");
  lista.innerHTML = "";
  materias.forEach(m => {
    const opcion = el("option");
    opcion.value = `${m.clave} · ${m.nombre}`;
    lista.appendChild(opcion);
  });
}

async function guardarEnMalla(evento) {
  evento.preventDefault();
  const malla = Number(document.getElementById("select-malla").value);
  const texto = document.getElementById("input-malla-materia").value.trim();
  const materia = materias.find(m => `${m.clave} · ${m.nombre}` === texto || m.clave === texto.toUpperCase() || m.nombre.toLowerCase() === texto.toLowerCase());
  const semestreBase = Number(document.getElementById("input-malla-semestre").value);
  if (!materia) return mostrarAviso("Elige una materia del catálogo.", "error");
  try {
    await pedir(`/admin/mallas/${malla}/materias`, { metodo: "PUT", datos: { materia_id: materia.id, semestreBase }, conToken: true });
    document.getElementById("input-malla-materia").value = "";
    ocultarAviso();
    await cargarMallas();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  }
}

async function quitarDeMalla(malla, m) {
  if (!await confirmar(`¿Quitar ${m.nombre} del plan?`, "Dejará de contar para el rezago de los alumnos de este plan. La materia sigue en el catálogo.", "Quitar")) return;
  try {
    await pedir(`/admin/mallas/${malla.id}/materias/${m.materia_id}`, { metodo: "DELETE", conToken: true });
    await cargarMallas();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  }
}

async function recalcularRiesgo() {
  const b = document.getElementById("btn-recalcular");
  b.disabled = true;
  try {
    const r = await pedir("/admin/riesgo/recalcular", { metodo: "POST", conToken: true });
    mostrarAviso(r.mensaje, "info");
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  } finally {
    b.disabled = false;
  }
}

// ==================== CICLOS (RF-08) ====================

async function cargarCiclos() {
  try {
    ciclos = await pedir("/catalogos/ciclos");
  } catch (error) {
    mostrarErrorApi(error);
  }
  const cuerpo = document.getElementById("tabla-ciclos");
  cuerpo.innerHTML = "";
  for (const c of ciclos) {
    const fila = el("tr", "border-t border-surface-container");
    const estado = el("td", "py-space-md px-space-lg");
    estado.appendChild(chip(...ESTADO_CICLO[c.estado]));
    fila.append(el("td", "py-space-md px-space-lg font-label-lg text-label-lg text-primary", c.nombreOficial),
      el("td", "py-space-md px-space-md", fechaLarga(c.fechaInicio)),
      el("td", "py-space-md px-space-md", fechaLarga(c.fechaTermino)), estado);
    cuerpo.appendChild(fila);
  }
  if (!ciclos.length) {
    const fila = el("tr");
    const celda = el("td", "py-space-lg px-space-lg text-on-surface-variant", "Aún no hay ciclos registrados.");
    celda.colSpan = 4;
    fila.appendChild(celda);
    cuerpo.appendChild(fila);
  }
  const vigente = ciclos.find(c => c.estado === "activo");
  const lugar = document.getElementById("inicio-ciclo");
  lugar.innerHTML = "";
  lugar.appendChild(vigente ? chip(`Ciclo en curso: ${vigente.nombreOficial}`, ESTADO_CICLO.activo[1])
    : chip("No hay ciclo en curso", "bg-semaforo-rojo-fondo text-semaforo-rojo"));
}

function fechaLarga(texto) {           // "2026-07-16" -> "16 jul 2026"
  return `${fechaCorta(texto)} ${texto.slice(0, 4)}`;
}

function previsualizarCiclo() {
  const nombre = document.getElementById("input-ciclo-nombre").value.trim().toUpperCase();
  const m = nombre.match(/^(\d{4})-([AB])$/);
  const texto = document.getElementById("ciclo-fechas");
  if (!m) {
    texto.textContent = "Escribe AAAA-A o AAAA-B. Las fechas salen del calendario oficial.";
    return;
  }
  const [[mi, di], [mt, dt]] = CALENDARIO[m[2]];
  texto.textContent = `${nombre}: del ${di} ${MESES[mi - 1]} ${m[1]} al ${dt} ${MESES[mt - 1]} ${m[1]}.`;
}

async function registrarCiclo(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-ciclo");
  const nombreOficial = document.getElementById("input-ciclo-nombre").value.trim().toUpperCase();
  if (!/^\d{4}-[AB]$/.test(nombreOficial)) return marcarCampo("nombreOficial", "Usa el formato AAAA-A o AAAA-B (por ejemplo 2027-A)");
  const b = document.getElementById("btn-guardar-ciclo");
  botonCargando(b, true);
  try {
    await pedir("/admin/ciclos", { metodo: "POST", datos: { nombreOficial }, conToken: true });
    document.getElementById("form-ciclo").reset();
    previsualizarCiclo();
    await cargarCiclos();
  } catch (error) {
    // 409 ciclo repetido · 422 formato inválido
    if (error.status !== 401) mostrarErrorApi(error, "aviso-ciclo");
  } finally {
    botonCargando(b, false);
  }
}

// ==================== CARRERAS (RF-02) ====================

async function cargarCarreras() {
  try {
    carreras = await pedir("/catalogos/carreras");
  } catch (error) {
    mostrarErrorApi(error);
  }
  const lista = document.getElementById("lista-carreras");
  lista.innerHTML = "";
  for (const c of carreras) {
    const fila = el("div", "flex items-center gap-space-sm p-space-sm rounded-lg bg-surface-container-low");
    fila.append(el("span", "font-mono font-label-lg text-label-lg text-primary w-16 shrink-0", c.clave), el("span", "font-body-md text-body-md", c.nombre));
    lista.appendChild(fila);
  }
  pintarUsuarios();  // la tabla de usuarios muestra el nombre de la carrera
}

async function registrarCarrera(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-carrera");
  const datos = {
    clave: document.getElementById("input-carrera-clave").value.trim().toUpperCase(),
    nombre: document.getElementById("input-carrera-nombre").value.trim()
  };
  if (!datos.clave || !datos.nombre) return mostrarAviso("Escribe la clave y el nombre de la carrera.", "error", "aviso-carrera");
  const b = document.getElementById("btn-guardar-carrera");
  botonCargando(b, true);
  try {
    await pedir("/admin/carreras", { metodo: "POST", datos, conToken: true });
    document.getElementById("form-carrera").reset();
    await cargarCarreras();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error, "aviso-carrera");
  } finally {
    botonCargando(b, false);
  }
}

// ==================== MATERIAS (RF-94) ====================

async function cargarMaterias() {
  try {
    materias = await pedir("/catalogos/materias");
  } catch (error) {
    mostrarErrorApi(error);
  }
  pintarMaterias();
}

function pintarMaterias() {
  const cuerpo = document.getElementById("tabla-materias");
  cuerpo.innerHTML = "";
  const texto = document.getElementById("buscar-materia").value.trim().toLowerCase();
  const visibles = materias.filter(m => !texto || `${m.clave} ${m.nombre}`.toLowerCase().includes(texto));
  document.getElementById("materias-total").textContent = String(materias.length);
  for (const m of visibles) {
    const fila = el("tr", "border-t border-surface-container hover:bg-surface-container-low");
    const acciones = el("td", "py-space-sm px-space-lg");
    const grupo = el("div", "flex justify-end gap-1");
    const editar = boton("", "edit", "suave");
    editar.title = "Editar materia";
    editar.addEventListener("click", () => abrirMateria(m));
    const borrar = boton("", "delete", "peligro");
    borrar.title = "Eliminar materia";
    borrar.addEventListener("click", () => eliminarMateria(m));
    grupo.append(editar, borrar);
    acciones.appendChild(grupo);
    fila.append(el("td", "py-space-sm px-space-lg font-mono font-label-lg text-label-lg text-primary", m.clave),
      el("td", "py-space-sm px-space-md", m.nombre), acciones);
    cuerpo.appendChild(fila);
  }
  if (!visibles.length) {
    const fila = el("tr");
    const celda = el("td", "py-space-lg px-space-lg text-on-surface-variant", materias.length ? "Ninguna materia coincide." : "El catálogo está vacío.");
    celda.colSpan = 3;
    fila.appendChild(celda);
    cuerpo.appendChild(fila);
  }
}

function abrirMateria(m) {
  materiaEditada = m;
  document.getElementById("form-materia").reset();
  limpiarErrores("aviso-materia");
  document.getElementById("materia-titulo").textContent = m ? "Editar materia" : "Nueva materia";
  document.getElementById("input-materia-clave").value = m?.clave || "";
  document.getElementById("input-materia-nombre").value = m?.nombre || "";
  abrirModal("modal-materia");
  document.getElementById("input-materia-clave").focus();
}

async function guardarMateria(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-materia");
  const datos = {
    clave: document.getElementById("input-materia-clave").value.trim().toUpperCase(),
    nombre: document.getElementById("input-materia-nombre").value.trim()
  };
  if (!datos.clave || !datos.nombre) return mostrarAviso("Escribe la clave y el nombre oficial.", "error", "aviso-materia");
  const b = document.getElementById("btn-guardar-materia");
  botonCargando(b, true);
  try {
    if (materiaEditada) await pedir(`/admin/materias/${materiaEditada.id}`, { metodo: "PATCH", datos, conToken: true });
    else await pedir("/admin/materias", { metodo: "POST", datos, conToken: true });
    cerrarModal("modal-materia");
    await cargarMaterias();
  } catch (error) {
    // 409 clave repetida · 422 formato inválido
    if (error.status !== 401) mostrarErrorApi(error, "aviso-materia");
  } finally {
    botonCargando(b, false);
  }
}

async function eliminarMateria(m) {
  if (!await confirmar(`¿Eliminar ${m.clave} · ${m.nombre}?`, "Solo se puede eliminar si no está en un plan de estudios, un curso o un historial. Si ya se usa, corrígela con Editar.", "Eliminar")) return;
  try {
    await pedir(`/admin/materias/${m.id}`, { metodo: "DELETE", conToken: true });
    await cargarMaterias();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}
