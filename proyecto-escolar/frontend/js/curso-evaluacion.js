// ============================================================
// curso-evaluacion.js: pestañas "Actividades", "Encuadre" y "Calificaciones" de curso.html.
//   Encuadre      RF-31, RF-32  -> GET/POST/PATCH/DELETE .../categorias
//   Actividades   RF-29, RF-30, RF-33, RF-34 -> GET/POST/PATCH/DELETE .../actividades
//                 RF-36 archivo del docente   -> PUT/DELETE .../actividades/{id}/archivo
//   Calificaciones RF-40, RF-46, RF-47         -> GET .../calificaciones
//   La revisión de entregas y la calificación de cada alumno están en actividad.html.
// Usa C, rutaCurso(), avisarError(), cargarMatricula() y pintarMetricas() de curso.js.
// ============================================================

// Colores de las categorías en la barra del encuadre (tomados del diseño)
const COLORES_CATEGORIA = ["#1a1a1a", "#00aeef", "#6b7075", "#0077b6", "#9fdcf3", "#3a3d40", "#b8bec3", "#00557f"];

let actividadEditada = null;   // null = crear; si no, la actividad que se edita
let categoriaEditada = null;

function iniciarEvaluacion() {
  document.getElementById("form-categoria").addEventListener("submit", crearCategoria);
  document.getElementById("form-editar-categoria").addEventListener("submit", guardarCategoria);
  document.getElementById("form-actividad").addEventListener("submit", guardarActividad);
  document.getElementById("select-act-categoria").addEventListener("change", pintarImpacto);
  document.getElementById("btn-crear-actividad").addEventListener("click", () => abrirActividad(null));
}

async function cargarEvaluacion() {
  await Promise.all([cargarEncuadre(), cargarActividades(), cargarCalificaciones()]);
  // El encuadre cuenta actividades y las actividades se agrupan por categoría: se repintan con ambos datos
  pintarEncuadre();
  pintarActividades();
}

function colorCategoria(id) {
  const indice = (C.categorias?.categorias || []).findIndex(c => c.id === id);
  return COLORES_CATEGORIA[Math.max(indice, 0) % COLORES_CATEGORIA.length];
}

function actividadesDe(categoriaId) {
  return C.actividades.filter(a => a.categoriaEvaluacion_id === categoriaId);
}

// ==================== ENCUADRE (RF-31, RF-32, RF-34) ====================

async function cargarEncuadre() {
  try {
    C.categorias = await pedir(rutaCurso("/categorias"), { conToken: true });
  } catch (error) {
    avisarError(error);
  }
  pintarEncuadre();
}

function pintarEncuadre() {
  const datos = C.categorias;
  if (!datos) return;

  const estado = document.getElementById("encuadre-estado");
  estado.innerHTML = "";
  estado.appendChild(datos.pesosCompletos
    ? chipSemaforo("verde", "Suma 100 %")
    : chipSemaforo("amarillo", `Suma ${numero(datos.sumaPesos)} %`));

  const barra = document.getElementById("encuadre-barra");
  const leyenda = document.getElementById("encuadre-leyenda");
  barra.innerHTML = "";
  leyenda.innerHTML = "";
  for (const c of datos.categorias) {
    const segmento = el("div", "h-full");
    segmento.style.width = `${c.porcentajePeso}%`;
    segmento.style.backgroundColor = colorCategoria(c.id);
    segmento.title = `${c.nombre}: ${numero(c.porcentajePeso)} %`;
    barra.appendChild(segmento);
    const item = el("span", "inline-flex items-center gap-1.5");
    const punto = el("span", "w-2.5 h-2.5 rounded-full");
    punto.style.backgroundColor = colorCategoria(c.id);
    item.append(punto, el("span", "", `${c.nombre} (${numero(c.porcentajePeso)} %)`));
    leyenda.appendChild(item);
  }

  const advertencia = document.getElementById("encuadre-advertencia");
  advertencia.classList.toggle("hidden", !datos.advertencia);
  advertencia.querySelector("[data-texto]").textContent = datos.advertencia || "";

  const lista = document.getElementById("categorias-lista");
  lista.innerHTML = "";
  if (!datos.categorias.length) {
    lista.appendChild(el("p", "bg-surface-container-lowest rounded-xl shadow-sm p-space-lg text-on-surface-variant",
      "Aún no hay categorías. Agrega las del encuadre (por ejemplo Exámenes, Tareas y Proyecto) hasta sumar 100 %."));
    return;
  }
  for (const c of datos.categorias) lista.appendChild(tarjetaCategoria(c));
}

