"""Módulo de categorías de evaluación (RF-31, RF-32)."""
import pytest

import models
from helpers import CURSO, Sesion, alta_alumno, alta_docente, auth, crear_admin

@pytest.fixture()
def curso(client):
    """Curso del docente t1; t2 es otro docente."""
    ta = crear_admin(client)
    t1 = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    t2 = alta_docente(client, ta, "d2@academicos.udg.mx", "D-2")
    r = client.post("/cursos", json=CURSO, headers=auth(t1))
    assert r.status_code == 201, r.text
    return {"ta": ta, "t1": t1, "t2": t2, "url": f"/docente/cursos/{r.json()['id']}/categorias"}

def _crear(client, cur, nombre, peso):
    return client.post(cur["url"], json={"nombre": nombre, "porcentajePeso": peso}, headers=auth(cur["t1"]))

def _listar(client, cur):
    r = client.get(cur["url"], headers=auth(cur["t1"]))
    assert r.status_code == 200, r.text
    return r.json()

# ------------------------------------------------------------------ RF-31: crear, editar, listar y eliminar
def test_rf31_crear_y_listar_categorias(client, curso):
    r = _crear(client, curso, "Exámenes", 60)
    assert r.status_code == 201, r.text
    assert r.json()["categoria"]["nombre"] == "Exámenes"
    assert r.json()["categoria"]["porcentajePeso"] == 60
    _crear(client, curso, "Tareas", 40)
    lista = _listar(client, curso)
    assert [(c["nombre"], c["porcentajePeso"]) for c in lista["categorias"]] == [("Exámenes", 60), ("Tareas", 40)]

@pytest.mark.parametrize("cuerpo", [
    {"nombre": "Tareas", "porcentajePeso": 0},
    {"nombre": "Tareas", "porcentajePeso": -10},
    {"nombre": "Tareas", "porcentajePeso": 101},
    {"nombre": "", "porcentajePeso": 20},
    {"porcentajePeso": 20},
    {"nombre": "Tareas"},
])
def test_rf31_datos_invalidos(client, curso, cuerpo):
    assert client.post(curso["url"], json=cuerpo, headers=auth(curso["t1"])).status_code == 422

def test_rf31_nombre_repetido_en_el_mismo_curso(client, curso):
    _crear(client, curso, "Tareas", 30)
    r = _crear(client, curso, "tareas", 20)
    assert r.status_code == 409
    assert r.json()["detail"] == "Ya existe una categoría con ese nombre en este curso"

def test_rf31_editar_categoria(client, curso):
    cid = _crear(client, curso, "Tareas", 30).json()["categoria"]["id"]
    r = client.patch(f"{curso['url']}/{cid}", json={"porcentajePeso": 45.5}, headers=auth(curso["t1"]))
    assert r.status_code == 200, r.text
    assert r.json()["categoria"] == {"id": cid, "curso_id": r.json()["categoria"]["curso_id"],
                                     "nombre": "Tareas", "porcentajePeso": 45.5}
    r = client.patch(f"{curso['url']}/{cid}", json={"nombre": "Prácticas"}, headers=auth(curso["t1"]))
    assert (r.json()["categoria"]["nombre"], r.json()["categoria"]["porcentajePeso"]) == ("Prácticas", 45.5)

def test_rf31_eliminar_categoria(client, curso):
    cid = _crear(client, curso, "Tareas", 30).json()["categoria"]["id"]
    _crear(client, curso, "Examen", 70)
    r = client.delete(f"{curso['url']}/{cid}", headers=auth(curso["t1"]))
    assert r.status_code == 200
    assert [c["nombre"] for c in r.json()["categorias"]] == ["Examen"]
    assert r.json()["sumaPesos"] == 70
    assert client.delete(f"{curso['url']}/{cid}", headers=auth(curso["t1"])).status_code == 404

def test_rf31_no_se_elimina_una_categoria_con_actividades(client, curso):
    cid = _crear(client, curso, "Tareas", 30).json()["categoria"]["id"]
    with Sesion() as db:
        db.add(models.Actividad(titulo="Tarea 1", fechaHoraLimite="2026-11-01T23:59:00",
                                puntuacionMaxima=10, categoriaEvaluacion_id=cid))
        db.commit()
    r = client.delete(f"{curso['url']}/{cid}", headers=auth(curso["t1"]))
    assert r.status_code == 409
    assert r.json()["detail"] == "No se puede eliminar una categoría que ya tiene actividades"
    assert len(_listar(client, curso)["categorias"]) == 1

