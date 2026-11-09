"""Módulo de calificaciones (RF-43, RF-46, RF-47, RF-67)."""
from datetime import datetime

import pytest

import models
import services
from helpers import ALUMNO, ALUMNO_B, CURSO, Sesion, alta_alumno, alta_docente, auth, crear_admin

ANTES = datetime(2026, 10, 25, 12, 0)
DESPUES_DEL_PARCIAL = datetime(2026, 11, 6, 8, 0)  # ya vencieron T1 y el parcial; T2 no
PDF = ("tarea.pdf", b"%PDF-1.4", "application/pdf")

@pytest.fixture()
def reloj(monkeypatch, tmp_path):
    actual = {"ahora": ANTES}
    monkeypatch.setattr(services, "ahora", lambda: actual["ahora"])
    monkeypatch.setattr(services, "CARPETA_ARCHIVOS", tmp_path)
    return actual

def _preparar(client, tipo="numerica"):
    """Tareas 40 % (T1 y T2, de 10 puntos) y Exámenes 60 % (Parcial, de 100): T1 y T2 valen 20 y el parcial 60."""
    ta = crear_admin(client)
    t1 = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    t2 = alta_docente(client, ta, "d2@academicos.udg.mx", "D-2")
    c = client.post("/cursos", json={**CURSO, "tipoEvaluacion": tipo}, headers=auth(t1)).json()
    base = f"/docente/cursos/{c['id']}"
    cats = {n: client.post(f"{base}/categorias", json={"nombre": n, "porcentajePeso": p},
                           headers=auth(t1)).json()["categoria"]["id"] for n, p in (("Tareas", 40), ("Exámenes", 60))}
    acts = {}
    for titulo, cat, limite, maximo in (("T1", "Tareas", "2026-11-01T23:59", 10),
                                        ("Parcial", "Exámenes", "2026-11-05T10:00", 100),
                                        ("T2", "Tareas", "2026-11-10T23:59", 10)):
        acts[titulo] = client.post(f"{base}/actividades", headers=auth(t1), json={
            "categoriaEvaluacion_id": cats[cat], "titulo": titulo,
            "fechaHoraLimite": limite, "puntuacionMaxima": maximo}).json()["id"]
    alumnos = {}
    for nombre, datos in (("ana", ALUMNO), ("beto", ALUMNO_B)):
        alumnos[nombre] = alta_alumno(client, datos)
        client.post("/inscripcion", json={"codigoCurso": c["codigoCurso"]}, headers=auth(alumnos[nombre]))
    return {"ta": ta, "t1": t1, "t2": t2, "id": c["id"], "base": base, "cats": cats, **acts, **alumnos}

@pytest.fixture()
def curso(client, reloj):
    return _preparar(client)

def _entregar(client, cur, actividad, alumno="ana"):
    r = client.post(f"/alumno/actividades/{cur[actividad]}/entrega", files={"archivo": PDF},
                    headers=auth(cur[alumno]))
    assert r.status_code == 201, r.text
    return r.json()["entrega"]["id"]

def _calificar(client, cur, entrega_id, nota, t=None, **extra):
    return client.put(f"{cur['base']}/entregas/{entrega_id}/calificacion",
                      json={"calificacionObtenida": nota, **extra}, headers=auth(t or cur["t1"]))

def _acumulada_guardada(client, cur, nombre="Ana"):
    alumnos = client.get(f"{cur['base']}/alumnos", headers=auth(cur["t1"])).json()
    return next(a["calificacionAcumuladaActual"] for a in alumnos if a["nombre"] == nombre)

def _fila(client, cur, nombre="Ana"):
    r = client.get(f"{cur['base']}/calificaciones", headers=auth(cur["t1"]))
    assert r.status_code == 200, r.text
    return next(f for f in r.json()["alumnos"] if f["nombre"] == nombre)

# ------------------------------------------------------------------ RF-43: calificar
def test_rf43_calificar_una_entrega(client, curso, reloj):
    eid = _entregar(client, curso, "T1")
    reloj["ahora"] = datetime(2026, 10, 26, 9, 30)
    r = _calificar(client, curso, eid, 8, retroalimentacion="Falta el ejercicio 3")
    assert r.status_code == 200, r.text
    assert r.json()["calificacion"] == {"calificacionObtenida": 8, "retroalimentacion": "Falta el ejercicio 3",
                                        "fecha": "2026-10-26T09:30:00"}
    assert r.json()["calificacionAcumuladaActual"] == 16  # 20 % × 8/10
    assert _acumulada_guardada(client, curso) == 16       # RF-67: queda guardada en Matricula

