r"""Datos de demostración para ver las pantallas con un grupo lleno (solo para desarrollo).

Crea un docente de demostración con dos cursos del ciclo 2026-B y 17 alumnos con perfiles
distintos (al día, regulares, en riesgo, uno dado de baja y tres con historial o rezago), con asistencia desde agosto,
entregas (a tiempo, con retraso y sin entregar) y calificaciones con retroalimentación.
No toca las cuentas ni los cursos que ya existen.

Uso, desde la carpeta backend (con el servidor apagado o encendido, da igual):
    .\venv\Scripts\python.exe sembrar_demo.py
Si ya se corrió, no vuelve a crear nada.

Cuentas que crea (todas son de prueba):
    Docente:  número de empleado  DEMO-01    contraseña  Demo12345
    Alumnos:  códigos 219000001 a 219000017  contraseña  Demo12345
      219000001 Ana Torres       al día (verde)
      219000005 Elena Ruiz       regular (amarillo por calificación)
      219000009 Iván Salas       en riesgo (asistencia < 80 %, rojo)
      219000012 Laura Méndez     en riesgo (calificación < 60 %, rojo)
    Historial y rezago (RF-54 a RF-59), plan ICOM:
      219000015 Oscar Valdez     rezago crítico: va en 5.º y cursa Programación Estructurada (2.º)
      219000016 Paola Jiménez    riesgo por historial: reprobó en 2025-B y en 2026-A
      219000017 Ricardo Ponce    casos límite sin alerta: 2 semestres de desfase y reprobó en un solo ciclo

Para borrar los datos de demostración y crearlos de nuevo (no toca nada más):
    .\venv\Scripts\python.exe sembrar_demo.py --reiniciar
"""
import random
import sys
from datetime import date, datetime, timedelta

import models
import schemas
import services
from database import SessionLocal, engine

CONTRASENA = "Demo12345"
NO_EMPLEADO = "DEMO-01"
INICIO_CLASES = date(2026, 8, 17)

# (nombre, apellidos, prob. de asistir, prob. de entregar, rango de calificación en %, retraso)
ALUMNOS = [
    ("Ana", "Torres Gómez", 0.98, 1.00, (90, 100), 0.00),
    ("Bruno", "Castillo Peña", 0.96, 1.00, (85, 100), 0.05),
    ("Carla", "Navarro Ibarra", 0.95, 0.95, (80, 95), 0.05),
    ("Diego", "Herrera Luna", 0.94, 0.95, (75, 95), 0.10),
    ("Elena", "Ruiz Vázquez", 0.94, 0.90, (58, 70), 0.10),    # amarillo por calificación
    ("Fernando", "Morales Ortiz", 0.93, 0.95, (72, 90), 0.15),
    ("Gabriela", "Sánchez Díaz", 0.94, 0.95, (70, 88), 0.10),
    ("Héctor", "Ramírez Flores", 0.84, 0.90, (70, 88), 0.20),  # amarillo por asistencia
    ("Iván", "Salas Medina", 0.70, 0.90, (70, 88), 0.20),      # rojo por asistencia
    ("Julia", "Reyes Campos", 0.93, 0.90, (72, 90), 0.25),
    ("Kevin", "Aguilar Rosas", 0.85, 0.85, (60, 72), 0.30),    # amarillo
    ("Laura", "Méndez Silva", 0.93, 0.70, (35, 55), 0.30),     # rojo por calificación
    ("Mario", "Cruz Delgado", 0.65, 0.55, (35, 60), 0.30),     # rojo por las dos
    ("Natalia", "Guzmán Ríos", 0.95, 0.95, (80, 95), 0.00),   # se da de baja a mitad del ciclo
    # Casos de historial y rezago (RF-54 a RF-59); su ingreso y su historial están en HISTORIAL
    ("Oscar", "Valdez Rubio", 0.92, 0.95, (72, 88), 0.10),     # rezago crítico en Programación Estructurada
    ("Paola", "Jiménez Cortés", 0.92, 0.95, (72, 88), 0.10),   # riesgo por historial
    ("Ricardo", "Ponce Lara", 0.92, 0.95, (72, 88), 0.10),     # casos límite: ninguna alerta
]

