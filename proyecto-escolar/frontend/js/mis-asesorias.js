// ============================================================
// mis-asesorias.js: publicaciones del asesor (mis-asesorias.html).
//   RF-92  Solo para estudiantes con rol de asesor; los demás vuelven al tablero
//   RF-74  Crear: materia, horario, modalidad y lugar o medio (obligatorios) -> POST /asesorias
//   RF-75  Temas a tratar (texto libre)
//   RF-76  Editar cualquier campo                                           -> PATCH /asesorias/{id}
//   RF-77  Ocultar del tablero (inactiva) o eliminar                         -> PATCH .../{id}, DELETE /asesorias/{id}
// ============================================================

document.addEventListener("DOMContentLoaded", iniciarMisAsesorias);

let mias = [];
let editando = null;

async function iniciarMisAsesorias() {
  const perfil = await protegerPagina(["estudiante"]);
  if (!perfil) return;
  if (!perfil.roles.includes("asesor")) return window.location.replace("asesorias.html");
  document.getElementById("form-publicacion").addEventListener("submit", guardar);
  document.getElementById("btn-cancelar-edicion").addEventListener("click", () => limpiarFormulario());
  document.querySelectorAll('input[name="modalidad"]').forEach(r => r.addEventListener("change", ajustarLugar));
  pedir("/catalogos/materias").then(materias => {
    const lista = document.getElementById("lista-materias");
    materias.forEach(m => {
      const opcion = el("option");
      opcion.value = m.nombre;
      opcion.label = m.clave;
      lista.appendChild(opcion);
    });
  }).catch(() => {});
  await cargar();
}

async function cargar() {
  try {
    mias = await pedir("/asesorias/mias", { conToken: true });
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  }
  document.getElementById("cargando").classList.add("hidden");
  pintar();
}

function ajustarLugar() {
  const virtual = document.querySelector('input[name="modalidad"]:checked').value === "virtual";
  document.getElementById("label-lugar").textContent = virtual ? "Enlace o medio" : "Lugar";
  document.getElementById("input-lugar").placeholder = virtual ? "https://meet.google.com/... o Teams" : "Módulo X, salón 12";
}

function pintar() {
  const lista = document.getElementById("lista");
  lista.innerHTML = "";
  document.getElementById("vacio").classList.toggle("hidden", mias.length > 0);
  for (const p of mias) {
    const activa = p.estado === "activa";
    const t = el("article", `bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-sm ${activa ? "" : "opacity-75"}`);
    const cabeza = el("div", "flex flex-wrap items-start justify-between gap-space-sm");
    const titulos = el("div", "min-w-0");
    titulos.append(el("h3", "font-title-lg text-title-lg text-primary", p.materia),
      el("p", "font-body-md text-body-md text-on-surface-variant", `${p.horario} · ${p.modalidad === "virtual" ? "Virtual" : "Presencial"} · ${p.lugarOMedio}`));
    const estado = el("span", `px-2.5 py-0.5 rounded-full font-label-md text-label-md ${activa ? "bg-semaforo-verde-fondo text-semaforo-verde" : "bg-surface-container text-on-surface-variant"}`,
      activa ? "Visible en el tablero" : "Oculta");
    cabeza.append(titulos, estado);
    t.appendChild(cabeza);
    if (p.topico) t.appendChild(el("p", "font-body-md text-body-md text-on-surface", p.topico));

    const acciones = el("div", "flex flex-wrap gap-1 pt-space-xs");
    const editar = boton("Editar", "edit", "suave");
    editar.addEventListener("click", () => editarPublicacion(p));
    const alternar = boton(activa ? "Ocultar del tablero" : "Volver a publicar", activa ? "visibility_off" : "visibility", "secundario");
    alternar.addEventListener("click", () => cambiarEstado(p, activa ? "inactiva" : "activa"));
    const borrar = boton("Eliminar", "delete", "peligro");
    borrar.addEventListener("click", () => eliminar(p));
    acciones.append(editar, alternar, borrar);
    t.appendChild(acciones);
    lista.appendChild(t);
  }
}

function limpiarFormulario() {
  editando = null;
  document.getElementById("form-publicacion").reset();
  limpiarErrores("aviso-publicacion");
  document.getElementById("form-titulo").textContent = "Nueva publicación";
  document.querySelector("#btn-publicar [data-texto-boton]").textContent = "Publicar en el tablero";
  document.getElementById("btn-cancelar-edicion").classList.add("hidden");
  ajustarLugar();
}

function editarPublicacion(p) {
  limpiarFormulario();
  editando = p;
  document.getElementById("form-titulo").textContent = "Editar publicación";
  document.querySelector("#btn-publicar [data-texto-boton]").textContent = "Guardar cambios";
  document.getElementById("btn-cancelar-edicion").classList.remove("hidden");
  document.getElementById("input-materia").value = p.materia;
  document.getElementById("input-horario").value = p.horario;
  document.querySelector(`input[name="modalidad"][value="${p.modalidad}"]`).checked = true;
  document.getElementById("input-lugar").value = p.lugarOMedio;
  document.getElementById("input-topico").value = p.topico || "";
  ajustarLugar();
  document.getElementById("form-publicacion").scrollIntoView({ behavior: "smooth", block: "start" });
  document.getElementById("input-materia").focus();
}

async function guardar(evento) {
  evento.preventDefault();
  limpiarErrores("aviso-publicacion");
  const valor = id => document.getElementById(id).value.trim();
  const datos = {
    materia: valor("input-materia"),
    horario: valor("input-horario"),
    modalidad: document.querySelector('input[name="modalidad"]:checked').value,
    lugarOMedio: valor("input-lugar"),
    topico: valor("input-topico")
  };
  const faltan = ["materia", "horario", "lugarOMedio"].filter(c => !datos[c]);
  if (faltan.length) {
    faltan.forEach(c => marcarCampo(c, "Este campo es obligatorio"));
    mostrarAviso("Materia, horario, modalidad y lugar o medio son obligatorios.", "error", "aviso-publicacion");
    return;
  }
  const b = document.getElementById("btn-publicar");
  botonCargando(b, true);
  try {
    if (editando) await pedir(`/asesorias/${editando.id}`, { metodo: "PATCH", datos, conToken: true });
    else await pedir("/asesorias", { metodo: "POST", datos: { ...datos, topico: datos.topico || null }, conToken: true });
    limpiarFormulario();
    await cargar();
  } catch (error) {
    // 422: la materia no está en el catálogo o algún dato no es válido
    if (error.status !== 401) mostrarErrorApi(error, "aviso-publicacion");
  } finally {
    botonCargando(b, false);
  }
}

async function cambiarEstado(p, estado) {
  try {
    await pedir(`/asesorias/${p.id}`, { metodo: "PATCH", datos: { estado }, conToken: true });
    await cargar();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  }
}

async function eliminar(p) {
  if (!await confirmar(`¿Eliminar la asesoría de ${p.materia}?`, "Se borrará del tablero y de tu lista. Si solo quieres pausarla, usa \"Ocultar del tablero\".", "Eliminar")) return;
  try {
    await pedir(`/asesorias/${p.id}`, { metodo: "DELETE", conToken: true });
    if (editando?.id === p.id) limpiarFormulario();
    await cargar();
  } catch (error) {
    if (error.status !== 401) mostrarErrorApi(error);
  }
}
