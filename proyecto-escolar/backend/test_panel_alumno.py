"""Panel del estudiante (RF-60, RF-61, RF-63, RF-68)."""
from datetime import datetime

import pytest

import services
from helpers import ALUMNO, ALUMNO_B, CURSO, alta_alumno, alta_docente, auth, crear_admin

PDF = ("tarea.pdf", b"%PDF-1.4", "application/pdf")

@pytest.fixture()
def curso(client, monkeypatch, tmp_path):
    """Curso de la docente "Doc Ente" en el ciclo vigente 2026-B, con Tareas 100 % (T1 vence el 1/nov) y Ana inscrita."""
    monkeypatch.setattr(services, "ahora", lambda: datetime(2026, 10, 25, 12, 0))
    monkeypatch.setattr(services, "CARPETA_ARCHIVOS", tmp_path)
    ta = crear_admin(client)
    t1 = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    c = client.post("/cursos", json=CURSO, headers=auth(t1)).json()
    base = f"/docente/cursos/{c['id']}"
    cat = client.post(f"{base}/categorias", json={"nombre": "Tareas", "porcentajePeso": 100},
                      headers=auth(t1)).json()["categoria"]["id"]
    act = client.post(f"{base}/actividades", headers=auth(t1), json={
        "categoriaEvaluacion_id": cat, "titulo": "T1", "fechaHoraLimite": "2026-11-01T23:59",
        "puntuacionMaxima": 10}).json()["id"]
    ana = alta_alumno(client, ALUMNO)
    client.post("/inscripcion", json={"codigoCurso": c["codigoCurso"]}, headers=auth(ana))
    return {"ta": ta, "t1": t1, "id": c["id"], "base": base, "act": act, "ana": ana, "codigo": c["codigoCurso"]}

# ------------------------------------------------------------------ RF-60 / RF-61: tarjetas de cursos
def test_rf60_rf61_tarjeta_con_profesor_y_semaforo(client, curso):
    r = client.get("/alumno/cursos", headers=auth(curso["ana"]))
    assert r.status_code == 200, r.text
    [tarjeta] = r.json()
    assert (tarjeta["nombreMateria"], tarjeta["profesor"], tarjeta["ciclo"]) == ("Bases de datos", "Doc Ente", "2026-B")
    assert (tarjeta["semaforoGeneral"], tarjeta["porcentajeAsistencia"], tarjeta["calificacionAcumulada"]) == ("verde", 100, 0)
    assert "codigoCurso" not in tarjeta

def test_rf60_solo_cursos_del_ciclo_activo(client, curso):
    ciclo = client.post("/admin/ciclos", json={"nombreOficial": "2027-A"}, headers=auth(curso["ta"])).json()
    proximo = client.post("/cursos", json={**CURSO, "cicloEscolar_id": ciclo["id"]}, headers=auth(curso["t1"])).json()
    client.post("/inscripcion", json={"codigoCurso": proximo["codigoCurso"]}, headers=auth(curso["ana"]))
    assert [c["id"] for c in client.get("/alumno/cursos", headers=auth(curso["ana"])).json()] == [curso["id"]]

def test_rf61_la_tarjeta_refleja_el_riesgo(client, curso):
    eid = client.post(f"/alumno/actividades/{curso['act']}/entrega", files={"archivo": PDF},
                      headers=auth(curso["ana"])).json()["entrega"]["id"]
    client.put(f"{curso['base']}/entregas/{eid}/calificacion", json={"calificacionObtenida": 4}, headers=auth(curso["t1"]))
    [tarjeta] = client.get("/alumno/cursos", headers=auth(curso["ana"])).json()
    assert (tarjeta["semaforoGeneral"], tarjeta["alertaCalificacion"], tarjeta["calificacionAcumulada"]) == ("rojo", True, 40)

def test_rf62_ficha_de_un_curso(client, curso):
    r = client.get(f"/alumno/cursos/{curso['id']}", headers=auth(curso["ana"]))
    assert r.status_code == 200
    assert (r.json()["id"], r.json()["profesor"]) == (curso["id"], "Doc Ente")
    beto = alta_alumno(client, ALUMNO_B)
    assert client.get(f"/alumno/cursos/{curso['id']}", headers=auth(beto)).status_code == 403
    assert client.get("/alumno/cursos/999", headers=auth(curso["ana"])).status_code == 404

# ------------------------------------------------------------------ RF-63: encuadre visible para el alumno
def test_rf63_el_alumno_ve_el_encuadre(client, curso):
    r = client.get(f"/alumno/cursos/{curso['id']}/encuadre", headers=auth(curso["ana"]))
    assert r.status_code == 200, r.text
    assert [(c["nombre"], c["porcentajePeso"]) for c in r.json()["categorias"]] == [("Tareas", 100)]
    assert r.json()["pesosCompletos"] is True
    beto = alta_alumno(client, ALUMNO_B)
    assert client.get(f"/alumno/cursos/{curso['id']}/encuadre", headers=auth(beto)).status_code == 403
    assert client.get(f"/alumno/cursos/{curso['id']}/encuadre", headers=auth(curso["t1"])).status_code == 403

# ------------------------------------------------------------------ RF-68: puntos perdidos
def test_rf68_puntos_obtenidos_posibles_y_perdidos(client, curso):
    eid = client.post(f"/alumno/actividades/{curso['act']}/entrega", files={"archivo": PDF},
                      headers=auth(curso["ana"])).json()["entrega"]["id"]
    client.put(f"{curso['base']}/entregas/{eid}/calificacion", json={"calificacionObtenida": 7}, headers=auth(curso["t1"]))
    mias = client.get(f"/alumno/cursos/{curso['id']}/calificaciones", headers=auth(curso["ana"])).json()
    assert (mias["calificacionAcumulada"], mias["puntosPosibles"], mias["puntosPerdidos"]) == (70, 100, 30)
    seg = client.get(f"/alumno/cursos/{curso['id']}/seguimiento", headers=auth(curso["ana"])).json()
    assert seg["puntosPerdidos"] == 30

def test_calculo_de_puntos_perdidos():
    r = services.calcular_calificacion([(20, 10, 8, False), (30, 10, None, True), (50, 10, None, False)])
    assert (r["calificacionAcumulada"], r["puntosPosibles"], r["puntosPerdidos"]) == (16, 50, 34)