# ------------------------------------------------------------------ RF-32: la suma debe ser 100
def test_rf32_sin_categorias_advierte(client, curso):
    lista = _listar(client, curso)
    assert (lista["categorias"], lista["sumaPesos"], lista["pesosCompletos"]) == ([], 0, False)
    assert lista["advertencia"] == "Los pesos de las categorías suman 0 %; deben sumar exactamente 100 %"

def test_rf32_suma_incompleta_se_guarda_con_advertencia(client, curso):
    r = _crear(client, curso, "Exámenes", 60)
    assert r.status_code == 201
    assert (r.json()["sumaPesos"], r.json()["pesosCompletos"]) == (60, False)
    assert r.json()["advertencia"] == "Los pesos de las categorías suman 60 %; deben sumar exactamente 100 %"
    r = _crear(client, curso, "Tareas", 40)
    assert (r.json()["sumaPesos"], r.json()["pesosCompletos"], r.json()["advertencia"]) == (100, True, None)
    assert _listar(client, curso)["pesosCompletos"] is True

def test_rf32_decimales_que_suman_100(client, curso):
    for nombre in ("A", "B", "C"):
        _crear(client, curso, nombre, 33.33)
    r = _crear(client, curso, "D", 0.01)
    assert r.status_code == 201
    assert (r.json()["sumaPesos"], r.json()["pesosCompletos"]) == (100, True)

def test_rf32_no_se_puede_superar_100_al_crear(client, curso):
    _crear(client, curso, "Exámenes", 70)
    r = _crear(client, curso, "Tareas", 40)
    assert r.status_code == 409
    assert r.json()["detail"] == "La suma de los pesos no puede superar 100 % (las demás categorías suman 70 %)"
    assert len(_listar(client, curso)["categorias"]) == 1

def test_rf32_no_se_puede_superar_100_al_editar(client, curso):
    _crear(client, curso, "Exámenes", 70)
    cid = _crear(client, curso, "Tareas", 30).json()["categoria"]["id"]
    r = client.patch(f"{curso['url']}/{cid}", json={"porcentajePeso": 31}, headers=auth(curso["t1"]))
    assert r.status_code == 409
    # Bajar el peso sí se puede, aunque la suma quede incompleta
    r = client.patch(f"{curso['url']}/{cid}", json={"porcentajePeso": 20}, headers=auth(curso["t1"]))
    assert r.status_code == 200
    assert (r.json()["sumaPesos"], r.json()["pesosCompletos"]) == (90, False)

# ------------------------------------------------------------------ RF-95: solo el docente creador
def test_rf95_solo_el_docente_creador_modifica_el_encuadre(client, curso):
    cid = _crear(client, curso, "Tareas", 30).json()["categoria"]["id"]
    alumno = alta_alumno(client)
    cuerpo = {"nombre": "Otra", "porcentajePeso": 10}
    for t in (curso["t2"], curso["ta"], alumno):
        assert client.get(curso["url"], headers=auth(t)).status_code == 403
        assert client.post(curso["url"], json=cuerpo, headers=auth(t)).status_code == 403
        assert client.patch(f"{curso['url']}/{cid}", json=cuerpo, headers=auth(t)).status_code == 403
        assert client.delete(f"{curso['url']}/{cid}", headers=auth(t)).status_code == 403

def test_categoria_de_otro_curso_no_se_encuentra(client, curso):
    cid = _crear(client, curso, "Tareas", 30).json()["categoria"]["id"]
    otro = client.post("/cursos", json={**CURSO, "seccion": "D02"}, headers=auth(curso["t1"])).json()
    r = client.patch(f"/docente/cursos/{otro['id']}/categorias/{cid}", json={"porcentajePeso": 10},
                     headers=auth(curso["t1"]))
    assert r.status_code == 404
    assert r.json()["detail"] == "Categoría no encontrada"
