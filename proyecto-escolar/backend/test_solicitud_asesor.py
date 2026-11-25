"""Solicitud para ser asesor: el estudiante la envía y el administrador la acepta o la rechaza."""
import pytest

from helpers import ALUMNO, ALUMNO_B, alta_alumno, auth, crear_admin

MOTIVO = "Tengo 95 en Bases de Datos y ya ayudo a mis compañeros a estudiar SQL."

@pytest.fixture()
def gente(client):
    ta = crear_admin(client)
    ana = alta_alumno(client, ALUMNO)
    beto = alta_alumno(client, ALUMNO_B)
    return {"ta": ta, "ana": ana, "beto": beto}

def _solicitar(client, token, **cambios):
    return client.post("/asesorias/solicitud", json={"motivo": MOTIVO, "materias": "Bases de Datos", **cambios},
                       headers=auth(token))

def _responder(client, g, solicitud_id, decision, comentario=None):
    return client.patch(f"/admin/solicitudes-asesor/{solicitud_id}",
                        json={"decision": decision, "comentario": comentario}, headers=auth(g["ta"]))

def _roles(client, g, nombre):
    return next(u["roles"] for u in client.get("/admin/usuarios", headers=auth(g["ta"])).json() if u["nombre"] == nombre)

def test_el_alumno_envia_y_ve_su_solicitud(client, gente):
    assert client.get("/asesorias/solicitud", headers=auth(gente["ana"])).json() is None
    r = _solicitar(client, gente["ana"])
    assert r.status_code == 201, r.text
    s = r.json()
    assert (s["estado"], s["motivo"], s["materias"], s["nombre"]) == ("pendiente", MOTIVO, "Bases de Datos", "Ana López")
    assert client.get("/asesorias/solicitud", headers=auth(gente["ana"])).json()["id"] == s["id"]

def test_motivo_obligatorio_y_con_detalle(client, gente):
    r = _solicitar(client, gente["ana"], motivo="Quiero ayudar")
    assert r.status_code == 422
    assert r.json()["errores"][0] == {"campo": "motivo", "mensaje": "Debe tener al menos 20 caracteres"}

def test_solo_una_pendiente_a_la_vez(client, gente):
    _solicitar(client, gente["ana"])
    r = _solicitar(client, gente["ana"])
    assert r.status_code == 409
    assert "pendiente" in r.json()["detail"]

def test_el_admin_ve_las_pendientes(client, gente):
    _solicitar(client, gente["ana"])
    _solicitar(client, gente["beto"])
    todas = client.get("/admin/solicitudes-asesor?estado=pendiente", headers=auth(gente["ta"])).json()
    assert [s["nombre"] for s in todas] == ["Ana López", "Beto López"]  # la más antigua primero
    # un estudiante no puede ver ni responder solicitudes
    assert client.get("/admin/solicitudes-asesor", headers=auth(gente["ana"])).status_code == 403
    assert client.patch(f"/admin/solicitudes-asesor/{todas[0]['id']}", json={"decision": "aceptada"},
                        headers=auth(gente["ana"])).status_code == 403

def test_aceptar_da_el_rol_de_asesor(client, gente):
    s = _solicitar(client, gente["ana"]).json()
    r = _responder(client, gente, s["id"], "aceptada")
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "aceptada" and r.json()["fechaRespuesta"]
    assert "asesor" in _roles(client, gente, "Ana")
    # ya puede usar las herramientas de asesor y no necesita volver a pedirlo
    assert client.get("/asesorias/mias", headers=auth(gente["ana"])).status_code == 200
    assert _solicitar(client, gente["ana"]).status_code == 409

def test_rechazar_con_comentario_y_volver_a_pedir(client, gente):
    s = _solicitar(client, gente["ana"]).json()
    r = _responder(client, gente, s["id"], "rechazada", "Primero acredita la materia con más de 85.")
    assert r.status_code == 200
    assert "asesor" not in _roles(client, gente, "Ana")
    mia = client.get("/asesorias/solicitud", headers=auth(gente["ana"])).json()
    assert (mia["estado"], mia["comentarioAdmin"]) == ("rechazada", "Primero acredita la materia con más de 85.")
    assert _solicitar(client, gente["ana"]).status_code == 201  # tras un rechazo puede volver a pedirlo

def test_no_se_responde_dos_veces(client, gente):
    s = _solicitar(client, gente["ana"]).json()
    _responder(client, gente, s["id"], "rechazada")
    r = _responder(client, gente, s["id"], "aceptada")
    assert r.status_code == 409
    assert "asesor" not in _roles(client, gente, "Ana")
    assert _responder(client, gente, 9999, "aceptada").status_code == 404
