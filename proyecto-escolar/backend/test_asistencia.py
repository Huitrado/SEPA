"""Módulo de control de asistencia (RF-19 a RF-28, RF-49)."""
from datetime import date

import pytest

import models
import services
from helpers import (ALUMNO, ALUMNO_B, CURSO, Sesion, alta_alumno, alta_docente, auth,
                     crear_admin)

LUNES = date(2026, 10, 26)       # el curso de ejemplo es lunes y miércoles
MIERCOLES = date(2026, 10, 28)
MARTES = date(2026, 10, 27)

def _fijar_fecha(monkeypatch, fecha):
    monkeypatch.setattr(services, "hoy", lambda: fecha)

@pytest.fixture()
def curso(client, monkeypatch):
    """Curso de t1 (lunes y miércoles, 08:00-10:00) con Ana y Beto inscritos; hoy es lunes."""
    _fijar_fecha(monkeypatch, LUNES)
    ta = crear_admin(client)
    t1 = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    t2 = alta_docente(client, ta, "d2@academicos.udg.mx", "D-2")
    r = client.post("/cursos", json=CURSO, headers=auth(t1))
    assert r.status_code == 201, r.text
    c = r.json()
    alumnos = []
    for datos in (ALUMNO, ALUMNO_B):
        ta_alumno = alta_alumno(client, datos)
        assert client.post("/inscripcion", json={"codigoCurso": c["codigoCurso"]},
                           headers=auth(ta_alumno)).status_code == 201
        alumnos.append(ta_alumno)
    matriculas = [a["matricula_id"] for a in
                  client.get(f"/docente/cursos/{c['id']}/alumnos", headers=auth(t1)).json()]
    return {"ta": ta, "t1": t1, "t2": t2, "id": c["id"], "codigo": c["codigoCurso"],
            "alumnos": alumnos, "ana": matriculas[0], "beto": matriculas[1]}

def _generar(client, cur, **cuerpo):
    return client.post(f"/docente/cursos/{cur['id']}/sesiones", json=cuerpo or None,
                       headers=auth(cur["t1"]))

def _guardar(client, cur, sesion_id, estados: dict, t=None):
    lista = [{"matricula_id": m, "estado": e} for m, e in estados.items()]
    return client.put(f"/docente/cursos/{cur['id']}/sesiones/{sesion_id}/lista",
                      json={"asistencias": lista}, headers=auth(t or cur["t1"]))

def _cuadricula(client, cur):
    r = client.get(f"/docente/cursos/{cur['id']}/asistencia", headers=auth(cur["t1"]))
    assert r.status_code == 200, r.text
    return r.json()

def _clase(client, cur, monkeypatch, fecha, ana, beto):
    """Genera y guarda la lista de una sesión en `fecha`."""
    _fijar_fecha(monkeypatch, fecha)
    r = _generar(client, cur)
    assert r.status_code == 201, r.text
    assert _guardar(client, cur, r.json()["id"], {cur["ana"]: ana, cur["beto"]: beto}).status_code == 200
    return r.json()["id"]

# ------------------------------------------------------------------ RF-19 / RF-27: generar la sesión
def test_rf19_genera_la_sesion_de_hoy_con_el_horario_del_curso(client, curso):
    r = _generar(client, curso, tema="Normalización")
    assert r.status_code == 201, r.text
    s = r.json()
    assert (s["fecha"], s["horaInicio"], s["horaFin"]) == ("2026-10-26", "08:00", "10:00")
    assert s["tema"] == "Normalización" and s["listaGuardada"] is False
    # RF-22: todos los alumnos activos quedan en "pendiente"
    assert [a["estado"] for a in s["alumnos"]] == ["pendiente", "pendiente"]

def test_rf19_el_tema_es_opcional(client, curso):
    r = _generar(client, curso)
    assert r.status_code == 201
    assert r.json()["tema"] is None

@pytest.mark.parametrize("fecha", [MARTES, date(2026, 10, 25)])  # martes y domingo
def test_rf27_solo_en_dias_de_clase(client, curso, monkeypatch, fecha):
    _fijar_fecha(monkeypatch, fecha)
    r = _generar(client, curso)
    assert r.status_code == 409
    assert r.json()["detail"] == "Hoy no es día de clase de este curso"

def test_rf27_no_se_duplica_la_sesion_del_dia(client, curso):
    assert _generar(client, curso).status_code == 201
    r = _generar(client, curso)
    assert r.status_code == 409
    assert r.json()["detail"] == "Ya existe una sesión de este curso para hoy"

def test_rf19_curso_archivado_no_genera_sesiones(client, curso):
    client.patch(f"/docente/cursos/{curso['id']}/estado", json={"estado": "archivado"},
                 headers=auth(curso["t1"]))
    r = _generar(client, curso)
    assert r.status_code == 409
    assert r.json()["detail"] == "El curso está archivado"

