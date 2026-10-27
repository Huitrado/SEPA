"""Módulo de gestión académica (RF-08 a RF-18, RF-95, RF-96). Ejecutar:  pytest -v"""
import re

import pytest

from helpers import (ALUMNO, ALUMNO_B, CURSO, alta_alumno, alta_docente, auth, crear_admin,
                     registrar, token)

from datetime import date

import models, services

from helpers import Sesion, engine

@pytest.fixture()
def escenario(client):
    """Un administrador y dos docentes ya con sesión."""
    ta = crear_admin(client)
    t1 = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    t2 = alta_docente(client, ta, "d2@academicos.udg.mx", "D-2")
    return ta, t1, t2

def _crear_curso(client, t, **cambios):
    r = client.post("/cursos", json={**CURSO, **cambios}, headers=auth(t))
    assert r.status_code == 201, r.text
    return r.json()

# ---------------------------------------------------------------- RF-08
def test_rf08_solo_el_administrador_crea_ciclos(client, escenario):
    ta, t1, _ = escenario
    assert client.post("/admin/ciclos", json={"nombreOficial": "2027-A"}, headers=auth(t1)).status_code == 403
    r = client.post("/admin/ciclos", json={"nombreOficial": "2027-A"}, headers=auth(ta))
    assert r.status_code == 201

def test_rf08_las_fechas_salen_del_calendario_oficial(client, escenario):
    ta, _, _ = escenario
    a = client.post("/admin/ciclos", json={"nombreOficial": "2027-a"}, headers=auth(ta)).json()
    assert (a["nombreOficial"], a["fechaInicio"], a["fechaTermino"]) == ("2027-A", "2027-01-16", "2027-07-15")
    b = client.post("/admin/ciclos", json={"nombreOficial": "2027-B"}, headers=auth(ta)).json()
    assert (b["fechaInicio"], b["fechaTermino"]) == ("2027-07-16", "2027-12-16")

def test_rf08_estado_calculado_con_la_fecha(client, escenario):
    ta, _, _ = escenario
    for nombre in ("2026-A", "2027-A"):
        client.post("/admin/ciclos", json={"nombreOficial": nombre}, headers=auth(ta))
    estados = {c["nombreOficial"]: c["estado"] for c in client.get("/catalogos/ciclos").json()}
    assert estados == {"2026-B": "activo", "2026-A": "cerrado", "2027-A": "proximo"}
    solo_activos = client.get("/catalogos/ciclos?estado=activo").json()
    assert [c["nombreOficial"] for c in solo_activos] == ["2026-B"]

@pytest.mark.parametrize("ciclo", [
    {"nombreOficial": "2027-C"},                                                     # letra inexistente
    {"nombreOficial": "27-A"},                                                       # formato
    {"nombreOficial": "2027-B", "fechaInicio": "2027-01-01", "fechaTermino": "2027-06-01"},  # fechas distintas a las oficiales
])
def test_rf08_ciclos_invalidos(client, escenario, ciclo):
    ta, _, _ = escenario
    assert client.post("/admin/ciclos", json=ciclo, headers=auth(ta)).status_code == 422

def test_rf08_ciclo_duplicado(client, escenario):
    ta, _, _ = escenario
    assert client.post("/admin/ciclos", json={"nombreOficial": "2026-B"}, headers=auth(ta)).status_code == 409

def test_rf08_los_docentes_solo_seleccionan_del_catalogo(client, escenario):
    ciclos = client.get("/catalogos/ciclos").json()  # catálogo de solo lectura
    assert [c["nombreOficial"] for c in ciclos] == ["2026-B"]

# ---------------------------------------------------------------- RF-09
def test_rf09_el_curso_exige_un_ciclo_existente_y_no_terminado(client, escenario):
    ta, t1, _ = escenario
    sin_ciclo = {k: v for k, v in CURSO.items() if k != "cicloEscolar_id"}
    assert client.post("/cursos", json=sin_ciclo, headers=auth(t1)).status_code == 422
    assert client.post("/cursos", json={**CURSO, "cicloEscolar_id": 999}, headers=auth(t1)).status_code == 404
    cerrado = client.post("/admin/ciclos", json={"nombreOficial": "2025-A"}, headers=auth(ta)).json()
    assert cerrado["estado"] == "cerrado"
    r = client.post("/cursos", json={**CURSO, "cicloEscolar_id": cerrado["id"]}, headers=auth(t1))
    assert r.status_code == 409

