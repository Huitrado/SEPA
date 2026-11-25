// ============================================================
// normatividad-contenido.js: TEXTO de la sección de normatividad (RF-81 a RF-88).
// Es el único archivo que hay que editar para cambiar el contenido: normatividad.js solo lo pinta.
//
// Fuentes:
//   - Reglamento General de Evaluación y Promoción de Alumnos de la UdeG (2017, con la reforma
//     del dictamen IV/2017/153): https://secgral.udg.mx/sites/default/files/Normatividad_general/rgepa-oct-2017.pdf
//   - CUCEI, "Solicitudes de oportunidad por Art. 33, 34 y 35" y "SIATCE"
//     (www.cucei.udg.mx/carreras/tecnologias/alumnos/solicitudes-y-tramites/...)
// Los artículos se resumen en lenguaje sencillo; el texto oficial completo está en el PDF enlazado.
//
// Cómo se escribe cada bloque de una sección:
//   "Un párrafo normal."
//   { pendiente: "Qué texto falta aquí" }          -> recuadro punteado "Pendiente" (placeholder)
//   { articulo: "Artículo 20", texto: "..." }      -> resumen de un artículo del reglamento
//   { lista: ["...", "..."] }                      -> lista con viñetas
//   { pasos: ["...", "..."] }                      -> pasos numerados (guía SIATCE)
//   { enlaces: [{ texto, url }] }                  -> botones a sitios externos; url null = pendiente
//   { contactos: [{ carrera, coordinador, telefono, correo, ubicacion, horario? }] }  -> directorio
//        (un dato en null sale como "pendiente"; uno que no se escribe, como horario, no aparece)
//   { checklist: [{ texto, enlace?, textoEnlace? }] }                      -> acciones sugeridas
//
// Los "id" de las secciones son las anclas que usan los avisos del panel del curso:
//   #asistencia (RF-83), #permanencia (RF-84) y #que-hago (RF-88). No los cambies sin cambiar curso-alumno.js.
// ============================================================

const REGLAMENTO_PDF = "https://secgral.udg.mx/sites/default/files/Normatividad_general/rgepa-oct-2017.pdf";
const SIATCE_URL = "https://escolar.cucei.udg.mx/cescolar/";

