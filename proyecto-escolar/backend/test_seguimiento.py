"""Baja de alumno (RF-16) y seguimiento: alerta por calificación y semáforo (RF-48, RF-49, RF-61)."""
from datetime import date, datetime

import pytest

import services
from helpers import ALUMNO, ALUMNO_B, CURSO, alta_alumno, alta_docente, auth, crear_admin

PDF = ("tarea.pdf", b"%PDF-1.4", "application/pdf")

@pytest.fixture()
def curso(client, monkeypatch, tmp_path):
    """Hoy es lunes 26/oct. Tareas 100 % con T1 y T2 (de 10 puntos, valen 50 cada una); Ana y Beto inscritos."""
    monkeypatch.setattr(services, "hoy", lambda: date(2026, 10, 26))
    monkeypatch.setattr(services, "ahora", lambda: datetime(2026, 10, 26, 12, 0))
    monkeypatch.setattr(services, "CARPETA_ARCHIVOS", tmp_path)
    ta = crear_admin(client)
    t1 = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    t2 = alta_docente(client, ta, "d2@academicos.udg.mx", "D-2")
    c = client.post("/cursos", json=CURSO, headers=auth(t1)).json()
    base = f"/docente/cursos/{c['id']}"
    cat = client.post(f"{base}/categorias", json={"nombre": "Tareas", "porcentajePeso": 100},
                      headers=auth(t1)).json()["categoria"]["id"]
    acts = [client.post(f"{base}/actividades", headers=auth(t1), json={
        "categoriaEvaluacion_id": cat, "titulo": titulo, "fechaHoraLimite": limite,
        "puntuacionMaxima": 10}).json()["id"] for titulo, limite in (("T1", "2026-10-27T23:59"),
                                                                     ("T2", "2026-11-03T23:59"))]
    alumnos = {}
    for nombre, datos in (("ana", ALUMNO), ("beto", ALUMNO_B)):
        alumnos[nombre] = alta_alumno(client, datos)
        client.post("/inscripcion", json={"codigoCurso": c["codigoCurso"]}, headers=auth(alumnos[nombre]))
    matriculas = {a["nombre"]: a["matricula_id"] for a in
                  client.get(f"{base}/alumnos", headers=auth(t1)).json()}
    return {"ta": ta, "t1": t1, "t2": t2, "id": c["id"], "base": base, "acts": acts,
            "m_ana": matriculas["Ana"], "m_beto": matriculas["Beto"], **alumnos}

def _calificar(client, cur, alumno, actividad, nota):
    eid = client.post(f"/alumno/actividades/{actividad}/entrega", files={"archivo": PDF},
                      headers=auth(cur[alumno])).json()["entrega"]["id"]
    r = client.put(f"{cur['base']}/entregas/{eid}/calificacion", json={"calificacionObtenida": nota},
                   headers=auth(cur["t1"]))
    assert r.status_code == 200, r.text

def _seguimiento(client, cur):
    r = client.get(f"{cur['base']}/seguimiento", headers=auth(cur["t1"]))
    assert r.status_code == 200, r.text
    return r.json()

def _de(seg, nombre):
    return next(a for a in seg["alumnos"] if a["nombre"] == nombre)

def _baja(client, cur, matricula, estado="baja", t=None):
    return client.patch(f"{cur['base']}/alumnos/{matricula}/estado", json={"estado": estado},
                        headers=auth(t or cur["t1"]))

# ------------------------------------------------------------------ reglas (funciones reutilizables)
@pytest.mark.parametrize("desempeno, semaforo, alerta", [
    (None, "verde", False), (100, "verde", False), (70, "verde", False),
    (69.99, "amarillo", False), (60, "amarillo", False),
    (59.99, "rojo", True), (0, "rojo", True),
])
def test_rf48_alerta_y_semaforo_por_calificacion(desempeno, semaforo, alerta):
    assert services.semaforo_calificacion(desempeno) == semaforo
    assert services.alerta_calificacion(desempeno) is alerta

@pytest.mark.parametrize("asistencia, calificacion, general", [
    ("verde", "verde", "verde"), ("verde", "amarillo", "amarillo"),
    ("rojo", "verde", "rojo"), ("amarillo", "rojo", "rojo"), ("amarillo", "amarillo", "amarillo"),
])
def test_rf61_el_semaforo_general_es_el_peor(asistencia, calificacion, general):
    assert services.semaforo_general(asistencia, calificacion) == general

# ------------------------------------------------------------------ seguimiento del curso
def test_sin_datos_todos_en_verde(client, curso):
    seg = _seguimiento(client, curso)
    assert seg["resumen"] == {"verde": 2, "amarillo": 0, "rojo": 0}
    ana = _de(seg, "Ana")
    assert (ana["porcentajeAsistencia"], ana["estatusNormativo"], ana["desempenoProporcional"]) == (100, "Ordinario", None)
    assert (ana["alertaCalificacion"], ana["semaforoCalificacion"], ana["semaforoGeneral"]) == (False, "verde", "verde")