# Ciclo de ingreso e historial de los alumnos de los casos de riesgo (índice en ALUMNOS).
# Con el plan ICOM: Programación Estructurada es de 2.º semestre y Bases de Datos de 5.º.
# (periodo, materia del catálogo, calificación); 60 o más es aprobada.
HISTORIAL = {
    # Ingresó en 2024-B: hoy (2026-B) va en 5.º y cursa una materia de 2.º -> 3 semestres de desfase,
    # rezago crítico (RF-58). Reprobó la materia en 2025-B, pero en un solo ciclo: sin riesgo por historial.
    14: ("2024-B", [("2024-B", "Fundamentos de la Programación", 81), ("2024-B", "Precálculo", 74),
                    ("2025-A", "Lógica Matemática", 77), ("2025-A", "Fundamentos de Física", 70),
                    ("2025-B", "Programación Estructurada", 48), ("2025-B", "Matemáticas Discretas", 72),
                    ("2026-A", "Cálculo Diferencial e Integral", 68), ("2026-A", "Mecánica", 75)]),
    # Ingresó en 2025-B (va en 3.º): reprobó al menos una materia en 2025-B y en 2026-A,
    # los dos ciclos inmediatamente anteriores -> riesgo por historial (RF-54, RF-55).
    15: ("2025-B", [("2025-B", "Precálculo", 45), ("2025-B", "Lógica Matemática", 78),
                    ("2026-A", "Cálculo Diferencial e Integral", 52), ("2026-A", "Matemáticas Discretas", 71)]),
    # Ingresó en 2025-A (va en 4.º): cursa una materia de 2.º -> 2 semestres de desfase, NO es crítico.
    # Solo reprobó en 2026-A (un ciclo) -> NO hay riesgo por historial.
    16: ("2025-A", [("2025-A", "Fundamentos de la Programación", 80), ("2025-A", "Precálculo", 69),
                    ("2025-B", "Lógica Matemática", 73), ("2025-B", "Fundamentos de Física", 66),
                    ("2026-A", "Mecánica", 55), ("2026-A", "Matemáticas Discretas", 70)]),
}

RETRO_BUENA = ["Excelente trabajo, muy bien explicado.", "Bien hecho; cuida la ortografía.",
               "Muy completo. Sigue así.", "Correcto y bien organizado."]
RETRO_MEDIA = ["Bien, pero faltó justificar algunos pasos.", "Revisa el formato que se pidió.",
               "Cumple lo básico; profundiza en el análisis."]
RETRO_BAJA = ["Incompleto: faltan varias secciones.", "Revisa los ejemplos de clase y pide asesoría.",
              "No cumple con lo solicitado; habla conmigo en clase."]

CURSOS = [
    {
        "datos": dict(nombreMateria="Bases de Datos", seccion="D02", descripcion="Modelado relacional, SQL y normalización.",
                      tipoEvaluacion="numerica", diasSemana=["lunes", "miercoles", "viernes"],
                      horaInicio="08:00", horaFin="10:00"),
        "categorias": [("Tareas", 30), ("Prácticas", 30), ("Exámenes", 40)],
        # (título, categoría, fecha límite, puntos)
        "actividades": [
            ("Tarea 1: diagrama entidad-relación", "Tareas", "2026-09-04T23:59", 10),
            ("Práctica 1: instalar PostgreSQL", "Prácticas", "2026-09-11T23:59", 10),
            ("Tarea 2: modelo relacional", "Tareas", "2026-09-25T23:59", 10),
            ("Parcial 1", "Exámenes", "2026-10-02T10:00", 100),
            ("Práctica 2: consultas SELECT", "Prácticas", "2026-10-16T23:59", 10),
            ("Tarea 3: normalización", "Tareas", "2026-10-30T23:59", 10),
            ("Parcial 2", "Exámenes", "2026-11-13T10:00", 100),
            ("Práctica 3: JOIN y subconsultas", "Prácticas", "2026-11-20T23:59", 10),
            ("Tarea 4: procedimientos almacenados", "Tareas", "2026-12-04T23:59", 10),
            ("Examen final", "Exámenes", "2026-12-11T10:00", 100),
        ],
        "alumnos": list(range(14)) + [15],
    },
    {
        "datos": dict(nombreMateria="Programación Estructurada", seccion="D05", descripcion="Fundamentos de programación en C.",
                      tipoEvaluacion="numerica", diasSemana=["martes", "jueves"],
                      horaInicio="11:00", horaFin="13:00"),
        "categorias": [("Ejercicios", 40), ("Proyecto", 30), ("Exámenes", 30)],
        "actividades": [
            ("Ejercicios: condicionales", "Ejercicios", "2026-09-08T23:59", 10),
            ("Ejercicios: ciclos", "Ejercicios", "2026-09-29T23:59", 10),
            ("Examen parcial", "Exámenes", "2026-10-15T13:00", 100),
            ("Avance del proyecto", "Proyecto", "2026-11-05T23:59", 20),
            ("Ejercicios: arreglos", "Ejercicios", "2026-11-19T23:59", 10),
            ("Entrega final del proyecto", "Proyecto", "2026-12-03T23:59", 20),
        ],
        # mayoría al día, Kevin en amarillo y Laura en rojo; Oscar, Paola y Ricardo son los casos de rezago
        "alumnos": [0, 1, 2, 3, 5, 6, 9, 10, 11, 14, 15, 16],
        "extra_entrega": 0.06,  # pocas actividades: una sola sin entregar pesa mucho
    },
]


