"""Módulo de entregas del alumno (RF-37 a RF-39)."""
from datetime import datetime

import pytest

import models
import services
from helpers import ALUMNO, ALUMNO_B, CURSO, Sesion, alta_alumno, alta_docente, auth, crear_admin

LIMITE = datetime(2026, 11, 1, 23, 59)
ANTES = datetime(2026, 10, 25, 12, 0)
DESPUES = datetime(2026, 11, 2, 8, 0)
PDF = ("tarea.pdf", b"%PDF-1.4 mi tarea", "application/pdf")

@pytest.fixture()
def reloj(monkeypatch, tmp_path):
    """Hora actual que cada prueba puede mover; los archivos van a una carpeta temporal."""
    actual = {"ahora": ANTES}
    monkeypatch.setattr(services, "ahora", lambda: actual["ahora"])
    monkeypatch.setattr(services, "CARPETA_ARCHIVOS", tmp_path)
    actual["carpeta"] = tmp_path
    return actual

@pytest.fixture()
def curso(client, reloj):
    """Curso de t1 con la actividad "Tarea 1" (límite 01/nov 23:59); Ana y Beto inscritos."""
    ta = crear_admin(client)
    t1 = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    t2 = alta_docente(client, ta, "d2@academicos.udg.mx", "D-2")
    c = client.post("/cursos", json=CURSO, headers=auth(t1)).json()
    base = f"/docente/cursos/{c['id']}"
    cat = client.post(f"{base}/categorias", json={"nombre": "Tareas", "porcentajePeso": 100},
                      headers=auth(t1)).json()["categoria"]["id"]
    act = client.post(f"{base}/actividades", headers=auth(t1), json={
        "categoriaEvaluacion_id": cat, "titulo": "Tarea 1",
        "fechaHoraLimite": LIMITE.isoformat(), "puntuacionMaxima": 10}).json()
    alumnos = {}
    for nombre, datos in (("ana", ALUMNO), ("beto", ALUMNO_B)):
        alumnos[nombre] = alta_alumno(client, datos)
        client.post("/inscripcion", json={"codigoCurso": c["codigoCurso"]}, headers=auth(alumnos[nombre]))
    return {"ta": ta, "t1": t1, "t2": t2, "id": c["id"], "base": base, "actividad": act["id"], **alumnos}

def _entregar(client, cur, t=None, archivo=PDF, actividad=None):
    return client.post(f"/alumno/actividades/{actividad or cur['actividad']}/entrega",
                       files={"archivo": archivo}, headers=auth(t or cur["ana"]))

def _cancelar(client, cur, t=None):
    return client.delete(f"/alumno/actividades/{cur['actividad']}/entrega", headers=auth(t or cur["ana"]))

def _mi_actividad(client, cur, t=None):
    r = client.get(f"/alumno/cursos/{cur['id']}/actividades", headers=auth(t or cur["ana"]))
    assert r.status_code == 200, r.text
    return r.json()[0]

# ------------------------------------------------------------------ vista del alumno
def test_el_alumno_ve_sus_cursos(client, curso):
    r = client.get("/alumno/cursos", headers=auth(curso["ana"]))
    assert r.status_code == 200
    assert [c["id"] for c in r.json()] == [curso["id"]]
    assert "codigoCurso" not in r.json()[0]
    assert client.get("/alumno/cursos", headers=auth(curso["t1"])).status_code == 403

def test_el_alumno_ve_las_actividades_de_su_curso(client, curso):
    a = _mi_actividad(client, curso)
    assert (a["titulo"], a["valorEnCurso"], a["fechaHoraLimite"]) == ("Tarea 1", 100, "2026-11-01T23:59:00")
    assert (a["estadoEntrega"], a["entrega"], a["puedeCancelar"]) == ("pendiente", None, False)

def test_sin_entrega_despues_de_la_fecha_queda_vencida(client, curso, reloj):
    reloj["ahora"] = DESPUES
    assert _mi_actividad(client, curso)["estadoEntrega"] == "vencida"

# ------------------------------------------------------------------ RF-37: entregar a tiempo
def test_rf37_entregar_a_tiempo_con_hora_del_servidor(client, curso):
    r = _entregar(client, curso)
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["estadoEntrega"] == "entregada" and a["puedeCancelar"] is True
    assert a["entrega"]["fechaHoraEntrega"] == "2026-10-25T12:00:00"
    assert a["entrega"]["entregadoConRetraso"] is False

def test_rf37_justo_en_la_fecha_limite_es_a_tiempo(client, curso, reloj):
    reloj["ahora"] = LIMITE
    assert _entregar(client, curso).json()["entrega"]["entregadoConRetraso"] is False

def test_no_se_entrega_dos_veces(client, curso):
    _entregar(client, curso)
    r = _entregar(client, curso)
    assert r.status_code == 409
    assert r.json()["detail"] == "Ya entregaste esta actividad; cancela tu entrega para volver a subirla"

# ------------------------------------------------------------------ RF-39: entrega tardía
def test_rf39_la_entrega_tardia_se_acepta_marcada(client, curso, reloj):
    reloj["ahora"] = DESPUES
    r = _entregar(client, curso)
    assert r.status_code == 201
    a = r.json()
    assert (a["estadoEntrega"], a["entrega"]["entregadoConRetraso"], a["puedeCancelar"]) == \
           ("entregada_con_retraso", True, False)

