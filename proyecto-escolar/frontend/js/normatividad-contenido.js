// ============================================================
// normatividad-contenido.js: TEXTO de la sección de normatividad (RF-81 a RF-88).
// Es el único archivo que hay que editar cuando llegue el reglamento: normatividad.js solo lo pinta.
//
// Cómo se escribe cada bloque de una sección:
//   "Un párrafo normal."
//   { pendiente: "Qué texto falta aquí" }          -> recuadro punteado "Pendiente" (placeholder)
//   { articulo: "Artículo 20", texto: "..." }      -> extracto de un artículo del reglamento
//   { lista: ["...", "..."] }                      -> lista con viñetas
//   { pasos: ["...", "..."] }                      -> pasos numerados (guía SIATCE)
//   { enlaces: [{ texto, url }] }                  -> botones a sitios externos; url null = pendiente
//   { contactos: [{ carrera, coordinador, correo, ubicacion, horario }] }  -> directorio
//   { checklist: [{ texto, enlace?, textoEnlace? }] }                      -> acciones sugeridas
//
// Los "id" de las secciones son las anclas que usan los avisos del panel del curso:
//   #asistencia (RF-83) y #permanencia (RF-84). No los cambies sin cambiar curso-alumno.js.
// ============================================================

const NORMATIVIDAD = {
  // Para mostrar en la página de qué documento salen los extractos
  fuente: { pendiente: "Nombre oficial del reglamento y fecha de la versión que se usó (p. ej. Reglamento General de Evaluación y Promoción de Alumnos de la UdeG)" },

  secciones: [
    {
      id: "evaluacion",
      icono: "fact_check",
      titulo: "Criterios de evaluación",
      resumen: "Cómo se califica una materia y cuál es la calificación mínima para aprobar.",
      bloques: [
        "En SEPA, una materia con calificación numérica se aprueba con 60 o más sobre 100.",
        { pendiente: "Extracto de los artículos sobre la escala de calificaciones y la calificación mínima aprobatoria" },
        { pendiente: "Extracto sobre la evaluación ordinaria y la extraordinaria (cuándo se presenta cada una y cómo se calcula la calificación)" },
        { pendiente: "Extracto sobre la revisión de calificaciones o aclaraciones" }
      ]
    },
    {
      id: "asistencia",  // RF-83: el aviso por asistencia enlaza aquí
      icono: "event_available",
      titulo: "Reglas de asistencia",
      resumen: "Cuánta asistencia necesitas para tener derecho a cada evaluación.",
      bloques: [
        { lista: [
          "Ordinario: 80 % de asistencia o más.",
          "Extraordinario: de 65 % a menos de 80 %.",
          "Sin Derecho: menos de 65 %; pierdes también la evaluación extraordinaria."
        ] },
        "Un retardo cuenta como asistencia.",
        { pendiente: "Extracto de los artículos sobre el porcentaje de asistencia para el periodo ordinario y el extraordinario" },
        { pendiente: "Extracto sobre la pérdida del derecho a evaluación por inasistencias" },
        { pendiente: "Extracto sobre la justificación de faltas (motivos válidos y ante quién se presenta)" }
      ]
    },
    {
      id: "permanencia",  // RF-84: el aviso de artículos 33 a 35 enlaza aquí
      icono: "gavel",
      titulo: "Condiciones de permanencia",
      resumen: "Qué pasa si repruebas una materia más de una vez (artículos 33, 34 y 35) y cuándo procede una baja.",
      bloques: [
        { articulo: "Artículo 33", texto: { pendiente: "Texto del artículo 33" } },
        { articulo: "Artículo 34", texto: { pendiente: "Texto del artículo 34" } },
        { articulo: "Artículo 35", texto: { pendiente: "Texto del artículo 35" } },
        { pendiente: "Extracto sobre las bajas (voluntaria y por reglamento) y cómo afectan tu permanencia" }
      ]
    },
    {
      id: "siatce",  // RF-85, RF-86
      icono: "assignment",
      titulo: "Trámite en SIATCE",
      resumen: "Cómo solicitar tu oportunidad de repetición o una justificación en la plataforma SIATCE.",
      bloques: [
        { pasos: [
          { pendiente: "Paso 1: cómo entrar a SIATCE" },
          { pendiente: "Paso 2: dónde está el trámite de repetición o de justificación" },
          { pendiente: "Paso 3: qué datos y documentos se piden" },
          { pendiente: "Paso 4: cómo saber si fue aceptado y en cuánto tiempo responden" }
        ] },
        { enlaces: [
          { texto: "Ir a SIATCE", url: null },
          { texto: "Calendario de trámites escolares", url: null }
        ] }
      ]
    },
    {
      id: "directorio",  // RF-87
      icono: "contact_mail",
      titulo: "Directorio de coordinaciones",
      resumen: "A quién acudir para una entrevista de revisión académica.",
      bloques: [
        { contactos: [
          { carrera: "Ingeniería en Computación (ICOM)", coordinador: null, correo: null, ubicacion: null, horario: null },
          { carrera: "Ingeniería Informática (INFO)", coordinador: null, correo: null, ubicacion: null, horario: null }
        ] }
      ]
    },
    {
      id: "que-hago",  // RF-88
      icono: "checklist",
      titulo: "¿Por dónde empiezo?",
      resumen: "Si una materia está en rojo o en riesgo de artículo, estos pasos te ayudan a empezar.",
      bloques: [
        { checklist: [
          { texto: "Revisa en tu panel del curso qué te falta: tareas sin entregar, faltas y puntos perdidos.", enlace: "estudiante.html", textoEnlace: "Mis cursos" },
          { texto: "Habla con tu profesor: pregunta qué puedes recuperar y si alguna falta se puede justificar." },
          { texto: "Busca una asesoría de la materia con un compañero asesor.", enlace: "asesorias.html", textoEnlace: "Asesorías" },
          { texto: "Agenda una entrevista con tu coordinación de carrera.", enlace: "#directorio", textoEnlace: "Directorio" },
          { texto: "Si te toca un trámite (repetición o justificación), hazlo dentro de las fechas del calendario.", enlace: "#siatce", textoEnlace: "Trámite en SIATCE" }
        ] }
      ]
    }
  ]
};