@pytest.mark.parametrize("nota", [0, 10])
def test_rf43_los_extremos_son_validos(client, curso, nota):
    assert _calificar(client, curso, _entregar(client, curso, "T1"), nota).status_code == 200

def test_rf43_fuera_de_rango(client, curso):
    eid = _entregar(client, curso, "T1")
    r = _calificar(client, curso, eid, 10.5)
    assert r.status_code == 422
    assert r.json()["detail"] == "La calificación debe estar entre 0 y 10"
    assert _calificar(client, curso, eid, -1).status_code == 422
    assert client.put(f"{curso['base']}/entregas/{eid}/calificacion", json={},
                      headers=auth(curso["t1"])).status_code == 422

def test_rf43_corregir_una_calificacion(client, curso):
    eid = _entregar(client, curso, "T1")
    _calificar(client, curso, eid, 5)
    r = _calificar(client, curso, eid, 10)
    assert r.json()["calificacionAcumuladaActual"] == 20
    with Sesion() as db:
        assert db.query(models.Calificacion).count() == 1

def test_entrega_de_otro_curso_o_inexistente(client, curso):
    eid = _entregar(client, curso, "T1")
    otro = client.post("/cursos", json={**CURSO, "seccion": "D02"}, headers=auth(curso["t1"])).json()
    r = client.put(f"/docente/cursos/{otro['id']}/entregas/{eid}/calificacion",
                   json={"calificacionObtenida": 5}, headers=auth(curso["t1"]))
    assert r.status_code == 404
    assert r.json()["detail"] == "Entrega no encontrada"
    assert _calificar(client, curso, 999, 5).status_code == 404

def test_no_se_califica_a_un_alumno_dado_de_baja(client, curso):
    eid = _entregar(client, curso, "T1")
    with Sesion() as db:
        db.get(models.Matricula, db.get(models.Entrega, eid).matricula_id).estado = "baja"
        db.commit()
    r = _calificar(client, curso, eid, 5)
    assert r.status_code == 409
    assert r.json()["detail"] == "El alumno ya no está activo en el curso"

# ------------------------------------------------------------------ RF-46 / RF-47: acumulada y ceros
def test_rf47_vencida_sin_entrega_cuenta_como_cero(client, curso, reloj):
    _calificar(client, curso, _entregar(client, curso, "T1"), 8)
    reloj["ahora"] = DESPUES_DEL_PARCIAL
    ana, beto = _fila(client, curso), _fila(client, curso, "Beto")
    # Ana: T1 calificada (16 de 20), parcial vencido sin entrega (0 de 60), T2 aún no vence
    assert [c["cuentaComoCero"] for c in ana["celdas"]] == [False, True, False]
    assert (ana["calificacionAcumulada"], ana["puntosPosibles"], ana["desempenoProporcional"]) == (16, 80, 20)
    # Beto: T1 y parcial vencidos sin entrega
    assert [c["estadoEntrega"] for c in beto["celdas"]] == ["vencida", "vencida", "pendiente"]
    assert (beto["calificacionAcumulada"], beto["puntosPosibles"], beto["desempenoProporcional"]) == (0, 80, 0)

def test_entregado_sin_calificar_no_cuenta_todavia(client, curso):
    _entregar(client, curso, "T1")
    ana = _fila(client, curso)
    assert ana["celdas"][0]["estadoEntrega"] == "entregada" and ana["celdas"][0]["calificacion"] is None
    assert (ana["calificacionAcumulada"], ana["puntosPosibles"], ana["desempenoProporcional"]) == (0, 0, None)

def test_rf46_acumulada_con_todas_las_actividades(client, curso, reloj):
    for act, nota in (("T1", 10), ("Parcial", 70), ("T2", 5)):
        _calificar(client, curso, _entregar(client, curso, act), nota)
    # 20 + 60 × 0.7 + 20 × 0.5 = 72
    assert _acumulada_guardada(client, curso) == 72
    reloj["ahora"] = datetime(2026, 11, 20)
    assert _fila(client, curso)["desempenoProporcional"] == 72

@pytest.mark.parametrize("items, esperado", [
    ([], (0, 0, None)),
    ([(20, 10, 8, False)], (16, 20, 80)),
    ([(20, 10, None, True), (60, 100, 90, False)], (54, 80, 67.5)),
    ([(20, 10, None, False)], (0, 0, None)),        # pendiente o sin calificar: no cuenta
    ([(13.333333, 10, 10, False)], (13.33, 13.33, 100)),
])
def test_calculo_de_la_calificacion(items, esperado):
    r = services.calcular_calificacion(items)
    assert (r["calificacionAcumulada"], r["puntosPosibles"], r["desempenoProporcional"]) == esperado

