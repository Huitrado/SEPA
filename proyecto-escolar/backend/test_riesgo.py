"""Historial académico y riesgo (RF-53 a RF-59, RF-84). Hoy es el 25/oct/2026 (ciclo 2026-B)."""
from datetime import datetime

import pytest

import models
import services
from config import fechas_ciclo
from helpers import ALUMNO, ALUMNO_B, CURSO, Sesion, alta_alumno, alta_docente, auth, crear_admin

PDF = ("tarea.pdf", b"%PDF-1.4", "application/pdf")

@pytest.fixture()
def plan(client, monkeypatch, tmp_path):
    """Plan INFO con Programación (1.er semestre) y Bases de datos (3.er semestre), un docente y el admin."""
    monkeypatch.setattr(services, "ahora", lambda: datetime(2026, 10, 25, 12, 0))
    monkeypatch.setattr(services, "CARPETA_ARCHIVOS", tmp_path)
    with Sesion() as db:
        malla = models.MallaCurricular(carrera="INFO", generacion="2023", nombrePlan="Plan INFO 2023")
        programacion = models.Materia(clave="I5000", nombre="Programación")
        bd = models.Materia(clave="I5288", nombre="Bases de datos")
        db.add_all([malla, programacion, bd])
        db.flush()
        db.add_all([models.MallaMateria(mallaCurricular_id=malla.id, materia_id=programacion.id, semestreBase=1),
                    models.MallaMateria(mallaCurricular_id=malla.id, materia_id=bd.id, semestreBase=3)])
        db.commit()
        ids = {"malla": malla.id, "bd": bd.id, "programacion": programacion.id}
    ta = crear_admin(client)
    t1 = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    return {"ta": ta, "t1": t1, **ids}

def _alumno(client, datos=ALUMNO, ingreso="2024-A"):
    t = alta_alumno(client, {**datos, "ciclo": ingreso})
    with Sesion() as db:
        e = db.query(models.Estudiante).filter_by(codigoEstudiante=datos["codigo"]).one()
        return t, e.id

def _curso_pasado(ciclo, materia, alumnos: dict, docente_id=None):
    """Curso de un ciclo ya cerrado con una actividad de 10 puntos. alumnos = {estudiante_id: nota o None}."""
    with Sesion() as db:
        c = db.query(models.CicloEscolar).filter_by(nombreOficial=ciclo).first()
        if not c:
            inicio, fin = fechas_ciclo(ciclo)
            c = models.CicloEscolar(nombreOficial=ciclo, fechaInicio=inicio.isoformat(), fechaTermino=fin.isoformat(), estado="cerrado")
            db.add(c)
            db.flush()
        curso = models.Curso(nombreMateria=materia, seccion="D01", codigoCurso=f"P{c.id}{materia[:3].upper()}{len(alumnos)}",
                             estado="activo", tipoEvaluacion="numerica", umbralNumerico=60, diasSemana="lunes",
                             horaInicio="08:00", horaFin="10:00", cicloEscolar_id=c.id, docente_id=docente_id,
                             materia_id=services._id_materia(db, materia))
        db.add(curso)
        db.flush()
        cat = models.CategoriaEvaluacion(nombre="Todo", porcentajePeso=100, curso_id=curso.id)
        db.add(cat)
        db.flush()
        act = models.Actividad(titulo="Final", fechaHoraLimite=f"{c.fechaTermino}T08:00:00", puntuacionMaxima=10,
                               categoriaEvaluacion_id=cat.id)
        db.add(act)
        db.flush()
        for estudiante_id, nota in alumnos.items():
            m = models.Matricula(curso_id=curso.id, estudiante_id=estudiante_id, fechaInscripcion=c.fechaInicio, estado="activo")
            db.add(m)
            db.flush()
            if nota is not None:
                e = models.Entrega(actividad_id=act.id, matricula_id=m.id, fechaHoraEntrega=c.fechaInicio, entregadoConRetraso=0)
                db.add(e)
                db.flush()
                db.add(models.Calificacion(entrega_id=e.id, calificacionObtenida=nota, fecha=c.fechaTermino))
        db.commit()
        return curso.id

