"""Catálogo de materias que mantiene el administrador (RF-94)."""
import pytest

import models
from helpers import Sesion, alta_alumno, alta_docente, auth, crear_admin

@pytest.fixture()
def ta(client):
    return crear_admin(client)

def _crear(client, ta, clave="I5288", nombre="Bases de Datos"):
    return client.post("/admin/materias", json={"clave": clave, "nombre": nombre}, headers=auth(ta))

def _catalogo(client):
    return [(m["clave"], m["nombre"]) for m in client.get("/catalogos/materias").json()]

def test_rf94_dar_de_alta_una_materia(client, ta):
    r = _crear(client, ta, " prov-01 ", "Optativa de prueba")
    assert r.status_code == 201, r.text
    assert (r.json()["clave"], r.json()["nombre"]) == ("PROV-01", "Optativa de prueba")  # clave en mayúsculas
    assert _catalogo(client) == [("PROV-01", "Optativa de prueba")]  # ya aparece en el catálogo público

def test_rf94_clave_repetida(client, ta):
    _crear(client, ta)
    r = _crear(client, ta, "i5288", "Otra")
    assert r.status_code == 409
    assert r.json()["detail"] == "Ya existe una materia con esa clave"

@pytest.mark.parametrize("cuerpo", [
    {"clave": "X", "nombre": "Muy corta"},
    {"clave": "CLAVE_CON_GUION_BAJO", "nombre": "Inválida"},
    {"clave": "I 5288", "nombre": "Con espacio"},
    {"clave": "I5288", "nombre": ""},
    {"nombre": "Sin clave"},
])
def test_rf94_datos_invalidos(client, ta, cuerpo):
    assert client.post("/admin/materias", json=cuerpo, headers=auth(ta)).status_code == 422

def test_rf94_editar_una_materia(client, ta):
    mid = _crear(client, ta).json()["id"]
    r = client.patch(f"/admin/materias/{mid}", json={"nombre": "Bases de Datos I"}, headers=auth(ta))
    assert r.status_code == 200
    assert (r.json()["clave"], r.json()["nombre"]) == ("I5288", "Bases de Datos I")
    r = client.patch(f"/admin/materias/{mid}", json={"clave": "i5288b"}, headers=auth(ta))
    assert r.json()["clave"] == "I5288B"
    # Puede conservar su propia clave, pero no tomar la de otra
    assert client.patch(f"/admin/materias/{mid}", json={"clave": "I5288B"}, headers=auth(ta)).status_code == 200
    otra = _crear(client, ta, "I5289", "Programación").json()["id"]
    assert client.patch(f"/admin/materias/{otra}", json={"clave": "I5288B"}, headers=auth(ta)).status_code == 409
    assert client.patch("/admin/materias/999", json={"nombre": "X"}, headers=auth(ta)).status_code == 404

def test_rf94_eliminar_una_materia_sin_uso(client, ta):
    mid = _crear(client, ta).json()["id"]
    r = client.delete(f"/admin/materias/{mid}", headers=auth(ta))
    assert r.status_code == 200
    assert r.json()["mensaje"] == "Materia eliminada correctamente"
    assert _catalogo(client) == []
    r = client.delete(f"/admin/materias/{mid}", headers=auth(ta))
    assert r.status_code == 404
    assert r.json()["detail"] == "Materia no encontrada"

@pytest.mark.parametrize("uso", ["malla", "curso", "historial"])
def test_rf94_no_se_elimina_una_materia_en_uso(client, ta, uso):
    mid = _crear(client, ta).json()["id"]
    with Sesion() as db:
        if uso == "malla":
            malla = models.MallaCurricular(carrera="INFO", generacion="2023", nombrePlan="Plan 2023")
            db.add(malla)
            db.flush()
            db.add(models.MallaMateria(semestreBase=1, mallaCurricular_id=malla.id, materia_id=mid))
        elif uso == "curso":
            db.add(models.Curso(nombreMateria="Bases de Datos", seccion="D01", codigoCurso="ABCD1234",
                                estado="activo", tipoEvaluacion="numerica", umbralNumerico=60,
                                diasSemana="lunes", horaInicio="08:00", horaFin="10:00", materia_id=mid))
        else:
            db.add(models.HistorialAcademico(periodo="2025-B", materia="Bases de Datos", calificacion=90,
                                             resultado="aprobada", materia_id=mid))
        db.commit()
    r = client.delete(f"/admin/materias/{mid}", headers=auth(ta))
    assert r.status_code == 409
    assert r.json()["detail"].startswith("No se puede eliminar una materia que ya se usa")
    assert len(_catalogo(client)) == 1

def test_rf94_solo_el_administrador_mantiene_el_catalogo(client, ta):
    mid = _crear(client, ta).json()["id"]
    docente = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    alumno = alta_alumno(client)
    for t in (docente, alumno):
        assert _crear(client, t, "I9999", "X").status_code == 403
        assert client.patch(f"/admin/materias/{mid}", json={"nombre": "X"}, headers=auth(t)).status_code == 403
        assert client.delete(f"/admin/materias/{mid}", headers=auth(t)).status_code == 403
    assert client.post("/admin/materias", json={"clave": "I9999", "nombre": "X"}).status_code in (401, 403)
