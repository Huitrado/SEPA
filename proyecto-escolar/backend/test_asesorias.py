"""Módulo de asesorías entre estudiantes (RF-73 a RF-80, RF-92)."""
import pytest

import models
from helpers import ALUMNO, ALUMNO_B, Sesion, alta_alumno, alta_docente, auth, crear_admin

@pytest.fixture()
def gente(client):
    """Ana es asesora (RF-73); Beto es estudiante regular. Hay dos materias en el catálogo."""
    with Sesion() as db:
        db.add_all([models.Materia(clave="I5288", nombre="Bases de Datos"),
                    models.Materia(clave="I5290", nombre="Estructuras de Datos")])
        db.commit()
    ta = crear_admin(client)
    ana = alta_alumno(client, ALUMNO)
    beto = alta_alumno(client, ALUMNO_B)
    ana_id = next(u["id"] for u in client.get("/admin/usuarios", headers=auth(ta)).json() if u["nombre"] == "Ana")
    client.patch(f"/admin/usuarios/{ana_id}/asesor", json={"asesor": True}, headers=auth(ta))
    return {"ta": ta, "ana": ana, "beto": beto, "ana_id": ana_id}

PUBLICACION = {"materia": "bases de datos", "horario": "Lunes y miércoles de 16:00 a 18:00",
               "modalidad": "presencial", "lugarOMedio": "Módulo X, salón 12", "topico": "Normalización y SQL"}

def _publicar(client, g, **cambios):
    return client.post("/asesorias", json={**PUBLICACION, **cambios}, headers=auth(g["ana"]))

def _tablero(client, g, consulta=""):
    r = client.get(f"/asesorias{consulta}", headers=auth(g["beto"]))
    assert r.status_code == 200, r.text
    return r.json()

# ------------------------------------------------------------------ RF-74, RF-75, RF-78, RF-80
def test_rf74_publicar_y_aparece_en_el_tablero(client, gente):
    r = _publicar(client, gente)
    assert r.status_code == 201, r.text
    p = r.json()
    assert (p["materia"], p["estado"], p["asesor"], p["esMia"]) == ("Bases de Datos", "activa", "Ana López", True)
    [visible] = _tablero(client, gente)
    assert (visible["id"], visible["esMia"], visible["correoAsesor"]) == (p["id"], False, "ana@alumnos.udg.mx")
    detalle = client.get(f"/asesorias/{p['id']}", headers=auth(gente["beto"])).json()
    assert (detalle["lugarOMedio"], detalle["topico"]) == ("Módulo X, salón 12", "Normalización y SQL")  # RF-80

def test_rf75_el_topico_es_opcional(client, gente):
    assert _publicar(client, gente, topico=None).status_code == 201

@pytest.mark.parametrize("cambio", [{"horario": ""}, {"lugarOMedio": ""}, {"modalidad": "hibrida"}, {"materia": ""}])
def test_rf74_campos_obligatorios(client, gente, cambio):
    assert _publicar(client, gente, **cambio).status_code == 422

def test_rf74_la_materia_sale_del_catalogo(client, gente):
    r = _publicar(client, gente, materia="Cocina")
    assert r.status_code == 422
    assert r.json()["detail"] == "La materia no está en el catálogo oficial"

# ------------------------------------------------------------------ RF-73, RF-92: solo asesores publican
def test_rf73_solo_los_asesores_publican(client, gente):
    r = client.post("/asesorias", json=PUBLICACION, headers=auth(gente["beto"]))
    assert r.status_code == 403
    assert r.json()["detail"] == "Se requiere rol de asesor"
    assert client.get("/asesorias/mias", headers=auth(gente["beto"])).status_code == 403
    docente = alta_docente(client, gente["ta"], "d1@academicos.udg.mx", "D-1")
    assert client.get("/asesorias", headers=auth(docente)).status_code == 403