def test_rf09_se_puede_preparar_un_curso_del_ciclo_proximo(client, escenario):
    ta, t1, _ = escenario
    proximo = client.post("/admin/ciclos", json={"nombreOficial": "2027-A"}, headers=auth(ta)).json()
    r = client.post("/cursos", json={**CURSO, "cicloEscolar_id": proximo["id"]}, headers=auth(t1))
    assert r.status_code == 201

# ---------------------------------------------------------------- RF-10 / RF-11
def test_rf10_rf11_archivar_y_filtrar(client, escenario):
    _, t1, _ = escenario
    c1 = _crear_curso(client, t1)
    _crear_curso(client, t1, seccion="D02")
    r = client.patch(f"/docente/cursos/{c1['id']}/estado", json={"estado": "archivado"}, headers=auth(t1))
    assert r.status_code == 200 and r.json()["estado"] == "archivado"

    por_defecto = client.get("/docente/cursos", headers=auth(t1)).json()
    assert [c["seccion"] for c in por_defecto] == ["D02"]            # solo activos
    archivados = client.get("/docente/cursos?estado=archivado", headers=auth(t1)).json()
    assert [c["seccion"] for c in archivados] == ["D01"]

def test_rf10_un_curso_archivado_se_puede_reactivar(client, escenario):
    _, t1, _ = escenario
    c = _crear_curso(client, t1)
    client.patch(f"/docente/cursos/{c['id']}/estado", json={"estado": "archivado"}, headers=auth(t1))
    r = client.patch(f"/docente/cursos/{c['id']}/estado", json={"estado": "activo"}, headers=auth(t1))
    assert r.json()["estado"] == "activo"

# ---------------------------------------------------------------- RF-12
@pytest.mark.parametrize("campo", ["nombreMateria", "seccion", "descripcion"])
def test_rf12_campos_minimos_obligatorios(client, escenario, campo):
    _, t1, _ = escenario
    datos = {k: v for k, v in CURSO.items() if k != campo}
    assert client.post("/cursos", json=datos, headers=auth(t1)).status_code == 422

def test_rf12_curso_duplicado_en_el_mismo_ciclo(client, escenario):
    _, t1, _ = escenario
    _crear_curso(client, t1)
    assert client.post("/cursos", json=CURSO, headers=auth(t1)).status_code == 409

def test_rf12_solo_los_docentes_crean_cursos(client, escenario):
    t = alta_alumno(client)
    assert client.post("/cursos", json=CURSO, headers=auth(t)).status_code == 403

# ---------------------------------------------------------------- RF-13
def test_rf13_horario_base(client, escenario):
    _, t1, _ = escenario
    c = _crear_curso(client, t1, diasSemana=["viernes", "lunes"])
    assert c["diasSemana"] == ["lunes", "viernes"]                   # en orden de la semana
    assert (c["horaInicio"], c["horaFin"]) == ("08:00", "10:00")

@pytest.mark.parametrize("cambio", [
    {"diasSemana": ["domingo"]},                    # día no permitido
    {"diasSemana": ["lunes", "lunes"]},             # repetido
    {"diasSemana": []},                             # al menos uno
    {"horaInicio": "10:00", "horaFin": "08:00"},    # fin antes que inicio
    {"horaInicio": "25:00"},                        # hora inexistente
])
def test_rf13_horarios_invalidos(client, escenario, cambio):
    _, t1, _ = escenario
    assert client.post("/cursos", json={**CURSO, **cambio}, headers=auth(t1)).status_code == 422