const NORMATIVIDAD = {
  // De qué documento salen los resúmenes
  fuente: "Resumen del Reglamento General de Evaluación y Promoción de Alumnos de la Universidad de Guadalajara (2017). Ante cualquier duda, consulta el texto oficial o a tu coordinación de carrera.",

  secciones: [
    {
      id: "evaluacion",
      icono: "fact_check",
      titulo: "Criterios de evaluación",
      resumen: "Cómo se califica una materia y cuál es la calificación mínima para aprobar.",
      bloques: [
        { articulo: "Artículo 5 · Escala de calificaciones",
          texto: "Las calificaciones van de 0 a 100, en números enteros, y la mínima para aprobar es 60. Las materias que no se miden con número se registran como acreditadas (A) o no acreditadas (NA)." },
        { articulo: "Artículo 6 · Promedio",
          texto: "Para tu promedio solo cuentan las materias que aprobaste con calificación numérica." },
        { articulo: "Artículos 9, 10 y 46 · Criterios del curso",
          texto: "Al inicio del curso, tu profesor debe darte a conocer los criterios de evaluación: qué se va a evaluar, cuánto vale cada aspecto y en qué momentos. En SEPA los ves en el bloque \"Encuadre de evaluación\" de cada curso." },
        { articulo: "Artículo 15 · Exámenes",
          texto: "Puede haber exámenes parciales y un examen global, pero ninguno de ellos puede valer por sí solo el 100 % de tu calificación final." },
        { articulo: "Artículos 23 a 25 · Periodo extraordinario",
          texto: "Si no aprobaste en el periodo ordinario, puedes presentar el extraordinario, que evalúa todo el contenido de la materia (no aplica a materias de orden práctico, que se repiten). Tu calificación final suma el 80 % de lo que obtengas en el extraordinario y el 40 % de tu calificación del ordinario." },
        { articulo: "Artículo 49 · Revisión de calificaciones",
          texto: "Si crees que hay un error en tu calificación, puedes pedir por escrito y con justificación una revisión al Jefe del Departamento de la materia, dentro de los 3 días hábiles siguientes a que se publique el resultado. Tres profesores revisan el caso y su resolución es definitiva." },
        { enlaces: [{ texto: "Leer el reglamento completo (PDF oficial)", url: REGLAMENTO_PDF }] }
      ]
    },
    {
      id: "asistencia",  // RF-83: el aviso por asistencia enlaza aquí
      icono: "event_available",
      titulo: "Reglas de asistencia",
      resumen: "Cuánta asistencia necesitas para tener derecho a cada evaluación y cómo justificar faltas.",
      bloques: [
        { lista: [
          "Ordinario: 80 % de asistencia o más.",
          "Extraordinario: de 65 % a menos de 80 %.",
          "Sin Derecho: menos de 65 %; pierdes también la evaluación extraordinaria."
        ] },
        "En SEPA, un retardo cuenta como asistencia.",
        { articulo: "Artículo 20 · Derecho al periodo ordinario",
          texto: "Para que se registre tu calificación en el periodo ordinario necesitas estar inscrito en la materia y tener al menos 80 % de asistencia a clases y actividades del curso." },
        { articulo: "Artículo 27 · Derecho al periodo extraordinario",
          texto: "Para el extraordinario necesitas estar inscrito, haber pagado el arancel (y presentar el comprobante) y tener al menos 65 % de asistencia. Con menos de 65 % ya no tienes derecho a ninguna de las dos evaluaciones." },
        { articulo: "Artículo 53 · Faltas que se pueden justificar",
          texto: "Solo se justifican faltas por enfermedad, por una comisión de una autoridad universitaria relacionada con tus estudios o por una causa de fuerza mayor que valore tu Coordinador de Carrera. Se puede justificar como máximo el 20 % de las horas de la materia." },
        { articulo: "Artículo 54 · Cómo justificarlas",
          texto: "Entrega el documento que compruebe la causa a tu Coordinador de Carrera dentro de los 5 días hábiles siguientes a que puedas volver a clases. Si las acepta, avisa a tus profesores para que lo anoten. En casos excepcionales se puede justificar hasta el 35 % de las horas." }
      ]
    },
    {
      id: "permanencia",  // RF-84: el aviso de artículos 33 a 35 enlaza aquí
      icono: "gavel",
      titulo: "Condiciones de permanencia",
      resumen: "Qué pasa si repruebas una materia más de una vez (artículos 33, 34 y 35) y cuándo procede una baja.",
      bloques: [
        "En corto: si repruebas una materia dos veces (la primera vez y al recursarla), causas baja. Puedes pedir una tercera oportunidad, pero si también la repruebas, la baja es definitiva y no puedes volver a esa carrera.",
        { articulo: "Artículo 33 · Repetir la materia",
          texto: "Si no apruebas una materia ni en el periodo extraordinario, debes repetirla en el siguiente ciclo en que se ofrezca, con oportunidad de aprobarla en ordinario o en extraordinario. Si tampoco la apruebas al repetirla, serás dado de baja." },
        { articulo: "Artículo 34 · Nueva oportunidad",
          texto: "Si causaste baja por el artículo 33, puedes pedir por escrito a la Comisión de Educación del Consejo de Centro, antes de que empiece el ciclo siguiente, una nueva oportunidad para acreditar las materias que debes. La Comisión decide según tus argumentos, tu historia académica y tu conducta. Si te la autoriza, solo puedes acreditar en el periodo ordinario; si no te presentas o no apruebas todas las materias que debes, la baja es automática y definitiva." },
        { articulo: "Artículo 35 · Sin reingreso",
          texto: "Quien es dado de baja por los artículos 32, 33 o 34 ya no puede reingresar a la carrera de la que fue dado de baja." },
        { enlaces: [
          { texto: "Solicitudes de oportunidad (CUCEI)", url: "https://www.cucei.udg.mx/carreras/tecnologias/alumnos/solicitudes-y-tramites/solicitudes-de-oportunidad-por-art-33-34-y-35-0" },
          { texto: "Leer el reglamento completo (PDF oficial)", url: REGLAMENTO_PDF }
        ] }
      ]
    },
    {
      id: "siatce",  // RF-85, RF-86
      icono: "assignment",
      titulo: "Trámite en SIATCE",
      resumen: "SIATCE es el sistema de atención electrónica al estudiante del CUCEI. Ahí haces la solicitud de oportunidad (artículo 34), la de licencia y otros trámites, como constancias y kárdex.",
      bloques: [
        { pasos: [
          "Entra a SIATCE con los datos de tu cuenta de SIIAU.",
          "Elige el trámite que necesitas: la solicitud de oportunidad si causaste baja por el artículo 33, la de licencia u otro trámite (constancias, kárdex, certificados).",
          "En la solicitud de oportunidad explica por escrito tus argumentos: la Comisión de Educación los revisa junto con tu historia académica y tu conducta.",
          "Hazlo antes de que empiece el ciclo siguiente a tu baja. Las solicitudes solo se reciben en las fechas que se publican cada ciclo: pregunta en tu coordinación y revisa las redes oficiales del CUCEI.",
          "Si te autorizan la oportunidad, solo puedes aprobar en el periodo ordinario. Organízate desde el primer día: busca asesoría y habla con tu profesor."
        ] },
        { enlaces: [
          { texto: "Ir a SIATCE", url: SIATCE_URL },
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
          { carrera: "Coordinación de Ingeniería en Computación (ICOM)",
            coordinador: "Mtro. Pedro Misraim Gómez Rodríguez",
            telefono: "33 1378 5900, ext. 27734",
            correo: "cdcomp@cucei.udg.mx",
            ubicacion: "Blvd. Marcelino García Barragán #1421, esq. Calzada Olímpica" },
          { carrera: "Coordinación de Ingeniería Informática (INFO)",
            coordinador: "Mtra. Sara Esquivel Torres",
            telefono: "33 1378 5900, ext. 27736",
            correo: "cdinf@cucei.udg.mx",
            ubicacion: "Blvd. Marcelino García Barragán #1421, esq. Calzada Olímpica" }
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
          { texto: "Habla con tu profesor: pregunta qué puedes recuperar y si alguna falta se puede justificar.", enlace: "#asistencia", textoEnlace: "Justificar faltas" },
          { texto: "Busca una asesoría de la materia con un compañero asesor.", enlace: "asesorias.html", textoEnlace: "Asesorías" },
          { texto: "Agenda una entrevista con tu coordinación de carrera.", enlace: "#directorio", textoEnlace: "Directorio" },
          { texto: "Si te toca un trámite (oportunidad o licencia), hazlo en SIATCE dentro de las fechas publicadas.", enlace: "#siatce", textoEnlace: "Trámite en SIATCE" }
        ] }
      ]
    }
  ]
};