def _cerrar():
    with Sesion() as db:
        return services.cerrar_ciclos_terminados(db)

def _curso_actual(client, plan, t_alumno, **cambios):
    c = client.post("/cursos", json={**CURSO, **cambios}, headers=auth(plan["t1"])).json()
    client.post("/inscripcion", json={"codigoCurso": c["codigoCurso"]}, headers=auth(t_alumno))
    return c

# ------------------------------------------------------------------ reglas (funciones puras)
@pytest.mark.parametrize("ingreso, vigente, semestre", [
    ("2023-B", "2026-B", 7), ("2026-B", "2026-B", 1), ("2026-A", "2026-B", 2), ("2024-A", "2026-B", 6),
    (None, "2026-B", None), ("26-B", "2026-B", None),
])
def test_rf57_semestre_cronologico(ingreso, vigente, semestre):
    assert services.semestre_cronologico(ingreso, vigente) == semestre

def test_ciclos_anteriores():
    assert services.ciclos_anteriores("2026-B", 2) == ["2026-A", "2025-B"]
    assert services.ciclos_anteriores("2026-A", 2) == ["2025-B", "2025-A"]

@pytest.mark.parametrize("acumulada, estatus, resultado", [
    (60, "Ordinario", "aprobada"), (59.99, "Ordinario", "reprobada"),
    (95, "Sin Derecho", "reprobada"), (60, "Extraordinario", "aprobada"),
])
def test_resultado_final_por_calificacion_y_asistencia(acumulada, estatus, resultado):
    assert services.resultado_final(acumulada, estatus) == resultado

# ------------------------------------------------------------------ vínculos con el plan de estudios
def test_rf56_el_alumno_y_el_curso_quedan_ligados_al_plan(client, plan):
    t, eid = _alumno(client)
    c = _curso_actual(client, plan, t, nombreMateria="bases de datos")
    with Sesion() as db:
        assert db.get(models.Estudiante, eid).mallaCurricular_id == plan["malla"]
        assert db.get(models.Curso, c["id"]).materia_id == plan["bd"]

# ------------------------------------------------------------------ RF-53: los ciclos cerrados pasan al historial
def test_rf53_cierre_de_ciclo_al_historial(client, plan):
    ta, ana = _alumno(client)
    tb, beto = _alumno(client, ALUMNO_B)
    _curso_pasado("2026-A", "Programación", {ana: 8, beto: 5})
    assert _cerrar() == 2
    assert _cerrar() == 0  # no se duplica
    r = client.get("/alumno/historial", headers=auth(ta))
    assert r.status_code == 200
    assert [(h["periodo"], h["materia"], h["calificacion"], h["resultado"]) for h in r.json()] == \
           [("2026-A", "Programación", 80, "aprobada")]
    assert client.get("/alumno/historial", headers=auth(tb)).json()[0]["resultado"] == "reprobada"

def test_rf53_sin_derecho_por_asistencia_reprueba(client, plan):
    ta, ana = _alumno(client)
    curso_id = _curso_pasado("2026-A", "Programación", {ana: 10})
    with Sesion() as db:
        m = db.query(models.Matricula).filter_by(curso_id=curso_id).one()
        s = models.SesionClase(curso_id=curso_id, fecha="2026-02-02", horaInicio="08:00", horaFin="10:00", listaGuardada=1)
        db.add(s)
        db.flush()
        db.add(models.Asistencia(sesionClase_id=s.id, matricula_id=m.id, estado="falta"))
        db.commit()
    _cerrar()
    [h] = client.get("/alumno/historial", headers=auth(ta)).json()
    assert (h["calificacion"], h["resultado"]) == (100, "reprobada")