def fechas_de_clase(dias: list[str], hasta: date) -> list[date]:
    numero = {d: i for i, d in enumerate(("lunes", "martes", "miercoles", "jueves", "viernes", "sabado"))}
    quiero = {numero[d] for d in dias}
    d, salida = INICIO_CLASES, []
    while d <= hasta:
        if d.weekday() in quiero:
            salida.append(d)
        d += timedelta(days=1)
    return salida


def borrar_demo(db) -> None:
    """Quita solo lo que creó este script: el docente DEMO-01, sus cursos y los alumnos 2190000xx."""
    docente = db.query(models.Docente).filter(models.Docente.noEmpleado == NO_EMPLEADO).first()
    cursos = db.query(models.Curso).filter(models.Curso.docente_id == docente.id).all() if docente else []
    for curso in cursos:
        mats = [m.id for m in db.query(models.Matricula).filter(models.Matricula.curso_id == curso.id)]
        acts = [a.id for a in db.query(models.Actividad).join(models.CategoriaEvaluacion,
                models.CategoriaEvaluacion.id == models.Actividad.categoriaEvaluacion_id)
                .filter(models.CategoriaEvaluacion.curso_id == curso.id)]
        entregas = [e.id for e in db.query(models.Entrega).filter(models.Entrega.actividad_id.in_(acts))]
        db.query(models.Calificacion).filter(models.Calificacion.entrega_id.in_(entregas)).delete(synchronize_session=False)
        db.query(models.Entrega).filter(models.Entrega.id.in_(entregas)).delete(synchronize_session=False)
        db.query(models.Actividad).filter(models.Actividad.id.in_(acts)).delete(synchronize_session=False)
        db.query(models.CategoriaEvaluacion).filter(models.CategoriaEvaluacion.curso_id == curso.id).delete()
        sesiones = [x.id for x in db.query(models.SesionClase).filter(models.SesionClase.curso_id == curso.id)]
        db.query(models.Asistencia).filter(models.Asistencia.sesionClase_id.in_(sesiones)).delete(synchronize_session=False)
        db.query(models.SesionClase).filter(models.SesionClase.curso_id == curso.id).delete()
        db.query(models.RegistroRiesgo).filter(models.RegistroRiesgo.matricula_id.in_(mats)).delete(synchronize_session=False)
        db.query(models.Matricula).filter(models.Matricula.curso_id == curso.id).delete()
        db.delete(curso)
    db.flush()  # los cursos se borran antes que su docente
    ids = [e.id for e in db.query(models.Estudiante).filter(models.Estudiante.codigoEstudiante.like("2190000%"))]
    if docente:
        ids.append(docente.id)
    db.query(models.Matricula).filter(models.Matricula.estudiante_id.in_(ids)).delete(synchronize_session=False)
    db.query(models.HistorialAcademico).filter(models.HistorialAcademico.estudiante_id.in_(ids)).delete(synchronize_session=False)
    db.query(models.SesionActiva).filter(models.SesionActiva.usuario_id.in_(ids)).delete(synchronize_session=False)
    db.execute(models.usuario_rol.delete().where(models.usuario_rol.c.usuario_id.in_(ids)))
    db.query(models.Estudiante).filter(models.Estudiante.id.in_(ids)).delete(synchronize_session=False)
    db.query(models.Docente).filter(models.Docente.id.in_(ids)).delete(synchronize_session=False)
    db.query(models.Usuario).filter(models.Usuario.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    print("Datos de demostración anteriores borrados.")


def main():
    models.Base.metadata.create_all(bind=engine)
    random.seed(2026)
    hoy = date.today()
    with SessionLocal() as db:
        if "--reiniciar" in sys.argv:
            borrar_demo(db)
        if db.query(models.Docente).filter(models.Docente.noEmpleado == NO_EMPLEADO).first():
            print("Los datos de demostración ya existen; no se creó nada.")
            return
        ciclo = db.query(models.CicloEscolar).filter(models.CicloEscolar.nombreOficial == "2026-B").first()
        if not ciclo:
            print("No existe el ciclo 2026-B; créalo antes desde el panel del administrador.")
            return
        carrera = db.query(models.Carrera).first()

        docente = services.crear_docente(db, schemas.DocenteCrear(
            nombre="Rosa", apellidos="Demostración López", correoInstitucional="rosa.demo@academicos.udg.mx",
            contrasena=CONTRASENA, noEmpleado=NO_EMPLEADO, departamento="Ciencias Computacionales"))

        alumnos = []
        for i, (nombre, apellidos, *_resto) in enumerate(ALUMNOS, start=1):
            usuario = services.registrarse(db, schemas.UsuarioCrear(
                nombre=nombre, apellidos=apellidos,
                correoInstitucional=f"{nombre.lower()}.demo{i}@alumnos.udg.mx",
                codigo=f"2190000{i:02d}", carrera=carrera.clave, ciclo=ciclo.nombreOficial,
                contrasena=CONTRASENA, confirmarContrasena=CONTRASENA))
            alumnos.append(usuario)

        # RF-53 a RF-59: ciclo de ingreso anterior, su plan de estudios y su historial
        materias = {m.nombre: m.id for m in db.query(models.Materia)}
        for idx, (ingreso, historial) in HISTORIAL.items():
            est = db.get(models.Estudiante, alumnos[idx].id)
            est.ciclo = ingreso
            malla = services.malla_para(db, est.carrera, ingreso)
            est.mallaCurricular_id = malla.id if malla else None
            for periodo, materia, calif in historial:
                db.add(models.HistorialAcademico(periodo=periodo, materia=materia, calificacion=calif,
                                                 resultado="aprobada" if calif >= 60 else "reprobada",
                                                 estudiante_id=est.id, materia_id=materias.get(materia)))
        db.commit()

        for plan in CURSOS:
            curso = services.crearCurso(db, docente, schemas.CursoCrear(cicloEscolar_id=ciclo.id, **plan["datos"]))
            cats = {}
            for nombre, peso in plan["categorias"]:
                c = models.CategoriaEvaluacion(nombre=nombre, porcentajePeso=peso, curso_id=curso.id)
                db.add(c)
                db.flush()
                cats[nombre] = c.id

            matriculas = {}
            for idx in plan["alumnos"]:
                services.inscribirseCurso(db, alumnos[idx], curso.codigoCurso)
                m = (db.query(models.Matricula)
                     .filter(models.Matricula.curso_id == curso.id, models.Matricula.estudiante_id == alumnos[idx].id).one())
                m.fechaInscripcion = INICIO_CLASES.isoformat()
                matriculas[idx] = m
            baja = matriculas.get(13)
            if baja:
                baja.estado = "baja"

            # Asistencia: todas las clases desde el 17 de agosto hasta ayer, con la lista guardada
            for f in fechas_de_clase(plan["datos"]["diasSemana"], hoy - timedelta(days=1)):
                sesion = models.SesionClase(fecha=f.isoformat(), horaInicio=plan["datos"]["horaInicio"],
                                            horaFin=plan["datos"]["horaFin"], listaGuardada=1, curso_id=curso.id)
                db.add(sesion)
                db.flush()
                for idx, m in matriculas.items():
                    if idx == 13 and f > date(2026, 10, 1):
                        continue  # la baja ya no aparece en las listas posteriores
                    prob = ALUMNOS[idx][2]
                    r = random.random()
                    estado = "asistencia" if r < prob - 0.05 else "retardo" if r < prob else "falta"
                    obs = "Llegó 15 minutos tarde" if estado == "retardo" and random.random() < 0.3 else None
                    db.add(models.Asistencia(estado=estado, observaciones=obs, sesionClase_id=sesion.id, matricula_id=m.id))

            # Actividades, entregas y calificaciones
            # "Por calificar": el docente aún no revisa la mayoría de la última actividad vencida,
            # parte de la penúltima y alguna entrega suelta de antes.
            vencidas = sorted((l for _, _, l, _ in plan["actividades"] if datetime.fromisoformat(l).date() < hoy), reverse=True)
            sin_revisar = {l: p for l, p in zip(vencidas, (0.7, 0.4))}
            for titulo, cat, limite, puntos in plan["actividades"]:
                act = models.Actividad(titulo=titulo, descripcion=f"Instrucciones de «{titulo}». Sube tu archivo en PDF.",
                                       fechaHoraLimite=limite, puntuacionMaxima=puntos, categoriaEvaluacion_id=cats[cat])
                db.add(act)
                db.flush()
                fecha_limite = datetime.fromisoformat(limite)
                ya_vencio = fecha_limite.date() < hoy
                for idx, m in matriculas.items():
                    if idx == 13 and fecha_limite.date() > date(2026, 10, 1):
                        continue
                    _, _, _, p_entrega, (cmin, cmax), p_retraso = ALUMNOS[idx]
                    if not ya_vencio:
                        if random.random() < 0.25 * p_entrega:  # algunos adelantan la próxima entrega
                            db.add(models.Entrega(fechaHoraEntrega=(datetime.now() - timedelta(hours=random.randint(2, 48))).isoformat(timespec="seconds"),
                                                  archivoDigital=None, entregadoConRetraso=0, actividad_id=act.id, matricula_id=m.id))
                        continue
                    # a exámenes y proyectos casi todos cumplen; las tareas son las que se quedan sin entregar
                    p = min(1.0, p_entrega + plan.get("extra_entrega", 0))
                    p = max(p, 0.97) if cat in ("Exámenes", "Proyecto") and p_entrega >= 0.7 else p
                    if random.random() > p:
                        continue  # no entregó: cuenta como 0 al vencer
                    tarde = cat != "Exámenes" and random.random() < p_retraso  # un examen no se entrega tarde
                    momento = fecha_limite + (timedelta(hours=random.randint(3, 60)) if tarde else -timedelta(hours=random.randint(1, 72)))
                    entrega = models.Entrega(fechaHoraEntrega=momento.isoformat(timespec="seconds"), archivoDigital=None,
                                             entregadoConRetraso=int(tarde), actividad_id=act.id, matricula_id=m.id)
                    db.add(entrega)
                    db.flush()
                    if random.random() < sin_revisar.get(limite, 0.05):
                        continue
                    porcentaje = random.uniform(cmin, cmax)
                    nota = round(puntos * porcentaje / 100 * 2) / 2
                    retro = random.choice(RETRO_BUENA if porcentaje >= 80 else RETRO_MEDIA if porcentaje >= 60 else RETRO_BAJA)
                    db.add(models.Calificacion(calificacionObtenida=min(nota, puntos), retroalimentacion=retro,
                                               fecha=(momento + timedelta(days=3)).isoformat(timespec="seconds"),
                                               entrega_id=entrega.id))
            db.commit()
            services.recalcular_acumuladas(db, curso.id)
            db.commit()
            print(f"Curso {curso.nombreMateria} {curso.seccion}: código {curso.codigoCurso}, {len(matriculas)} alumnos")

        services.analizar_riesgo_ciclo(db)  # RF-53: lo mismo que hace el servidor al arrancar
        print("Listo. Credenciales al inicio de sembrar_demo.py.")


if __name__ == "__main__":
    main()