def test_rf13_editar_horario(client, escenario):
    _, t1, _ = escenario
    c = _crear_curso(client, t1)
    r = client.patch(f"/docente/cursos/{c['id']}", headers=auth(t1),
                     json={"diasSemana": ["martes"], "horaInicio": "09:00", "horaFin": "11:00"})
    assert r.status_code == 200
    assert r.json()["diasSemana"] == ["martes"] and r.json()["horaInicio"] == "09:00"
    malo = client.patch(f"/docente/cursos/{c['id']}", json={"horaFin": "08:00"}, headers=auth(t1))
    assert malo.status_code == 422                                   # contra la hora de inicio ya guardada

# ---------------------------------------------------------------- RF-14
def test_rf14_codigo_unico_alfanumerico(client, escenario):
    _, t1, _ = escenario
    c1 = _crear_curso(client, t1)
    c2 = _crear_curso(client, t1, seccion="D02")
    assert re.fullmatch(r"[A-Z0-9]{8}", c1["codigoCurso"])
    assert c1["codigoCurso"] != c2["codigoCurso"]
    visible = client.get("/docente/cursos", headers=auth(t1)).json()
    assert {c["codigoCurso"] for c in visible} == {c1["codigoCurso"], c2["codigoCurso"]}

def test_rf14_el_listado_general_no_expone_el_codigo(client, escenario):
    _, t1, _ = escenario
    _crear_curso(client, t1)
    ta = alta_alumno(client)
    lista = client.get("/cursos", headers=auth(ta)).json()
    assert len(lista) == 1 and "codigoCurso" not in lista[0]

# ---------------------------------------------------------------- RF-15
def test_rf15_autoinscripcion_por_codigo(client, escenario):
    _, t1, _ = escenario
    codigo = _crear_curso(client, t1)["codigoCurso"]
    ta = alta_alumno(client)
    assert client.post("/inscripcion", json={"codigoCurso": codigo}, headers=auth(ta)).status_code == 201
    assert client.post("/inscripcion", json={"codigoCurso": codigo}, headers=auth(ta)).status_code == 409
    assert client.post("/inscripcion", json={"codigoCurso": "NOEXISTE"}, headers=auth(ta)).status_code == 404
    assert client.post("/inscripcion", json={"codigoCurso": codigo}, headers=auth(t1)).status_code == 403

def test_rf15_el_codigo_no_distingue_mayusculas(client, escenario):
    _, t1, _ = escenario
    codigo = _crear_curso(client, t1)["codigoCurso"]
    ta = alta_alumno(client)
    r = client.post("/inscripcion", json={"codigoCurso": codigo.lower()}, headers=auth(ta))
    assert r.status_code == 201

def test_rf15_un_curso_archivado_no_acepta_inscripciones(client, escenario):
    _, t1, _ = escenario
    c = _crear_curso(client, t1)
    client.patch(f"/docente/cursos/{c['id']}/estado", json={"estado": "archivado"}, headers=auth(t1))
    ta = alta_alumno(client)
    r = client.post("/inscripcion", json={"codigoCurso": c["codigoCurso"]}, headers=auth(ta))
    assert r.status_code == 409

# ---------------------------------------------------------------- RF-16
def test_rf16_listado_de_matricula(client, escenario):
    _, t1, _ = escenario
    c = _crear_curso(client, t1)
    ta = alta_alumno(client)
    tb = alta_alumno(client, ALUMNO_B)
    for t in (ta, tb):
        client.post("/inscripcion", json={"codigoCurso": c["codigoCurso"]}, headers=auth(t))
    alumnos = client.get(f"/docente/cursos/{c['id']}/alumnos", headers=auth(t1)).json()
    assert len(alumnos) == 2
    ana = next(a for a in alumnos if a["nombre"] == "Ana")
    assert ana["correoInstitucional"] == "ana@alumnos.udg.mx"
    assert ana["estado"] == "activo" and ana["fechaInscripcion"]

# ---------------------------------------------------------------- RF-17 / RF-18
def test_rf17_solo_dos_tipos_de_evaluacion(client, escenario):
    _, t1, _ = escenario
    assert client.post("/cursos", json={**CURSO, "tipoEvaluacion": "otro"}, headers=auth(t1)).status_code == 422
    tipos = client.get("/catalogos/tipos-evaluacion").json()
    assert {t["etiqueta"] for t in tipos} == {"Calificación Numérica", "Aprobado/No Aprobado"}