def test_rf48_alerta_por_desempeno_proporcional(client, curso):
    _calificar(client, curso, "ana", curso["acts"][0], 5)     # 50 % de lo evaluado
    _calificar(client, curso, "beto", curso["acts"][0], 6.5)  # 65 %
    seg = _seguimiento(client, curso)
    ana, beto = _de(seg, "Ana"), _de(seg, "Beto")
    # Ana lleva 25 de 100 puntos absolutos, pero la alerta usa el desempeño proporcional (50 %)
    assert (ana["calificacionAcumulada"], ana["desempenoProporcional"]) == (25, 50)
    assert (ana["alertaCalificacion"], ana["semaforoCalificacion"], ana["semaforoGeneral"]) == (True, "rojo", "rojo")
    assert (beto["alertaCalificacion"], beto["semaforoCalificacion"], beto["semaforoGeneral"]) == (False, "amarillo", "amarillo")
    assert seg["resumen"] == {"verde": 0, "amarillo": 1, "rojo": 1}

def test_rf61_la_asistencia_puede_poner_el_general_en_rojo(client, curso):
    _calificar(client, curso, "ana", curso["acts"][0], 10)
    sid = client.post(f"{curso['base']}/sesiones", headers=auth(curso["t1"])).json()["id"]
    client.put(f"{curso['base']}/sesiones/{sid}/lista", headers=auth(curso["t1"]), json={"asistencias": [
        {"matricula_id": curso["m_ana"], "estado": "falta"}, {"matricula_id": curso["m_beto"], "estado": "asistencia"}]})
    ana = _de(_seguimiento(client, curso), "Ana")
    assert (ana["porcentajeAsistencia"], ana["estatusNormativo"], ana["semaforoAsistencia"]) == (0, "Sin Derecho", "rojo")
    assert (ana["semaforoCalificacion"], ana["semaforoGeneral"]) == ("verde", "rojo")

def test_el_alumno_ve_su_propio_seguimiento(client, curso):
    _calificar(client, curso, "ana", curso["acts"][0], 5)
    r = client.get(f"/alumno/cursos/{curso['id']}/seguimiento", headers=auth(curso["ana"]))
    assert r.status_code == 200, r.text
    assert (r.json()["curso_id"], r.json()["alertaCalificacion"], r.json()["semaforoGeneral"]) == (curso["id"], True, "rojo")
    carla = alta_alumno(client, {**ALUMNO, "codigo": "111222333", "correoInstitucional": "carla@alumnos.udg.mx"})
    assert client.get(f"/alumno/cursos/{curso['id']}/seguimiento", headers=auth(carla)).status_code == 403

# ------------------------------------------------------------------ RF-16: baja de alumno
def test_rf16_el_alumno_de_baja_desaparece_del_curso(client, curso):
    r = _baja(client, curso, curso["m_beto"])
    assert r.status_code == 200, r.text
    assert (r.json()["nombre"], r.json()["estado"]) == ("Beto", "baja")
    # El listado de matrícula lo sigue mostrando, con su estado
    assert {a["nombre"]: a["estado"] for a in
            client.get(f"{curso['base']}/alumnos", headers=auth(curso["t1"])).json()} == {"Ana": "activo", "Beto": "baja"}
    # Pero ya no aparece en asistencia, calificaciones ni seguimiento
    for ruta in ("asistencia", "calificaciones", "seguimiento"):
        filas = client.get(f"{curso['base']}/{ruta}", headers=auth(curso["t1"])).json()["alumnos"]
        assert [f["nombre"] for f in filas] == ["Ana"], ruta
    # Y él ya no ve el curso ni puede entregar
    assert client.get("/alumno/cursos", headers=auth(curso["beto"])).json() == []
    assert client.get(f"/alumno/cursos/{curso['id']}/seguimiento", headers=auth(curso["beto"])).status_code == 403

def test_rf16_reactivar_a_un_alumno(client, curso):
    _calificar(client, curso, "beto", curso["acts"][0], 10)
    _baja(client, curso, curso["m_beto"])
    r = _baja(client, curso, curso["m_beto"], "activo")
    assert r.status_code == 200
    assert (r.json()["estado"], r.json()["calificacionAcumuladaActual"]) == ("activo", 50)
    assert [f["nombre"] for f in _seguimiento(client, curso)["alumnos"]] == ["Ana", "Beto"]

def test_rf16_validaciones(client, curso):
    otro = client.post("/cursos", json={**CURSO, "seccion": "D02"}, headers=auth(curso["t1"])).json()
    r = client.patch(f"/docente/cursos/{otro['id']}/alumnos/{curso['m_ana']}/estado", json={"estado": "baja"},
                     headers=auth(curso["t1"]))
    assert r.status_code == 404
    assert r.json()["detail"] == "El alumno no está inscrito en este curso"
    assert _baja(client, curso, curso["m_ana"], "expulsado").status_code == 422

# ------------------------------------------------------------------ RF-95: solo el docente creador
def test_rf95_solo_el_docente_creador_da_de_baja_y_ve_el_seguimiento(client, curso):
    for t in (curso["t2"], curso["ta"], curso["ana"]):
        assert _baja(client, curso, curso["m_beto"], t=t).status_code == 403
        assert client.get(f"{curso['base']}/seguimiento", headers=auth(t)).status_code == 403