# ------------------------------------------------------------------ RF-67: se recalcula cuando cambian los pesos
def test_rf67_agregar_una_actividad_recalcula(client, curso):
    _calificar(client, curso, _entregar(client, curso, "T1"), 10)
    assert _acumulada_guardada(client, curso) == 20
    client.post(f"{curso['base']}/actividades", headers=auth(curso["t1"]), json={
        "categoriaEvaluacion_id": curso["cats"]["Tareas"], "titulo": "T3",
        "fechaHoraLimite": "2026-11-20T23:59", "puntuacionMaxima": 10})
    assert _acumulada_guardada(client, curso) == 13.33  # ahora cada tarea vale 40/3

def test_rf67_cambiar_el_peso_de_la_categoria_recalcula(client, curso):
    _calificar(client, curso, _entregar(client, curso, "T1"), 10)
    r = client.patch(f"{curso['base']}/categorias/{curso['cats']['Tareas']}", json={"porcentajePeso": 30},
                     headers=auth(curso["t1"]))
    assert r.status_code == 200
    assert _acumulada_guardada(client, curso) == 15

def test_rf67_eliminar_una_actividad_recalcula(client, curso):
    _calificar(client, curso, _entregar(client, curso, "T1"), 10)
    client.delete(f"{curso['base']}/actividades/{curso['T2']}", headers=auth(curso["t1"]))
    assert _acumulada_guardada(client, curso) == 40  # T1 queda sola en Tareas

def test_la_puntuacion_maxima_no_baja_de_una_calificacion_puesta(client, curso):
    _calificar(client, curso, _entregar(client, curso, "T1"), 8)
    url = f"{curso['base']}/actividades/{curso['T1']}"
    r = client.patch(url, json={"puntuacionMaxima": 7}, headers=auth(curso["t1"]))
    assert r.status_code == 409
    assert r.json()["detail"] == "La puntuación máxima no puede ser menor que una calificación ya asignada (8)"
    assert client.patch(url, json={"puntuacionMaxima": 20}, headers=auth(curso["t1"])).status_code == 200
    assert _acumulada_guardada(client, curso) == 8  # 20 % × 8/20

# ------------------------------------------------------------------ cuadrícula y vista del alumno
def test_cuadricula_ordenada_por_fecha_limite(client, curso):
    r = client.get(f"{curso['base']}/calificaciones", headers=auth(curso["t1"]))
    assert [(a["titulo"], a["valorEnCurso"]) for a in r.json()["actividades"]] == \
           [("T1", 20), ("Parcial", 60), ("T2", 20)]
    assert [f["nombre"] for f in r.json()["alumnos"]] == ["Ana", "Beto"]

def test_el_alumno_ve_solo_sus_calificaciones(client, curso):
    _calificar(client, curso, _entregar(client, curso, "T1"), 9, retroalimentacion="Bien")
    _calificar(client, curso, _entregar(client, curso, "T1", "beto"), 4)
    r = client.get(f"/alumno/cursos/{curso['id']}/calificaciones", headers=auth(curso["ana"]))
    assert r.status_code == 200, r.text
    mia = r.json()
    assert mia["calificacionAcumulada"] == 18
    assert mia["celdas"][0]["calificacion"]["retroalimentacion"] == "Bien"
    assert [a["titulo"] for a in mia["actividades"]] == ["T1", "Parcial", "T2"]
    carla = alta_alumno(client, {**ALUMNO, "codigo": "111222333", "correoInstitucional": "carla@alumnos.udg.mx"})
    assert client.get(f"/alumno/cursos/{curso['id']}/calificaciones", headers=auth(carla)).status_code == 403

def test_aprobado_no_aprobado_se_califica_igual(client, reloj):
    cur = _preparar(client, "aprobado_no_aprobado")
    r = _calificar(client, cur, _entregar(client, cur, "T1"), 10)
    assert r.status_code == 200
    assert r.json()["calificacionAcumuladaActual"] == 20

# ------------------------------------------------------------------ RF-95: solo el docente creador califica
def test_rf95_solo_el_docente_creador_califica(client, curso):
    eid = _entregar(client, curso, "T1")
    for t in (curso["t2"], curso["ta"], curso["ana"]):
        assert _calificar(client, curso, eid, 10, t=t).status_code == 403
        assert client.get(f"{curso['base']}/calificaciones", headers=auth(t)).status_code == 403
