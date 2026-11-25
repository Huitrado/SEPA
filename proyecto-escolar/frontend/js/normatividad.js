// ============================================================
// normatividad.js: pinta la sección de normatividad (normatividad.html) para el estudiante.
//   RF-81  Páginas estáticas con extractos del reglamento (sin backend: el texto está en
//          normatividad-contenido.js)
//   RF-82  Secciones fijas: criterios de evaluación, asistencia y permanencia
//   RF-83  #asistencia y RF-84 #permanencia: destino de los avisos del panel del curso
//   RF-85, RF-86  Guía de SIATCE con sus enlaces · RF-87 directorio · RF-88 "¿Por dónde empiezo?"
// Lo que aún no llega del reglamento se muestra como un recuadro "Pendiente".
// ============================================================

document.addEventListener("DOMContentLoaded", iniciarNormatividad);

async function iniciarNormatividad() {
  const perfil = await protegerPagina(["estudiante"]);
  if (!perfil) return;
  const fuente = document.getElementById("fuente");
  fuente.appendChild(texto(NORMATIVIDAD.fuente, "font-helper-sm text-helper-sm text-on-surface-variant"));
  pintarIndice();
  pintarSecciones();
  // Al llegar con un ancla (#asistencia), el contenido se pinta después de cargar: hay que bajar a mano
  if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
}

function pintarIndice() {
  const indice = document.getElementById("indice");
  for (const s of NORMATIVIDAD.secciones) {
    const a = el("a", "inline-flex items-center gap-1 px-space-md py-1.5 rounded-lg bg-surface-container-low text-on-surface-variant hover:bg-surface-container hover:text-primary font-label-md text-label-md transition-colors");
    a.href = `#${s.id}`;
    a.append(icono(s.icono), el("span", "", s.titulo));
    indice.appendChild(a);
  }
}

function pintarSecciones() {
  const contenedor = document.getElementById("secciones");
  for (const s of NORMATIVIDAD.secciones) {
    const seccion = el("section", "scroll-mt-24 bg-surface-container-lowest rounded-xl shadow-sm p-space-lg space-y-space-md");
    seccion.id = s.id;
    const cabeza = el("div");
    const titulo = el("h2", "font-title-lg text-title-lg text-primary flex items-center gap-space-xs");
    titulo.append(icono(s.icono, "text-[24px]"), el("span", "", s.titulo));
    cabeza.append(titulo, el("p", "font-body-md text-body-md text-on-surface-variant mt-1", s.resumen));
    seccion.appendChild(cabeza);
    s.bloques.forEach(b => seccion.appendChild(bloque(b)));
    contenedor.appendChild(seccion);
  }
}

// ---------- Bloques (formatos en normatividad-contenido.js) ----------

// Un texto o un placeholder { pendiente: "..." }
function texto(valor, clases = "font-body-md text-body-md text-on-surface") {
  if (valor && typeof valor === "object" && "pendiente" in valor) return pendiente(valor.pendiente);
  return el("p", clases, valor);
}

function pendiente(descripcion) {
  const caja = el("div", "flex items-start gap-space-xs p-space-sm rounded-lg border border-dashed border-outline text-on-surface-variant");
  caja.append(icono("edit_note", "text-[20px] shrink-0"),
    el("p", "font-body-md text-body-md italic", `Pendiente: ${descripcion}`));
  return caja;
}