def test_rf27_no_hay_sesiones_en_un_ciclo_que_no_ha_empezado(client, curso):
    ciclo = client.post("/admin/ciclos", json={"nombreOficial": "2027-A"}, headers=auth(curso["ta"])).json()
    c = client.post("/cursos", json={**CURSO, "cicloEscolar_id": ciclo["id"]}, headers=auth(curso["t1"])).json()
    r = client.post(f"/docente/cursos/{c['id']}/sesiones", headers=auth(curso["t1"]))
    assert r.status_code == 409
    assert r.json()["detail"] == "El ciclo escolar del curso no está en curso"

# ------------------------------------------------------------------ RF-22: lista pendiente
def test_rf22_una_lista_pendiente_no_cuenta(client, curso):
    _generar(client, curso)
    g = _cuadricula(client, curso)
    assert g["sesiones"][0]["listaGuardada"] is False
    fila = g["alumnos"][0]
    assert fila["estados"][0]["estado"] == "pendiente"
    assert (fila["porcentajeAsistencia"], fila["estatusNormativo"], fila["semaforo"]) == (100, "Ordinario", "verde")

# ------------------------------------------------------------------ RF-20 / RF-23: guardar la lista
def test_rf20_rf23_guardar_lista(client, curso):
    sid = _generar(client, curso).json()["id"]
    r = client.put(f"/docente/cursos/{curso['id']}/sesiones/{sid}/lista", headers=auth(curso["t1"]), json={
        "asistencias": [{"matricula_id": curso["ana"], "estado": "retardo", "observaciones": "Llegó 08:20"},
                        {"matricula_id": curso["beto"], "estado": "falta"}]})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["listaGuardada"] is True
    assert [(a["estado"], a["observaciones"]) for a in s["alumnos"]] == [("retardo", "Llegó 08:20"), ("falta", None)]

def test_rf23_validaciones_de_la_lista(client, curso):
    sid = _generar(client, curso).json()["id"]
    url = f"/docente/cursos/{curso['id']}/sesiones/{sid}/lista"

    r = _guardar(client, curso, sid, {curso["ana"]: "asistencia"})  # falta Beto
    assert r.status_code == 422
    assert r.json()["detail"].startswith("Falta el estado de algunos alumnos")

    r = _guardar(client, curso, sid, {curso["ana"]: "asistencia", curso["beto"]: "falta", 999: "falta"})
    assert r.status_code == 422
    assert r.json()["detail"].startswith("Hay alumnos que no pertenecen a este curso")

    repetida = [{"matricula_id": curso["ana"], "estado": "falta"}] * 2
    assert client.put(url, json={"asistencias": repetida}, headers=auth(curso["t1"])).status_code == 422

    r = _guardar(client, curso, sid, {curso["ana"]: "justificada", curso["beto"]: "falta"})
    assert r.status_code == 422

def test_rf23_no_acepta_matriculas_de_otro_curso(client, curso):
    otro = client.post("/cursos", json={**CURSO, "seccion": "D02"}, headers=auth(curso["t1"])).json()
    client.post("/inscripcion", json={"codigoCurso": otro["codigoCurso"]}, headers=auth(curso["alumnos"][0]))
    ajena = client.get(f"/docente/cursos/{otro['id']}/alumnos", headers=auth(curso["t1"])).json()[0]["matricula_id"]
    sid = _generar(client, curso).json()["id"]
    r = _guardar(client, curso, sid, {curso["ana"]: "asistencia", curso["beto"]: "falta", ajena: "falta"})
    assert r.status_code == 422

def test_un_alumno_dado_de_baja_no_aparece_ni_se_acepta(client, curso):
    with Sesion() as db:
        db.get(models.Matricula, curso["beto"]).estado = "baja"
        db.commit()
    s = _generar(client, curso).json()
    assert [a["matricula_id"] for a in s["alumnos"]] == [curso["ana"]]
    r = _guardar(client, curso, s["id"], {curso["ana"]: "asistencia", curso["beto"]: "falta"})
    assert r.status_code == 422
    assert [f["matricula_id"] for f in _cuadricula(client, curso)["alumnos"]] == [curso["ana"]]

def test_un_alumno_inscrito_despues_de_generar_la_sesion(client, curso):
    sid = _generar(client, curso).json()["id"]
    tc = alta_alumno(client, {**ALUMNO, "codigo": "111222333", "nombre": "Carla",
                              "apellidos": "Zamora", "correoInstitucional": "carla@alumnos.udg.mx"})
    client.post("/inscripcion", json={"codigoCurso": curso["codigo"]}, headers=auth(tc))
    # No es obligatorio incluirla en la lista porque no estaba al generar la sesión
    assert _guardar(client, curso, sid, {curso["ana"]: "asistencia", curso["beto"]: "falta"}).status_code == 200
    carla = _cuadricula(client, curso)["alumnos"][2]
    assert carla["nombre"] == "Carla"
    assert carla["estados"][0]["estado"] is None
    assert carla["porcentajeAsistencia"] == 100