def test_rf92_el_asesor_ve_sus_publicaciones(client, gente):
    _publicar(client, gente)
    _publicar(client, gente, materia="Estructuras de Datos", modalidad="virtual", lugarOMedio="https://meet.example/abc")
    mias = client.get("/asesorias/mias", headers=auth(gente["ana"])).json()
    assert sorted(p["materia"] for p in mias) == ["Bases de Datos", "Estructuras de Datos"]

def test_al_quitar_el_rol_sus_anuncios_salen_del_tablero(client, gente):
    _publicar(client, gente)
    client.patch(f"/admin/usuarios/{gente['ana_id']}/asesor", json={"asesor": False}, headers=auth(gente["ta"]))
    assert _tablero(client, gente) == []
    assert client.get("/asesorias/mias", headers=auth(gente["ana"])).status_code == 403

# ------------------------------------------------------------------ RF-76, RF-77: editar, ocultar y eliminar
def test_rf76_editar_una_publicacion(client, gente):
    pid = _publicar(client, gente).json()["id"]
    r = client.patch(f"/asesorias/{pid}", json={"horario": "Viernes 10:00", "modalidad": "virtual",
                                                "lugarOMedio": "https://meet.example/xyz"}, headers=auth(gente["ana"]))
    assert r.status_code == 200, r.text
    assert (r.json()["horario"], r.json()["modalidad"], r.json()["materia"]) == ("Viernes 10:00", "virtual", "Bases de Datos")

def test_rf77_desactivar_la_retira_del_tablero(client, gente):
    pid = _publicar(client, gente).json()["id"]
    client.patch(f"/asesorias/{pid}", json={"estado": "inactiva"}, headers=auth(gente["ana"]))
    assert _tablero(client, gente) == []
    assert client.get(f"/asesorias/{pid}", headers=auth(gente["beto"])).status_code == 404
    assert client.get(f"/asesorias/{pid}", headers=auth(gente["ana"])).json()["estado"] == "inactiva"  # su autora sí la ve
    client.patch(f"/asesorias/{pid}", json={"estado": "activa"}, headers=auth(gente["ana"]))
    assert len(_tablero(client, gente)) == 1

def test_rf77_eliminar_una_publicacion(client, gente):
    pid = _publicar(client, gente).json()["id"]
    r = client.delete(f"/asesorias/{pid}", headers=auth(gente["ana"]))
    assert r.status_code == 200
    assert client.get(f"/asesorias/{pid}", headers=auth(gente["ana"])).status_code == 404

def test_otro_asesor_no_modifica_lo_ajeno(client, gente):
    pid = _publicar(client, gente).json()["id"]
    otro = next(u["id"] for u in client.get("/admin/usuarios", headers=auth(gente["ta"])).json() if u["nombre"] == "Beto")
    client.patch(f"/admin/usuarios/{otro}/asesor", json={"asesor": True}, headers=auth(gente["ta"]))
    r = client.patch(f"/asesorias/{pid}", json={"horario": "X"}, headers=auth(gente["beto"]))
    assert r.status_code == 403
    assert r.json()["detail"] == "Esta publicación no es tuya"
    assert client.delete(f"/asesorias/{pid}", headers=auth(gente["beto"])).status_code == 403

# ------------------------------------------------------------------ RF-79: filtros
def test_rf79_filtros_del_tablero(client, gente):
    _publicar(client, gente)
    _publicar(client, gente, materia="Estructuras de Datos", modalidad="virtual",
              lugarOMedio="https://meet.example/abc", horario="Sábado 9:00", topico="Árboles AVL")
    assert [p["materia"] for p in _tablero(client, gente, "?materia=estructuras de datos")] == ["Estructuras de Datos"]
    assert [p["modalidad"] for p in _tablero(client, gente, "?modalidad=presencial")] == ["presencial"]
    assert [p["topico"] for p in _tablero(client, gente, "?q=avl")] == ["Árboles AVL"]
    assert [p["horario"] for p in _tablero(client, gente, "?q=sábado")] == ["Sábado 9:00"]
    assert client.get("/asesorias?modalidad=hibrida", headers=auth(gente["beto"])).status_code == 422