def test_rf53_ciclo_vigente_y_alumnos_de_baja_no_pasan(client, plan):
    ta, ana = _alumno(client)
    tb, beto = _alumno(client, ALUMNO_B)
    _curso_actual(client, plan, ta)
    curso_id = _curso_pasado("2026-A", "Programación", {beto: 9})
    with Sesion() as db:
        db.query(models.Matricula).filter_by(curso_id=curso_id).one().estado = "baja"
        db.commit()
    assert _cerrar() == 0

# ------------------------------------------------------------------ RF-54, RF-55: riesgo por historial
def test_rf54_reprobo_en_los_dos_ciclos_anteriores(client, plan):
    ta, ana = _alumno(client)
    _curso_pasado("2026-A", "Programación", {ana: 2})
    _curso_pasado("2025-B", "Bases de datos", {ana: 4})
    _cerrar()
    r = client.get("/alumno/riesgo", headers=auth(ta)).json()
    assert (r["riesgoPorHistorial"], r["ciclosConReprobadas"]) == (True, ["2026-A", "2025-B"])

def test_rf54_un_solo_ciclo_con_reprobadas_no_basta(client, plan):
    ta, ana = _alumno(client)
    _curso_pasado("2026-A", "Programación", {ana: 2})
    _curso_pasado("2025-B", "Bases de datos", {ana: 9})
    _cerrar()
    r = client.get("/alumno/riesgo", headers=auth(ta)).json()
    assert (r["riesgoPorHistorial"], r["ciclosConReprobadas"]) == (False, [])

# ------------------------------------------------------------------ RF-56 a RF-59: rezago
def test_rf58_rf59_rezago_critico_con_detalle(client, plan):
    ta, _ = _alumno(client, ingreso="2024-A")  # va en 6.º semestre
    c = _curso_actual(client, plan, ta)        # "Bases de datos" es de 3.er semestre
    r = client.get("/alumno/riesgo", headers=auth(ta)).json()
    assert (r["semestreActual"], r["plan"]) == (6, "Plan INFO 2023")
    [curso] = r["cursos"]
    assert (curso["curso_id"], curso["semestreBase"], curso["desfase"], curso["rezagoCritico"]) == (c["id"], 3, 3, True)
    assert curso["detalleRezago"] == "Bases de datos corresponde al 3.º semestre de tu plan y vas en 6.º: 3 semestres de desfase."

def test_rf57_desfase_menor_no_es_critico(client, plan):
    ta, _ = _alumno(client, ingreso="2025-A")  # 4.º semestre
    _curso_actual(client, plan, ta)
    [curso] = client.get("/alumno/riesgo", headers=auth(ta)).json()["cursos"]
    assert (curso["desfase"], curso["rezagoCritico"], curso["detalleRezago"]) == (1, False, None)

def test_rf56_materia_fuera_del_plan(client, plan):
    ta, _ = _alumno(client)
    _curso_actual(client, plan, ta, nombreMateria="Optativa libre")
    [curso] = client.get("/alumno/riesgo", headers=auth(ta)).json()["cursos"]
    assert (curso["semestreBase"], curso["desfase"], curso["rezagoCritico"]) == (None, None, False)