function tarjetaCategoria(c) {
  const actividades = actividadesDe(c.id);
  const tarjeta = el("article", "bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex items-center gap-space-md");
  const marca = el("span", "w-3 self-stretch rounded-full shrink-0");
  marca.style.backgroundColor = colorCategoria(c.id);
  const textos = el("div", "flex-1 min-w-0");
  textos.append(
    el("h3", "font-title-lg text-title-lg text-primary", c.nombre),
    el("p", "font-body-md text-body-md text-on-surface-variant", actividades.length
      ? `${actividades.length} actividad${actividades.length === 1 ? "" : "es"} · cada una vale ${numero(c.porcentajePeso / actividades.length)} % del curso`
      : "Sin actividades todavía")
  );
  const peso = el("p", "font-headline-md text-headline-md text-primary shrink-0", `${numero(c.porcentajePeso)} %`);
  const acciones = el("div", "flex gap-1 shrink-0");
  const editar = boton("", "edit", "suave");
  editar.title = "Editar categoría";
  editar.addEventListener("click", () => abrirCategoria(c));
  const borrar = boton("", "delete", "peligro");
  borrar.title = actividades.length ? "No se puede eliminar: ya tiene actividades" : "Eliminar categoría";
  borrar.disabled = actividades.length > 0;
  borrar.addEventListener("click", () => eliminarCategoria(c));
  acciones.append(editar, borrar);
  tarjeta.append(marca, textos, peso, acciones);
  return tarjeta;
}

async function crearCategoria(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-categoria");
  const datos = {
    nombre: document.getElementById("input-cat-nombre").value.trim(),
    porcentajePeso: Number(document.getElementById("input-cat-peso").value)
  };
  if (!datos.nombre) return marcarCampo("nombre", "Escribe el nombre de la categoría");
  if (!(datos.porcentajePeso > 0 && datos.porcentajePeso <= 100)) return marcarCampo("porcentajePeso", "Debe ser mayor que 0 y hasta 100");
  const b = document.getElementById("btn-guardar-categoria");
  botonCargando(b, true);
  try {
    await pedir(rutaCurso("/categorias"), { metodo: "POST", datos, conToken: true });
    document.getElementById("form-categoria").reset();
    await cargarEncuadre();
    pintarActividades();
    pintarMetricas();
  } catch (error) {
    // 409: el nombre se repite o la suma pasaría de 100
    if (error.status !== 401) mostrarErrorApi(error, "aviso-categoria");
  } finally {
    botonCargando(b, false);
  }
}

function abrirCategoria(c) {
  categoriaEditada = c;
  limpiarErrores("aviso-editar-categoria");
  document.getElementById("input-edit-cat-nombre").value = c.nombre;
  document.getElementById("input-edit-cat-peso").value = c.porcentajePeso;
  abrirModal("modal-categoria");
}

async function guardarCategoria(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-editar-categoria");
  const datos = {
    nombre: document.getElementById("input-edit-cat-nombre").value.trim(),
    porcentajePeso: Number(document.getElementById("input-edit-cat-peso").value)
  };
  const b = document.getElementById("btn-editar-categoria");
  botonCargando(b, true);
  try {
    await pedir(rutaCurso(`/categorias/${categoriaEditada.id}`), { metodo: "PATCH", datos, conToken: true });
    cerrarModal("modal-categoria");
    // Cambiar un peso cambia lo que vale cada actividad y la acumulada (RF-67)
    await Promise.all([cargarEvaluacion(), cargarMatricula()]);
    pintarMetricas();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error, "aviso-editar-categoria");
  } finally {
    botonCargando(b, false);
  }
}

async function eliminarCategoria(c) {
  if (!await confirmar(`¿Eliminar "${c.nombre}"?`, "La categoría se quitará del encuadre.", "Eliminar")) return;
  try {
    C.categorias = await pedir(rutaCurso(`/categorias/${c.id}`), { metodo: "DELETE", conToken: true });
    pintarEncuadre();
    pintarActividades();
    pintarMetricas();
  } catch (error) {
    avisarError(error);
  }
}

