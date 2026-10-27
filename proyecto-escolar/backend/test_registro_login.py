"""Módulo: registro de sesión y login (RF-01 a RF-07, RF-89 a RF-93). Ejecutar:  pytest -v"""
from datetime import date

import pytest

import config
import services
from helpers import (ALUMNO, DOCENTE, alta_alumno, alta_docente, auth, crear_admin, login,
                     registrar, token)

# ---------------------------------------------------------------- RF-01
def test_rf01_registro_exitoso_con_mensaje_y_sin_contrasena(client):
    r = registrar(client, ALUMNO)
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["mensaje"] == "Cuenta creada correctamente"
    assert cuerpo["rol"] == "estudiante" and cuerpo["estado"] == "activo"
    assert "contrasena" not in cuerpo

@pytest.mark.parametrize("cambio", [
    {"codigo": "123"},                              # el código debe tener 9 dígitos
    {"codigo": "12345678A"},
    {"nombre": "Ana123"},                           # el nombre no admite números
    {"apellidos": "   "},
    {"correoInstitucional": "ana@"},                # formato de correo
])
def test_rf01_formatos_invalidos(client, cambio):
    assert registrar(client, {**ALUMNO, **cambio}).status_code == 422

@pytest.mark.parametrize("campo", ["nombre", "apellidos", "carrera", "ciclo", "codigo", "contrasena"])
def test_rf01_campos_obligatorios(client, campo):
    datos = {k: v for k, v in ALUMNO.items() if k != campo}
    assert registrar(client, datos).status_code == 422

def test_rf01_el_codigo_se_acepta_como_numero(client):
    assert registrar(client, {**ALUMNO, "codigo": 123456789}).status_code == 201

# ---------------------------------------------------------------- RF-02
def test_rf02_carrera_y_ciclo_deben_estar_en_el_catalogo(client):
    assert registrar(client, {**ALUMNO, "carrera": "XXXX"}).status_code == 422
    assert registrar(client, {**ALUMNO, "ciclo": "1999-Z"}).status_code == 422

def test_rf02_catalogos_publicos_y_administrables(client):
    assert [c["clave"] for c in client.get("/catalogos/carreras").json()] == ["INFO"]
    assert [c["nombreOficial"] for c in client.get("/catalogos/ciclos").json()] == ["2026-B"]
    ta = crear_admin(client)
    nueva = {"clave": "icom", "nombre": "Ingeniería en Computación"}
    r = client.post("/admin/carreras", json=nueva, headers=auth(ta))
    assert r.status_code == 201 and r.json()["clave"] == "ICOM"
    assert client.post("/admin/carreras", json=nueva, headers=auth(ta)).status_code == 409
    assert registrar(client, {**ALUMNO, "carrera": "ICOM"}).status_code == 201

def test_rf02_codigo_y_correo_duplicados(client):
    registrar(client, ALUMNO)
    assert registrar(client, ALUMNO).status_code == 409
    mismo_codigo = {**ALUMNO, "correoInstitucional": "otra@alumnos.udg.mx"}
    assert registrar(client, mismo_codigo).status_code == 409
    mismo_correo = {**ALUMNO, "codigo": "111111111"}
    assert registrar(client, mismo_correo).status_code == 409

def test_rf02_el_ciclo_del_estudiante_es_el_que_esta_en_curso(client):
    ta = crear_admin(client)
    assert client.get("/catalogos/ciclo-actual").json()["nombreOficial"] == "2026-B"
    client.post("/admin/ciclos", json={"nombreOficial": "2026-A"}, headers=auth(ta))   # ya terminó
    r = registrar(client, {**ALUMNO, "ciclo": "2026-A"})
    assert r.status_code == 422 and "2026-B" in str(r.json())
    assert registrar(client, {**ALUMNO, "ciclo": "2026-b"}).status_code == 201         # sin distinguir mayúsculas

def test_rf02_entre_dos_ciclos_se_usa_el_siguiente(client, monkeypatch):
    ta = crear_admin(client)
    monkeypatch.setattr(services, "hoy", lambda: date(2026, 12, 20))   # 17-dic a 15-ene: no hay ciclo en curso
    assert client.get("/catalogos/ciclo-actual").status_code == 404
    assert registrar(client, ALUMNO).status_code == 409                # aún no hay ciclo próximo registrado
    client.post("/admin/ciclos", json={"nombreOficial": "2027-A"}, headers=auth(ta))
    assert client.get("/catalogos/ciclo-actual").json()["nombreOficial"] == "2027-A"
    assert registrar(client, {**ALUMNO, "ciclo": "2027-A"}).status_code == 201