# ------------------------------------------------------------------ RF-84: artículos 33 a 35
def test_rf84_reprobada_antes_y_hoy_en_rojo(client, plan):
    ta, ana = _alumno(client, ingreso="2025-B")
    _curso_pasado("2026-A", "Bases de datos", {ana: 3})
    _cerrar()
    c = _curso_actual(client, plan, ta)
    [curso] = client.get("/alumno/riesgo", headers=auth(ta)).json()["cursos"]
    assert (curso["reprobadaAntes"], curso["alertaArticulos"]) == (True, False)  # aún en verde
    # Calificación baja en el curso actual: semáforo rojo
    base = f"/docente/cursos/{c['id']}"
    cat = client.post(f"{base}/categorias", json={"nombre": "Todo", "porcentajePeso": 100}, headers=auth(plan["t1"])).json()["categoria"]["id"]
    act = client.post(f"{base}/actividades", headers=auth(plan["t1"]), json={
        "categoriaEvaluacion_id": cat, "titulo": "T1", "fechaHoraLimite": "2026-11-01T23:59", "puntuacionMaxima": 10}).json()["id"]
    eid = client.post(f"/alumno/actividades/{act}/entrega", files={"archivo": PDF}, headers=auth(ta)).json()["entrega"]["id"]
    client.put(f"{base}/entregas/{eid}/calificacion", json={"calificacionObtenida": 3}, headers=auth(plan["t1"]))
    [curso] = client.get("/alumno/riesgo", headers=auth(ta)).json()["cursos"]
    assert curso["alertaArticulos"] is True
    # El docente ve las mismas banderas en su seguimiento
    [fila] = client.get(f"{base}/seguimiento", headers=auth(plan["t1"])).json()["alumnos"]
    assert (fila["reprobadaAntes"], fila["alertaArticulos"], fila["semaforoGeneral"]) == (True, True, "rojo")

def test_el_docente_ve_rezago_e_historial(client, plan):
    ta, ana = _alumno(client, ingreso="2024-A")
    _curso_pasado("2026-A", "Programación", {ana: 2})
    _curso_pasado("2025-B", "Programación", {ana: 2})
    _cerrar()
    c = _curso_actual(client, plan, ta)
    [fila] = client.get(f"/docente/cursos/{c['id']}/seguimiento", headers=auth(plan["t1"])).json()["alumnos"]
    assert (fila["riesgoPorHistorial"], fila["rezagoCritico"]) == (True, True)
    assert fila["detalleRezago"].startswith("Bases de datos corresponde al 3.º semestre")

# ------------------------------------------------------------------ análisis en segundo plano y administrador
def test_rf53_el_analisis_guarda_registro_de_riesgo(client, plan):
    ta, ana = _alumno(client, ingreso="2024-A")
    _curso_pasado("2026-A", "Programación", {ana: 2})
    _curso_pasado("2025-B", "Programación", {ana: 2})
    _curso_actual(client, plan, ta)
    with Sesion() as db:
        assert services.analizar_riesgo_ciclo(db) == 1
        [registro] = db.query(models.RegistroRiesgo).all()
        assert (registro.riesgoPorHistorial, registro.riesgoCritico, registro.semaforo) == (1, 1, "rojo")
        assert db.query(models.HistorialAcademico).count() == 2  # también cerró los ciclos pasados
        assert services.analizar_riesgo_ciclo(db) == 1
        assert db.query(models.RegistroRiesgo).count() == 1  # se actualiza, no se duplica

def test_el_administrador_lanza_el_analisis(client, plan):
    r = client.post("/admin/riesgo/recalcular", headers=auth(plan["ta"]))
    assert r.status_code == 202
    assert client.post("/admin/riesgo/recalcular", headers=auth(plan["t1"])).status_code == 403

def test_el_administrador_mantiene_los_planes(client, plan):
    ta = plan["ta"]
    [malla] = client.get("/admin/mallas", headers=auth(ta)).json()
    assert [(m["nombre"], m["semestreBase"]) for m in malla["materias"]] == [("Programación", 1), ("Bases de datos", 3)]
    url = f"/admin/mallas/{malla['id']}/materias"
    assert client.put(url, json={"materia_id": plan["bd"], "semestreBase": 4}, headers=auth(ta)).status_code == 204
    assert client.delete(f"{url}/{plan['programacion']}", headers=auth(ta)).status_code == 204
    [malla] = client.get("/admin/mallas", headers=auth(ta)).json()
    assert [(m["nombre"], m["semestreBase"]) for m in malla["materias"]] == [("Bases de datos", 4)]
    assert client.delete(f"{url}/{plan['programacion']}", headers=auth(ta)).status_code == 404
    assert client.put("/admin/mallas/999/materias", json={"materia_id": plan["bd"], "semestreBase": 1}, headers=auth(ta)).status_code == 404
    assert client.put(url, json={"materia_id": plan["bd"], "semestreBase": 0}, headers=auth(ta)).status_code == 422
    assert client.get("/admin/mallas", headers=auth(plan["t1"])).status_code == 403

