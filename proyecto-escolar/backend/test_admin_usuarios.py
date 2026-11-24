"""Gestión de usuarios del administrador (RF-73, RF-92, RF-93)."""
import pytest

from helpers import ALUMNO, ALUMNO_B, alta_alumno, alta_docente, auth, crear_admin, login

@pytest.fixture()
def gente(client):
    """Administrador, una docente (d1, D-1) y dos alumnos (Ana y Beto)."""
    ta = crear_admin(client)
    t1 = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    alta_alumno(client, ALUMNO)
    alta_alumno(client, ALUMNO_B)
    usuarios = {u["correoInstitucional"]: u for u in client.get("/admin/usuarios", headers=auth(ta)).json()}
    return {"ta": ta, "t1": t1, "ana": usuarios["ana@alumnos.udg.mx"], "doc": usuarios["d1@academicos.udg.mx"],
            "admin": usuarios["admin@escuela.mx"]}

def _usuario(client, ta, usuario_id):
    return next(u for u in client.get("/admin/usuarios", headers=auth(ta)).json() if u["id"] == usuario_id)

# ------------------------------------------------------------------ RF-93: lista con código, carrera y departamento
def test_rf93_lista_con_codigo_carrera_y_departamento(client, gente):
    ana, doc, admin = gente["ana"], gente["doc"], gente["admin"]
    assert (ana["codigo"], ana["carrera"], ana["ciclo"], ana["departamento"]) == ("123456789", "INFO", "2026-B", None)
    assert (doc["codigo"], doc["carrera"], doc["departamento"]) == ("D-1", None, "Sistemas")
    assert (admin["codigo"], admin["roles"]) == ("A-001", ["administrador"])
    assert ana["fechaRegistro"]

# ------------------------------------------------------------------ RF-93: modificar cuentas
def test_rf93_editar_datos_de_un_alumno(client, gente):
    r = client.patch(f"/admin/usuarios/{gente['ana']['id']}", headers=auth(gente["ta"]), json={
        "nombre": "Ana María", "correoInstitucional": "Ana.Lopez@alumnos.udg.mx", "carrera": "info"})
    assert r.status_code == 200, r.text
    assert (r.json()["nombre"], r.json()["correoInstitucional"], r.json()["carrera"]) == \
           ("Ana María", "ana.lopez@alumnos.udg.mx", "INFO")
    assert login(client, "123456789", "Secreto123").status_code == 200  # el código de acceso no cambia

def test_rf93_editar_departamento_de_un_docente(client, gente):
    r = client.patch(f"/admin/usuarios/{gente['doc']['id']}", json={"departamento": "Ciencias Computacionales"},
                     headers=auth(gente["ta"]))
    assert r.status_code == 200
    assert r.json()["departamento"] == "Ciencias Computacionales"

@pytest.mark.parametrize("quien, cambio, codigo, mensaje", [
    ("ana", {"correoInstitucional": "beto@alumnos.udg.mx"}, 409, "El correo institucional ya está registrado"),
    ("ana", {"correoInstitucional": "ana@academicos.udg.mx"}, 422, "El correo de un estudiante debe terminar en @alumnos.udg.mx"),
    ("doc", {"correoInstitucional": "d1@alumnos.udg.mx"}, 422, "El correo de un docente debe terminar en @academicos.udg.mx"),
    ("ana", {"carrera": "XXXX"}, 422, "La carrera seleccionada no pertenece al catálogo oficial"),
    ("doc", {"carrera": "INFO"}, 422, "Solo los estudiantes tienen carrera"),
    ("ana", {"departamento": "Sistemas"}, 422, "Solo los docentes tienen departamento"),
])
def test_rf93_validaciones_al_editar(client, gente, quien, cambio, codigo, mensaje):
    r = client.patch(f"/admin/usuarios/{gente[quien]['id']}", json=cambio, headers=auth(gente["ta"]))
    assert r.status_code == codigo
    assert r.json()["detail"] == mensaje

def test_rf93_usuario_inexistente_y_datos_invalidos(client, gente):
    assert client.patch("/admin/usuarios/999", json={"nombre": "X"}, headers=auth(gente["ta"])).status_code == 404
    assert client.patch(f"/admin/usuarios/{gente['ana']['id']}", json={"nombre": "123"},
                        headers=auth(gente["ta"])).status_code == 422

# ------------------------------------------------------------------ RF-73, RF-92: rol de asesor
def test_rf73_asignar_y_quitar_el_rol_de_asesor(client, gente):
    url = f"/admin/usuarios/{gente['ana']['id']}/asesor"
    r = client.patch(url, json={"asesor": True}, headers=auth(gente["ta"]))
    assert r.status_code == 200, r.text
    assert sorted(r.json()["roles"]) == ["asesor", "estudiante"]
    assert client.patch(url, json={"asesor": True}, headers=auth(gente["ta"])).json()["roles"].count("asesor") == 1
    asesores = client.get("/admin/usuarios?rol=asesor", headers=auth(gente["ta"])).json()
    assert [u["id"] for u in asesores] == [gente["ana"]["id"]]
    r = client.patch(url, json={"asesor": False}, headers=auth(gente["ta"]))
    assert r.json()["roles"] == ["estudiante"]

def test_rf92_el_asesor_entra_a_su_panel_de_estudiante(client, gente):
    client.patch(f"/admin/usuarios/{gente['ana']['id']}/asesor", json={"asesor": True}, headers=auth(gente["ta"]))
    r = login(client, "123456789", "Secreto123").json()
    assert (r["panel"], sorted(r["roles"])) == ("estudiante", ["asesor", "estudiante"])

def test_rf73_solo_estudiantes_pueden_ser_asesores(client, gente):
    r = client.patch(f"/admin/usuarios/{gente['doc']['id']}/asesor", json={"asesor": True}, headers=auth(gente["ta"]))
    assert r.status_code == 409
    assert r.json()["detail"] == "Solo los estudiantes pueden tener el rol de asesor"

def test_solo_el_administrador_gestiona_usuarios(client, gente):
    alumno = alta_alumno(client, {**ALUMNO, "codigo": "111222333", "correoInstitucional": "carla@alumnos.udg.mx"})
    for t in (gente["t1"], alumno):
        assert client.patch(f"/admin/usuarios/{gente['ana']['id']}", json={"nombre": "X"}, headers=auth(t)).status_code == 403
        assert client.patch(f"/admin/usuarios/{gente['ana']['id']}/asesor", json={"asesor": True}, headers=auth(t)).status_code == 403