function bloque(b) {
  if (typeof b === "string" || "pendiente" in b) return texto(b);
  if (b.articulo) {
    const caja = el("div", "pl-space-md border-l-4 border-secondary space-y-1");
    caja.append(el("p", "font-label-lg text-label-lg text-primary", b.articulo), texto(b.texto));
    return caja;
  }
  if (b.lista) {
    const ul = el("ul", "list-disc pl-space-lg space-y-1 font-body-md text-body-md text-on-surface");
    b.lista.forEach(x => ul.appendChild(el("li", "", x)));
    return ul;
  }
  if (b.pasos) {
    const ol = el("ol", "space-y-space-sm");
    b.pasos.forEach((paso, i) => {
      const li = el("li", "flex items-start gap-space-sm");
      const numeroPaso = el("span", "shrink-0 w-7 h-7 rounded-full bg-primary-container text-on-primary flex items-center justify-center font-label-md text-label-md", String(i + 1));
      const contenido = el("div", "flex-1 min-w-0");
      contenido.appendChild(texto(paso));
      li.append(numeroPaso, contenido);
      ol.appendChild(li);
    });
    return ol;
  }
  if (b.enlaces) {
    const fila = el("div", "flex flex-wrap gap-space-sm");
    for (const e of b.enlaces) {
      if (e.url) {
        const a = el("a", "inline-flex items-center gap-space-xs px-space-md py-space-sm rounded-lg bg-primary-container text-on-primary hover:bg-primary font-label-md text-label-md transition-colors");
        a.href = e.url;
        a.target = "_blank";
        a.rel = "noopener";
        a.append(el("span", "", e.texto), icono("open_in_new"));
        fila.appendChild(a);
      } else {
        const sin = el("span", "inline-flex items-center gap-space-xs px-space-md py-space-sm rounded-lg border border-dashed border-outline text-on-surface-variant font-label-md text-label-md");
        sin.append(icono("link_off"), el("span", "", `${e.texto} (enlace pendiente)`));
        fila.appendChild(sin);
      }
    }
    return fila;
  }
  if (b.contactos) {
    const rejilla = el("div", "grid grid-cols-1 sm:grid-cols-2 gap-space-md");
    for (const c of b.contactos) {
      const tarjeta = el("div", "p-space-md rounded-xl bg-surface-container-low space-y-1");
      tarjeta.appendChild(el("p", "font-label-lg text-label-lg text-primary", c.carrera));
      // [campo, ícono, etiqueta, enlace]: el teléfono y el correo se pueden tocar para llamar o escribir
      const campos = [["coordinador", "person", "Coordinador"],
        ["telefono", "call", "Teléfono", v => `tel:+52${v.split(",")[0].replace(/\D/g, "")}`],
        ["correo", "mail", "Correo", v => `mailto:${v}`],
        ["ubicacion", "location_on", "Ubicación"], ["horario", "schedule", "Horario de atención"]];
      for (const [campo, nombreIcono, etiqueta, enlace] of campos) {
        if (!(campo in c)) continue;  // dato que no aplica para esta coordinación
        const valor = c[campo];
        const fila = el("p", `flex items-start gap-space-xs font-body-md text-body-md ${valor ? "text-on-surface" : "text-on-surface-variant italic"}`);
        let contenido = el("span", "", valor || `${etiqueta}: pendiente`);
        if (valor && enlace) {
          contenido = el("a", "text-secondary hover:underline break-all", valor);
          contenido.href = enlace(valor);
        }
        fila.append(icono(nombreIcono, "text-[18px] mt-0.5"), contenido);
        tarjeta.appendChild(fila);
      }
      rejilla.appendChild(tarjeta);
    }
    return rejilla;
  }
  if (b.checklist) {
    const lista = el("ol", "space-y-space-sm");
    for (const item of b.checklist) {
      const li = el("li", "flex items-start gap-space-sm p-space-sm rounded-lg bg-surface-container-low");
      li.appendChild(icono("check_circle", "text-[20px] text-secondary shrink-0"));
      const contenido = el("div", "flex-1 min-w-0 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-space-xs");
      contenido.appendChild(el("p", "font-body-md text-body-md text-on-surface", item.texto));
      if (item.enlace) {
        const a = el("a", "shrink-0 inline-flex items-center gap-1 font-label-md text-label-md text-secondary hover:underline", item.textoEnlace);
        a.href = item.enlace;
        contenido.appendChild(a);
      }
      li.appendChild(contenido);
      lista.appendChild(li);
    }
    return lista;
  }
  return el("p", "text-error", "Bloque con un formato desconocido en normatividad-contenido.js");
}