// ==================== ACTIVIDADES (RF-29, RF-30, RF-33 a RF-36) ====================

async function cargarActividades() {
  try {
    C.actividades = await pedir(rutaCurso("/actividades"), { conToken: true });
  } catch (error) {
    avisarError(error);
  }
  pintarActividades();
}

function pintarActividades() {
  const contenedor = document.getElementById("actividades-lista");
  contenedor.innerHTML = "";
  const categorias = C.categorias?.categorias || [];

  const barra = el("div", "flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm");
  barra.appendChild(el("p", "font-body-md text-body-md text-on-surface-variant",
    `${C.actividades.length} actividad${C.actividades.length === 1 ? "" : "es"} agrupadas por categoría del encuadre.`));
  if (C.curso?.estado === "activo" && categorias.length) {
    const crear = boton("Crear actividad", "add_task", "primario");
    crear.addEventListener("click", () => abrirActividad(null));
    barra.appendChild(crear);
  }
  contenedor.appendChild(barra);

  if (!categorias.length) {
    const aviso = el("div", "bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col sm:flex-row sm:items-center justify-between gap-space-md");
    aviso.appendChild(el("p", "text-on-surface-variant", "Para crear actividades primero define el encuadre: cada actividad debe pertenecer a una categoría (RF-33)."));
    const ir = boton("Ir al encuadre", "balance", "secundario");
    ir.addEventListener("click", () => mostrarPestana("encuadre"));
    aviso.appendChild(ir);
    contenedor.appendChild(aviso);
    return;
  }

  for (const c of categorias) {
    const actividades = actividadesDe(c.id);
    const grupo = el("section", "bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden");
    const cabeza = el("div", "px-space-lg py-space-md bg-surface-container-low flex flex-wrap items-center justify-between gap-space-sm");
    const titulo = el("div", "flex items-center gap-space-sm");
    const punto = el("span", "w-3 h-3 rounded-full");
    punto.style.backgroundColor = colorCategoria(c.id);
    titulo.append(punto, el("h3", "font-title-lg text-title-lg text-primary", `${c.nombre} · ${numero(c.porcentajePeso)} %`));
    cabeza.append(titulo, el("span", "font-helper-sm text-helper-sm text-on-surface-variant",
      actividades.length ? `${actividades.length} · ${numero(c.porcentajePeso / actividades.length)} % c/u` : "Sin actividades"));
    grupo.appendChild(cabeza);
    if (!actividades.length) {
      grupo.appendChild(el("p", "px-space-lg py-space-md text-on-surface-variant font-body-md text-body-md", "Aún no hay actividades en esta categoría."));
    }
    actividades.forEach(a => grupo.appendChild(filaActividad(a)));
    contenedor.appendChild(grupo);
  }
}

function filaActividad(a) {
  const vencida = new Date(a.fechaHoraLimite) < new Date();
  const fila = el("div", "px-space-lg py-space-md border-t border-surface-container flex flex-col lg:flex-row lg:items-center gap-space-md");
  const textos = el("div", "flex-1 min-w-0");
  textos.appendChild(el("h4", "font-label-lg text-label-lg text-primary", a.titulo));
  if (a.descripcion) textos.appendChild(el("p", "font-body-md text-body-md text-on-surface-variant line-clamp-2 mt-0.5", a.descripcion));
  const datos = el("div", "flex flex-wrap items-center gap-x-space-md gap-y-1 mt-space-xs font-helper-sm text-helper-sm text-on-surface-variant");
  const dato = (nombreIcono, texto, clases = "") => {
    const s = el("span", `inline-flex items-center gap-1 ${clases}`);
    s.append(icono(nombreIcono, "text-[16px]"), el("span", "", texto));
    return s;
  };
  datos.append(
    dato("event", `Límite: ${fechaHora(a.fechaHoraLimite)}`, vencida ? "text-on-tertiary-container" : ""),
    dato("star", `${numero(a.puntuacionMaxima)} pts`),
    dato("percent", `Vale ${numero(a.valorEnCurso)} % del curso`)
  );
  if (vencida) datos.appendChild(el("span", "font-label-md text-label-md px-2 py-0.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed-variant", "Vencida"));
  textos.appendChild(datos);

  const acciones = el("div", "flex flex-wrap gap-1 shrink-0");
  if (a.tieneArchivo) {
    const archivo = boton("Archivo", "download", "suave");
    archivo.title = "Descargar el archivo adjunto";
    archivo.addEventListener("click", () => descargarArchivo(`/actividades/${a.id}/archivo`).catch(avisarError));
    acciones.appendChild(archivo);
  }
  const revisar = el("a", "inline-flex items-center justify-center gap-space-xs font-label-md text-label-md px-space-md py-space-sm rounded-lg bg-primary-container text-on-primary hover:bg-primary transition-colors");
  revisar.href = `actividad.html?curso=${CURSO_ID}&actividad=${a.id}`;
  revisar.append(icono("fact_check"), el("span", "", "Entregas y calificación"));
  const editar = boton("", "edit", "suave");
  editar.title = "Editar actividad";
  editar.addEventListener("click", () => abrirActividad(a));
  const borrar = boton("", "delete", "peligro");
  borrar.title = "Eliminar actividad";
  borrar.addEventListener("click", () => eliminarActividad(a));
  acciones.append(revisar, editar, borrar);
  fila.append(textos, acciones);
  return fila;
}