# ------------------------------------------------------------------ RF-38: cancelar y volver a subir
def test_rf38_cancelar_y_volver_a_subir_antes_de_la_fecha(client, curso, reloj):
    _entregar(client, curso)
    r = _cancelar(client, curso)
    assert r.status_code == 200
    assert (r.json()["estadoEntrega"], r.json()["entrega"]) == ("pendiente", None)
    assert list(reloj["carpeta"].rglob("*.pdf")) == []  # se borra el archivo
    assert _entregar(client, curso, archivo=("v2.zip", b"PK\x03\x04", "application/zip")).status_code == 201

def test_rf38_no_se_cancela_despues_de_la_fecha(client, curso, reloj):
    _entregar(client, curso)
    reloj["ahora"] = DESPUES
    r = _cancelar(client, curso)
    assert r.status_code == 409
    assert r.json()["detail"] == "Ya pasó la fecha límite; no puedes cancelar tu entrega"
    assert _mi_actividad(client, curso)["estadoEntrega"] == "entregada"

def test_rf38_no_se_cancela_una_entrega_calificada(client, curso):
    _entregar(client, curso)
    with Sesion() as db:
        entrega = db.query(models.Entrega).first()
        db.add(models.Calificacion(entrega_id=entrega.id, calificacionObtenida=9, fecha="2026-10-26"))
        db.commit()
    r = _cancelar(client, curso)
    assert r.status_code == 409
    assert r.json()["detail"] == "Tu entrega ya fue calificada; no puedes cancelarla"

def test_cancelar_sin_haber_entregado(client, curso):
    r = _cancelar(client, curso)
    assert r.status_code == 404
    assert r.json()["detail"] == "No has entregado esta actividad"

# ------------------------------------------------------------------ RNF-8: el archivo
def test_rnf8_la_entrega_valida_el_archivo(client, curso, reloj):
    assert _entregar(client, curso, archivo=("tarea.exe", b"MZ", "application/octet-stream")).status_code == 415
    assert _entregar(client, curso, archivo=("tarea.pdf", b"", "application/pdf")).status_code == 422
    assert client.post(f"/alumno/actividades/{curso['actividad']}/entrega",
                       headers=auth(curso["ana"])).status_code == 422  # sin archivo
    assert list(reloj["carpeta"].rglob("*.*")) == []
    assert _mi_actividad(client, curso)["entrega"] is None

# ------------------------------------------------------------------ quién puede entregar
def test_solo_alumnos_inscritos_y_activos_entregan(client, curso):
    carla = alta_alumno(client, {**ALUMNO, "codigo": "111222333", "nombre": "Carla",
                                 "correoInstitucional": "carla@alumnos.udg.mx"})
    for peticion in (lambda: _entregar(client, curso, t=carla),
                     lambda: client.get(f"/alumno/cursos/{curso['id']}/actividades", headers=auth(carla))):
        r = peticion()
        assert r.status_code == 403
        assert r.json()["detail"] == "No estás inscrito en este curso"
    with Sesion() as db:  # dar de baja a Beto
        db.query(models.Matricula).filter_by(estudiante_id=db.query(models.Estudiante)
                                             .filter_by(codigoEstudiante="987654321").one().id).one().estado = "baja"
        db.commit()
    assert _entregar(client, curso, t=curso["beto"]).status_code == 403
    assert _entregar(client, curso, t=curso["t1"]).status_code == 403  # un docente no es alumno

def test_actividad_o_curso_inexistente(client, curso):
    assert _entregar(client, curso, actividad=999).status_code == 404
    assert client.get("/alumno/cursos/999/actividades", headers=auth(curso["ana"])).status_code == 404

def test_no_se_entrega_en_un_curso_archivado(client, curso):
    client.patch(f"/docente/cursos/{curso['id']}/estado", json={"estado": "archivado"}, headers=auth(curso["t1"]))
    r = _entregar(client, curso)
    assert r.status_code == 409
    assert r.json()["detail"] == "El curso está archivado"

# ------------------------------------------------------------------ vista del docente y descargas
def test_el_docente_ve_las_entregas_de_la_actividad(client, curso, reloj):
    _entregar(client, curso)
    reloj["ahora"] = DESPUES
    r = client.get(f"{curso['base']}/actividades/{curso['actividad']}/entregas", headers=auth(curso["t1"]))
    assert r.status_code == 200, r.text
    assert [(f["nombre"], f["estadoEntrega"]) for f in r.json()] == [("Ana", "entregada"), ("Beto", "vencida")]
    assert r.json()[0]["entrega"]["fechaHoraEntrega"] == "2026-10-25T12:00:00"
    for t in (curso["t2"], curso["ana"]):
        assert client.get(f"{curso['base']}/actividades/{curso['actividad']}/entregas",
                          headers=auth(t)).status_code == 403

def test_descargar_la_entrega(client, curso):
    entrega_id = _entregar(client, curso).json()["entrega"]["id"]
    for t in (curso["ana"], curso["t1"]):
        r = client.get(f"/entregas/{entrega_id}/archivo", headers=auth(t))
        assert r.status_code == 200
        assert r.content == PDF[1]
        assert "123456789_Tarea%201.pdf" in r.headers["content-disposition"]  # nombre codificado (RFC 5987)
    for t in (curso["beto"], curso["t2"], curso["ta"]):
        r = client.get(f"/entregas/{entrega_id}/archivo", headers=auth(t))
        assert r.status_code == 403
        assert r.json()["detail"] == "No tienes acceso a esta entrega"
    assert client.get("/entregas/999/archivo", headers=auth(curso["t1"])).status_code == 404