# ---------------------------------------------------------------- RF-03
@pytest.mark.parametrize("contrasena", ["Corta1A", "sinmayuscula1", "SINMINUSCULA1", "SinNumeros"])
def test_rf03_criterios_de_contrasena(client, contrasena):
    datos = {**ALUMNO, "contrasena": contrasena, "confirmarContrasena": contrasena}
    assert registrar(client, datos).status_code == 422

def test_rf03_la_confirmacion_debe_coincidir(client):
    r = registrar(client, {**ALUMNO, "confirmarContrasena": "Distinta123"})
    assert r.status_code == 422
    assert "no coinciden" in str(r.json()["errores"])

def test_rf03_no_se_crea_cuenta_si_hay_datos_invalidos(client):
    registrar(client, {**ALUMNO, "contrasena": "x", "confirmarContrasena": "x"})
    assert login(client, ALUMNO["codigo"], "Secreto123").status_code == 401

# ---------------------------------------------------------------- RF-04
def test_rf04_login_con_codigo_y_contrasena(client):
    registrar(client, ALUMNO)
    r = login(client, ALUMNO["codigo"], ALUMNO["contrasena"])
    assert r.status_code == 200
    assert r.json()["roles"] == ["estudiante"] and r.json()["panel"] == "estudiante"

def test_rf04_campos_vacios_dan_mensaje_especifico(client):
    r = client.post("/usuarios/login", json={"codigo": "", "contrasena": ""})
    assert r.status_code == 422
    errores = {e["campo"]: e["mensaje"] for e in r.json()["errores"]}
    assert errores == {"codigo": "Este campo es obligatorio", "contrasena": "Este campo es obligatorio"}

def test_rf04_datos_incorrectos_no_revelan_cual_fallo(client):
    registrar(client, ALUMNO)
    mala_contrasena = login(client, ALUMNO["codigo"], "Incorrecta1")
    codigo_inexistente = login(client, "000000000", "Secreto123")
    assert mala_contrasena.status_code == codigo_inexistente.status_code == 401
    assert mala_contrasena.json() == codigo_inexistente.json()

# ---------------------------------------------------------------- RF-05
def test_rf05_acceso_protegido(client):
    assert client.get("/usuarios/yo").status_code in (401, 403)
    assert client.get("/cursos").status_code in (401, 403)
    t = alta_alumno(client)
    yo = client.get("/usuarios/yo", headers=auth(t)).json()
    assert yo["codigo"] == ALUMNO["codigo"] and yo["roles"] == ["estudiante"] and yo["panel"] == "estudiante"
    assert "contrasena" not in yo

def test_rf05_token_alterado_no_sirve(client):
    t = alta_alumno(client)
    assert client.get("/usuarios/yo", headers=auth(t[:-3] + "abc")).status_code == 401

# ---------------------------------------------------------------- RF-06 / RF-91
def test_rf06_logout_invalida_la_sesion(client):
    t = alta_alumno(client)
    assert client.post("/usuarios/logout", headers=auth(t)).status_code == 200
    assert client.get("/usuarios/yo", headers=auth(t)).status_code == 401
    # se puede volver a entrar con una sesión nueva
    t2 = token(client, ALUMNO["codigo"], ALUMNO["contrasena"])
    assert client.get("/usuarios/yo", headers=auth(t2)).status_code == 200

def test_rf06_las_respuestas_no_se_guardan_en_cache(client):
    t = alta_alumno(client)
    assert client.get("/usuarios/yo", headers=auth(t)).headers["cache-control"] == "no-store"

# ---------------------------------------------------------------- RF-07
def test_rf07_mensaje_de_recuperacion_manual(client):
    r = client.get("/usuarios/recuperar-contrasena")
    assert r.status_code == 200 and "coordinador" in r.json()["mensaje"]