function abrirActividad(actividad) {
  const categorias = C.categorias?.categorias || [];
  if (!categorias.length) {
    mostrarPestana("encuadre");
    mostrarAviso("Antes de crear actividades agrega al menos una categoría al encuadre.", "info");
    return;
  }
  actividadEditada = actividad;
  const form = document.getElementById("form-actividad");
  form.reset();
  limpiarErrores("aviso-actividad");
  document.getElementById("actividad-titulo-modal").textContent = actividad ? "Editar actividad" : "Crear actividad";
  document.querySelector("#btn-guardar-actividad [data-texto-boton]").textContent = actividad ? "Guardar cambios" : "Publicar actividad";

  const select = document.getElementById("select-act-categoria");
  select.innerHTML = "";
  select.appendChild(new Option("Selecciona la categoría...", ""));
  for (const c of categorias) select.appendChild(new Option(`${c.nombre} (${numero(c.porcentajePeso)} %)`, c.id));

  document.getElementById("actividad-archivo-actual").classList.toggle("hidden", !actividad?.tieneArchivo);
  document.getElementById("actividad-archivo-actual").classList.toggle("flex", Boolean(actividad?.tieneArchivo));
  if (actividad) {
    document.getElementById("input-act-titulo").value = actividad.titulo;
    document.getElementById("input-act-descripcion").value = actividad.descripcion || "";
    select.value = String(actividad.categoriaEvaluacion_id);
    document.getElementById("input-act-limite").value = actividad.fechaHoraLimite.slice(0, 16);
    document.getElementById("input-act-puntos").value = actividad.puntuacionMaxima;
  }
  pintarImpacto();
  abrirModal("modal-actividad");
  document.getElementById("input-act-titulo").focus();
}

// RF-34: cuánto valdrá la actividad según su categoría
function pintarImpacto() {
  const texto = document.getElementById("actividad-impacto");
  const id = Number(document.getElementById("select-act-categoria").value);
  const categoria = (C.categorias?.categorias || []).find(c => c.id === id);
  if (!categoria) {
    texto.textContent = "Elige una categoría para ver cuánto valdrá esta actividad.";
    return;
  }
  const otras = actividadesDe(id).filter(a => a.id !== actividadEditada?.id).length;
  const total = otras + 1;
  texto.textContent = `Valdrá ${numero(categoria.porcentajePeso / total)} % del curso. "${categoria.nombre}" pesa ${numero(categoria.porcentajePeso)} % y lo reparte por igual entre sus ${total} actividad${total === 1 ? "" : "es"}, sin importar la puntuación máxima de cada una.`;
}