def test_rf18_el_umbral_es_60_y_no_se_puede_cambiar(client, escenario):
    _, t1, _ = escenario
    c = _crear_curso(client, t1, umbralNumerico=10)                  # el cliente intenta fijar otro
    assert c["umbralNumerico"] == 60
    r = client.patch(f"/docente/cursos/{c['id']}", json={"umbralNumerico": 30}, headers=auth(t1))
    assert r.json()["umbralNumerico"] == 60

def test_rf18_aprobado_no_aprobado_no_usa_umbral(client, escenario):
    _, t1, _ = escenario
    c = _crear_curso(client, t1, tipoEvaluacion="aprobado_no_aprobado")
    assert c["umbralNumerico"] == 0
    r = client.patch(f"/docente/cursos/{c['id']}", json={"tipoEvaluacion": "numerica"}, headers=auth(t1))
    assert r.json()["umbralNumerico"] == 60

# ---------------------------------------------------------------- RF-95 / RF-96
def test_rf95_solo_el_docente_creador_controla_el_curso(client, escenario):
    ta, t1, t2 = escenario
    c = _crear_curso(client, t1)
    ruta = f"/docente/cursos/{c['id']}"
    alumno = alta_alumno(client)
    for t in (t2, ta, alumno):                       # otro docente, administrador, estudiante
        assert client.get(f"{ruta}/alumnos", headers=auth(t)).status_code == 403
        assert client.patch(ruta, json={"seccion": "X"}, headers=auth(t)).status_code == 403
        assert client.patch(f"{ruta}/estado", json={"estado": "archivado"}, headers=auth(t)).status_code == 403
    assert client.get("/docente/cursos", headers=auth(t2)).json() == []
    assert client.patch(ruta, json={"seccion": "d02"}, headers=auth(t1)).json()["seccion"] == "D02"

def test_rf96_el_alumno_no_puede_crear_ni_editar(client, escenario):
    t = alta_alumno(client)
    assert client.post("/cursos", json=CURSO, headers=auth(t)).status_code == 403
    assert client.post("/admin/ciclos", headers=auth(t), json={
        "nombreOficial": "X", "fechaInicio": "2027-01-01", "fechaTermino": "2027-06-01"}).status_code == 403

def test_el_administrador_puede_reasignar_un_curso(client, escenario):
    ta, t1, _ = escenario
    c = _crear_curso(client, t1)
    docentes = client.get("/admin/usuarios?rol=docente", headers=auth(ta)).json()
    d2 = next(d for d in docentes if d["correoInstitucional"] == "d2@academicos.udg.mx")["id"]
    r = client.patch(f"/admin/cursos/{c['id']}/docente", json={"docente_id": d2}, headers=auth(ta))
    assert r.status_code == 200 and r.json()["docente_id"] == d2

@pytest.mark.parametrize("fecha, esperado", [
    (date(2026, 10, 25), "2026-B"), (date(2026, 7, 16), "2026-B"), (date(2026, 7, 15), "2026-A"),
    (date(2026, 12, 16), "2026-B"), (date(2026, 12, 17), "2027-A"), (date(2027, 1, 10), "2027-A"),
])
def test_ciclo_para_fecha(fecha, esperado):
    assert services.ciclo_para_fecha(fecha)[0] == esperado

def test_sembrar_crea_ciclo_en_curso(monkeypatch):
    monkeypatch.setattr(services, "hoy", lambda: date(2026, 10, 25))
    models.Base.metadata.drop_all(engine)
    models.Base.metadata.create_all(engine)
    with Sesion() as db:
        services.sembrar_catalogos(db)
        services.sembrar_catalogos(db)  # la segunda llamada no debe duplicar nada
        ciclos = db.query(models.CicloEscolar).all()
        assert [c.nombreOficial for c in ciclos] == ["2026-B"]
        assert services.ciclo_vigente(db).nombreOficial == "2026-B"