def test_rf07_el_administrador_restablece_la_contrasena(client):
    alta_alumno(client)
    ta = crear_admin(client)
    uid = client.get("/admin/usuarios?rol=estudiante", headers=auth(ta)).json()[0]["id"]
    r = client.patch(f"/admin/usuarios/{uid}/contrasena", json={"nueva_contrasena": "Nueva12345"},
                     headers=auth(ta))
    assert r.status_code == 200
    assert login(client, ALUMNO["codigo"], ALUMNO["contrasena"]).status_code == 401
    assert login(client, ALUMNO["codigo"], "Nueva12345").status_code == 200
    malo = client.patch(f"/admin/usuarios/{uid}/contrasena", json={"nueva_contrasena": "debil"},
                        headers=auth(ta))
    assert malo.status_code == 422

# ---------------------------------------------------------------- dominios de correo y roles
@pytest.mark.parametrize("correo", [
    "ana@gmail.com", "ana@escuela.mx",
    "ana@evil-alumnos.udg.mx",        # termina parecido, pero no es el dominio
    "ana@alumnos.udg.mx.evil.com",    # contiene el dominio, pero no es el dominio
])
def test_correos_fuera_de_dominio_se_rechazan(client, correo):
    assert registrar(client, {**ALUMNO, "correoInstitucional": correo}).status_code == 422

def test_mayusculas_en_el_correo_no_crean_cuentas_distintas(client):
    registrar(client, {**ALUMNO, "correoInstitucional": "ANA@Alumnos.UDG.mx"})
    assert registrar(client, ALUMNO).status_code == 409

def test_faltan_datos_segun_el_rol(client):
    sin_empleado = {k: v for k, v in DOCENTE.items() if k != "noEmpleado"}
    assert registrar(client, sin_empleado).status_code == 422

def test_docente_por_dominio_y_aprobacion(client):
    if not config.DOCENTE_REQUIERE_APROBACION:
        pytest.skip("La aprobación de docentes está desactivada")
    r = registrar(client, DOCENTE)
    assert r.status_code == 201 and r.json()["rol"] == "docente" and r.json()["estado"] == "pendiente"
    assert login(client, "D-001", DOCENTE["contrasena"]).status_code == 403

    ta = crear_admin(client)
    pendientes = client.get("/admin/usuarios?estado=pendiente", headers=auth(ta)).json()
    assert [u["correoInstitucional"] for u in pendientes] == ["luis@academicos.udg.mx"]
    aprobado = client.patch(f"/admin/usuarios/{pendientes[0]['id']}/estado",
                            json={"estado": "activo"}, headers=auth(ta))
    assert aprobado.status_code == 200
    ok = login(client, "d-001", DOCENTE["contrasena"])  # el código no distingue mayúsculas
    assert ok.status_code == 200 and ok.json()["roles"] == ["docente"]

# ---------------------------------------------------------------- RF-90 / RF-93
def test_rf90_cada_rol_va_a_su_panel(client):
    ta = crear_admin(client)
    alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    alta_alumno(client)
    assert login(client, "A-001", "Admin12345").json()["panel"] == "administrador"
    assert login(client, "D-1", "Docente123").json()["panel"] == "docente"
    assert login(client, ALUMNO["codigo"], ALUMNO["contrasena"]).json()["panel"] == "estudiante"

def test_rf93_solo_el_administrador_gestiona_usuarios(client):
    t = alta_alumno(client)
    assert client.get("/admin/usuarios", headers=auth(t)).status_code == 403

def test_rf93_admin_solo_crea_docentes_con_correo_academico(client):
    ta = crear_admin(client)
    r = client.post("/admin/docentes", headers=auth(ta), json={
        "nombre": "X", "apellidos": "Y", "correoInstitucional": "x@gmail.com",
        "contrasena": "Docente123", "noEmpleado": "D-7"})
    assert r.status_code == 422

def test_rf93_desactivar_cuentas(client):
    ta = crear_admin(client)
    alta_alumno(client)
    yo = client.get("/admin/usuarios?rol=administrador", headers=auth(ta)).json()[0]["id"]
    assert client.patch(f"/admin/usuarios/{yo}/estado", json={"estado": "inactivo"},
                        headers=auth(ta)).status_code == 409
    alumno = client.get("/admin/usuarios?rol=estudiante", headers=auth(ta)).json()[0]["id"]
    assert client.patch(f"/admin/usuarios/{alumno}/estado", json={"estado": "inactivo"},
                        headers=auth(ta)).status_code == 200
    assert login(client, ALUMNO["codigo"], ALUMNO["contrasena"]).status_code == 403