async function guardarActividad(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-actividad");
  const valor = id => document.getElementById(id).value.trim();
  const datos = {
    categoriaEvaluacion_id: Number(valor("select-act-categoria")) || null,
    titulo: valor("input-act-titulo"),
    descripcion: valor("input-act-descripcion"),  // texto vacío (no null) para poder borrarla al editar
    fechaHoraLimite: valor("input-act-limite"),
    puntuacionMaxima: Number(valor("input-act-puntos"))
  };
  const errores = [];
  if (!datos.titulo) errores.push(["titulo", "Escribe el título"]);
  if (!datos.categoriaEvaluacion_id) errores.push(["categoriaEvaluacion_id", "Elige la categoría (RF-33)"]);
  if (!datos.fechaHoraLimite) errores.push(["fechaHoraLimite", "Indica la fecha y hora límite"]);
  if (!(datos.puntuacionMaxima > 0)) errores.push(["puntuacionMaxima", "Debe ser mayor que 0"]);
  if (errores.length) {
    errores.forEach(([campo, mensaje]) => marcarCampo(campo, mensaje));
    mostrarAviso("Revisa los campos marcados en rojo.", "error", "aviso-actividad");
    return;
  }
  // Al editar, solo se mandan los campos que cambiaron (la fecha pasada no se vuelve a validar)
  if (actividadEditada) {
    const original = {
      categoriaEvaluacion_id: actividadEditada.categoriaEvaluacion_id,
      titulo: actividadEditada.titulo,
      descripcion: actividadEditada.descripcion || "",
      fechaHoraLimite: actividadEditada.fechaHoraLimite.slice(0, 16),
      puntuacionMaxima: actividadEditada.puntuacionMaxima
    };
    for (const campo of Object.keys(datos)) if (datos[campo] === original[campo]) delete datos[campo];
  }

  const archivo = document.getElementById("input-act-archivo").files[0];
  const quitar = document.getElementById("check-quitar-archivo").checked;
  const b = document.getElementById("btn-guardar-actividad");
  botonCargando(b, true);
  try {
    const actividad = actividadEditada
      ? (Object.keys(datos).length
        ? await pedir(rutaCurso(`/actividades/${actividadEditada.id}`), { metodo: "PATCH", datos, conToken: true })
        : actividadEditada)
      : await pedir(rutaCurso("/actividades"), { metodo: "POST", datos, conToken: true });
    actividadEditada = actividad;  // si falla el archivo, el siguiente intento ya edita
    if (archivo) {
      const formulario = new FormData();
      formulario.append("archivo", archivo);
      await pedir(rutaCurso(`/actividades/${actividad.id}/archivo`), { metodo: "PUT", datos: formulario, conToken: true });
    } else if (quitar && actividad.tieneArchivo) {
      await pedir(rutaCurso(`/actividades/${actividad.id}/archivo`), { metodo: "DELETE", conToken: true });
    }
    cerrarModal("modal-actividad");
    await Promise.all([cargarActividades(), cargarCalificaciones(), cargarMatricula()]);
    pintarEncuadre();
    pintarMetricas();
  } catch (error) {
    // 413 archivo grande · 415 tipo no permitido · 422 fecha pasada o datos inválidos
    if (error.status !== 401) mostrarErrorApi(error, "aviso-actividad");
  } finally {
    botonCargando(b, false);
  }
}

async function eliminarActividad(a) {
  if (!await confirmar(`¿Eliminar "${a.titulo}"?`, "Se borrará la actividad y su archivo adjunto. No se puede eliminar si algún alumno ya entregó.", "Eliminar")) return;
  try {
    C.actividades = await pedir(rutaCurso(`/actividades/${a.id}`), { metodo: "DELETE", conToken: true });
    pintarActividades();
    pintarEncuadre();
    await Promise.all([cargarCalificaciones(), cargarMatricula()]);
    pintarMetricas();
  } catch (error) {
    avisarError(error);
  }
}

// ==================== CALIFICACIONES (RF-40, RF-46, RF-47, RF-67) ====================

async function cargarCalificaciones() {
  try {
    C.calificaciones = await pedir(rutaCurso("/calificaciones"), { conToken: true });
  } catch (error) {
    avisarError(error);
  }
  pintarCalificaciones();
}