# ------------------------------------------------------------------ RF-25: editar una sesión pasada
def test_rf25_editar_la_lista_de_una_sesion_pasada(client, curso, monkeypatch):
    lunes = _clase(client, curso, monkeypatch, LUNES, "falta", "asistencia")
    _clase(client, curso, monkeypatch, MIERCOLES, "asistencia", "asistencia")
    assert _guardar(client, curso, lunes, {curso["ana"]: "asistencia", curso["beto"]: "asistencia"}).status_code == 200
    r = client.get(f"/docente/cursos/{curso['id']}/sesiones/{lunes}", headers=auth(curso["t1"]))
    assert r.status_code == 200
    assert [a["estado"] for a in r.json()["alumnos"]] == ["asistencia", "asistencia"]
    assert _cuadricula(client, curso)["alumnos"][0]["porcentajeAsistencia"] == 100

# ------------------------------------------------------------------ RF-24 / RF-26: cuadrícula
def test_rf24_rf26_cuadricula_con_porcentaje_estatus_y_semaforo(client, curso, monkeypatch):
    fechas = [LUNES, MIERCOLES, date(2026, 11, 2), date(2026, 11, 4), date(2026, 11, 9)]
    ana = ["asistencia", "retardo", "asistencia", "asistencia", "falta"]   # 4/5 = 80 %
    beto = ["falta", "falta", "asistencia", "retardo", "falta"]            # 2/5 = 40 %
    for f, a, b in zip(reversed(fechas), reversed(ana), reversed(beto)):  # se generan en desorden
        _clase(client, curso, monkeypatch, f, a, b)
    _fijar_fecha(monkeypatch, date(2026, 11, 11))
    _generar(client, curso)  # sexta sesión, pendiente: no cuenta

    g = _cuadricula(client, curso)
    assert [s["fecha"] for s in g["sesiones"]] == [f.isoformat() for f in fechas] + ["2026-11-11"]
    assert [s["listaGuardada"] for s in g["sesiones"]] == [True] * 5 + [False]
    fila_ana, fila_beto = g["alumnos"]
    assert [e["estado"] for e in fila_ana["estados"]] == ana + ["pendiente"]
    assert [e["sesion_id"] for e in fila_ana["estados"]] == [s["id"] for s in g["sesiones"]]
    assert (fila_ana["porcentajeAsistencia"], fila_ana["estatusNormativo"], fila_ana["semaforo"]) == (80, "Ordinario", "amarillo")
    assert (fila_beto["porcentajeAsistencia"], fila_beto["estatusNormativo"], fila_beto["semaforo"]) == (40, "Sin Derecho", "rojo")
    with Sesion() as db:  # la función reutilizable da lo mismo que la cuadrícula
        assert services.porcentaje_asistencia(db, curso["ana"]) == 80

# ------------------------------------------------------------------ cálculo (funciones reutilizables)
@pytest.mark.parametrize("estados, esperado", [
    ([], 100),
    (["pendiente", "pendiente"], 100),
    (["asistencia", "retardo", "falta", "falta"], 50),
    (["retardo", "retardo"], 100),
])
def test_calculo_del_porcentaje(estados, esperado):
    assert services.calcular_porcentaje_asistencia(estados) == esperado

@pytest.mark.parametrize("porcentaje, estatus, semaforo", [
    (100, "Ordinario", "verde"),
    (85.01, "Ordinario", "verde"),
    (85, "Ordinario", "amarillo"),
    (80, "Ordinario", "amarillo"),
    (79.99, "Extraordinario", "rojo"),
    (65, "Extraordinario", "rojo"),
    (64.99, "Sin Derecho", "rojo"),
])
def test_rf49_estatus_normativo_y_semaforo(porcentaje, estatus, semaforo):
    assert services.estatus_normativo(porcentaje) == estatus
    assert services.semaforo_asistencia(porcentaje) == semaforo

# ------------------------------------------------------------------ RF-95: solo el docente creador
def test_rf95_solo_el_docente_creador_pasa_lista(client, curso):
    sid = _generar(client, curso).json()["id"]
    base = f"/docente/cursos/{curso['id']}"
    for t in (curso["t2"], curso["ta"], curso["alumnos"][0]):
        assert client.post(f"{base}/sesiones", headers=auth(t)).status_code == 403
        assert client.get(f"{base}/sesiones/{sid}", headers=auth(t)).status_code == 403
        assert client.get(f"{base}/asistencia", headers=auth(t)).status_code == 403
        assert _guardar(client, curso, sid, {curso["ana"]: "falta", curso["beto"]: "falta"}, t=t).status_code == 403

def test_sesion_de_otro_curso_no_se_encuentra(client, curso):
    sid = _generar(client, curso).json()["id"]
    otro = client.post("/cursos", json={**CURSO, "seccion": "D02"}, headers=auth(curso["t1"])).json()
    r = client.get(f"/docente/cursos/{otro['id']}/sesiones/{sid}", headers=auth(curso["t1"]))
    assert r.status_code == 404
    assert r.json()["detail"] == "Sesión no encontrada"