# ------------------------------------------------------------------ RF-56: el administrador crea planes de estudio
def _nuevo_plan(client, plan, **cambios):
    datos = {"carrera": "INFO", "generacion": "2026-A", "nombrePlan": "Plan INFO 2026", **cambios}
    return client.post("/admin/mallas", json=datos, headers=auth(plan["ta"]))

def test_rf56_crear_plan_vacio(client, plan):
    r = _nuevo_plan(client, plan, carrera="info", generacion="2026-b")  # se normaliza a mayúsculas
    assert r.status_code == 201, r.text
    nuevo = r.json()
    assert (nuevo["carrera"], nuevo["generacion"], nuevo["nombrePlan"], nuevo["materias"]) == ("INFO", "2026-B", "Plan INFO 2026", [])
    assert len(client.get("/admin/mallas", headers=auth(plan["ta"])).json()) == 2

def test_rf56_crear_plan_copiando_otro(client, plan):
    nuevo = _nuevo_plan(client, plan, copiarDe=plan["malla"]).json()
    assert [(m["nombre"], m["semestreBase"]) for m in nuevo["materias"]] == [("Programación", 1), ("Bases de datos", 3)]
    # son copias: cambiar el plan nuevo no toca el original
    client.put(f"/admin/mallas/{nuevo['id']}/materias", json={"materia_id": plan["bd"], "semestreBase": 5}, headers=auth(plan["ta"]))
    original = next(m for m in client.get("/admin/mallas", headers=auth(plan["ta"])).json() if m["id"] == plan["malla"])
    assert [m["semestreBase"] for m in original["materias"]] == [1, 3]

def test_rf56_los_alumnos_pasan_al_plan_de_su_generacion(client, plan):
    t_ana, ana = _alumno(client, ALUMNO, "2024-A")      # entró antes del plan nuevo: se queda en el de 2023
    t_beto, beto = _alumno(client, ALUMNO_B, "2026-B")  # entró después: pasa al plan 2026-A
    r = _nuevo_plan(client, plan, copiarDe=plan["malla"])
    assert r.json()["alumnosReasignados"] == 1
    with Sesion() as db:
        assert db.get(models.Estudiante, ana).mallaCurricular_id == plan["malla"]
        assert db.get(models.Estudiante, beto).mallaCurricular_id == r.json()["id"]
    assert client.get("/alumno/riesgo", headers=auth(t_beto)).json()["plan"] == "Plan INFO 2026"

def test_rf56_validaciones_al_crear_plan(client, plan):
    r = _nuevo_plan(client, plan, generacion="2023-A")  # el plan de la fixture es "2023" = 2023-A
    assert r.status_code == 409
    assert r.json()["detail"] == "Ya existe un plan de INFO para la generación 2023-A: Plan INFO 2023"
    r = _nuevo_plan(client, plan, generacion="2026")
    assert r.status_code == 422
    assert r.json()["errores"][0]["mensaje"] == "La generación debe tener el formato AAAA-A o AAAA-B (por ejemplo 2026-B)"
    r = _nuevo_plan(client, plan, carrera="XYZ")
    assert (r.status_code, r.json()["detail"]) == (422, "La carrera seleccionada no pertenece al catálogo oficial")
    assert _nuevo_plan(client, plan, copiarDe=999).status_code == 404
    assert _nuevo_plan(client, plan, nombrePlan="").status_code == 422
    r = client.post("/admin/mallas", json={"carrera": "INFO", "generacion": "2026-B", "nombrePlan": "X"}, headers=auth(plan["t1"]))
    assert r.status_code == 403