function pintarCalificaciones() {
  const tabla = document.getElementById("tabla-calificaciones");
  const vacia = document.getElementById("calificaciones-vacia");
  tabla.innerHTML = "";
  const datos = C.calificaciones;
  if (!datos) return;
  if (!datos.actividades.length || !datos.alumnos.length) {
    vacia.textContent = !datos.alumnos.length ? "No hay alumnos activos en el curso todavía." : "Aún no hay actividades en el curso.";
    vacia.classList.remove("hidden");
    return;
  }
  vacia.classList.add("hidden");

  const fijaAlumno = "sticky left-0 z-10 bg-surface-container-lowest min-w-[150px] max-w-[150px] sm:min-w-[220px] sm:max-w-[220px]";
  const fijaTotal = "sticky left-[150px] sm:left-[220px] z-10 bg-surface-container-lowest min-w-[140px] shadow-[4px_0_6px_-4px_rgba(0,0,0,0.12)]";
  const thead = el("thead");
  const encabezado = el("tr", "font-label-md text-label-md text-on-surface-variant");
  encabezado.append(el("th", `${fijaAlumno} !bg-surface-container py-3 px-space-md uppercase tracking-wider`, "Alumno"),
    el("th", `${fijaTotal} !bg-surface-container py-3 px-space-md uppercase tracking-wider`, "Acumulada"));
  for (const a of datos.actividades) {
    const th = el("th", "bg-surface-container py-2 px-space-sm text-center min-w-[110px] align-top");
    const enlace = el("a", "block rounded-md px-1 py-1 hover:bg-surface-container-high transition-colors");
    enlace.href = `actividad.html?curso=${CURSO_ID}&actividad=${a.id}`;
    enlace.title = `Revisar entregas de ${a.titulo}`;
    enlace.append(el("span", "block text-primary normal-case line-clamp-2", a.titulo),
      el("span", "block font-caption text-caption normal-case mt-0.5", `${numero(a.valorEnCurso)} % · ${numero(a.puntuacionMaxima)} pts`));
    th.appendChild(enlace);
    encabezado.appendChild(th);
  }
  thead.appendChild(encabezado);

  const tbody = el("tbody", "font-body-md text-body-md");
  for (const fila of datos.alumnos) {
    const tr = el("tr", "hover:bg-surface-container-low");
    const nombre = el("td", `${fijaAlumno} py-space-sm px-space-md border-t border-surface-container`);
    nombre.append(el("p", "font-label-lg text-label-lg text-primary truncate", `${fila.apellidos} ${fila.nombre}`),
      el("p", "font-helper-sm text-helper-sm text-on-surface-variant font-mono", fila.codigoEstudiante));
    const total = el("td", `${fijaTotal} py-space-sm px-space-md border-t border-surface-container`);
    total.append(el("p", "font-label-lg text-label-lg text-primary", `${numero(fila.calificacionAcumulada)} / 100`),
      el("p", `font-helper-sm text-helper-sm ${fila.desempenoProporcional !== null && fila.desempenoProporcional < 60 ? "text-error" : "text-on-surface-variant"}`,
        fila.desempenoProporcional === null ? "Sin evaluar" : `${numero(fila.desempenoProporcional, 1)} % de ${numero(fila.puntosPosibles)}`));
    tr.append(nombre, total);
    fila.celdas.forEach((celda, i) => tr.appendChild(celdaCalificacion(celda, datos.actividades[i])));
    tbody.appendChild(tr);
  }
  tabla.append(thead, tbody);
}

function celdaCalificacion(celda, actividad) {
  const td = el("td", "py-space-sm px-space-sm text-center border-t border-surface-container");
  if (celda.calificacion) {
    td.appendChild(el("span", "font-label-lg text-label-lg text-primary", `${numero(celda.calificacion.calificacionObtenida)}/${numero(actividad.puntuacionMaxima)}`));
    if (celda.estadoEntrega === "entregada_con_retraso") td.appendChild(el("span", "block font-caption text-caption text-on-tertiary-container", "con retraso"));
  } else if (celda.entrega_id) {
    const pendiente = el("span", "inline-flex items-center gap-1 font-label-md text-label-md text-on-tertiary-container");
    pendiente.append(icono("inbox", "text-[16px]"), el("span", "", "Por calificar"));
    td.appendChild(pendiente);
  } else if (celda.cuentaComoCero) {
    const cero = el("span", "font-label-lg text-label-lg text-error", "0");
    cero.title = "Venció sin entrega: cuenta como 0 (RF-47)";
    td.append(cero, el("span", "block font-caption text-caption text-error", "sin entrega"));
  } else {
    td.appendChild(el("span", "text-outline", "—"));
  }
  return td;
}
