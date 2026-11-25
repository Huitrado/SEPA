"""Seguridad de la sesión: cierre por inactividad (RNF-02) y bloqueo por intentos fallidos (RNF-03)."""
from datetime import datetime, timedelta, timezone

import pytest

import models
import security
from helpers import ALUMNO, Sesion, alta_alumno, auth, login, token

@pytest.fixture()
def reloj(client, monkeypatch):
    """Hora UTC que cada prueba puede mover: reloj["ahora"] += timedelta(...).
    Parte de la hora real porque PyJWT revisa "exp" contra el reloj del sistema."""
    hora = {"ahora": datetime.now(timezone.utc)}
    monkeypatch.setattr(security, "ahora_utc", lambda: hora["ahora"])
    return hora

def _fallar(client, veces, codigo=ALUMNO["codigo"]):
    return [login(client, codigo, "Incorrecta1") for _ in range(veces)]

# ---------------------------------------------------------------- RNF-02
def test_rnf02_la_sesion_se_cierra_tras_30_minutos_sin_actividad(client, reloj):
    t = alta_alumno(client)
    reloj["ahora"] += timedelta(minutes=30, seconds=1)
    r = client.get("/usuarios/yo", headers=auth(t))
    assert r.status_code == 401
    assert r.json()["detail"] == "Tu sesión se cerró por inactividad; inicia sesión de nuevo"
    # ya cerrada, no revive aunque se vuelva a intentar
    assert client.get("/usuarios/yo", headers=auth(t)).status_code == 401

def test_rnf02_cada_peticion_renueva_el_plazo(client, reloj):
    t = alta_alumno(client)
    for _ in range(4):  # 4 peticiones separadas por 25 min: 1 h 40 min en total sin cortarse
        reloj["ahora"] += timedelta(minutes=25)
        assert client.get("/usuarios/yo", headers=auth(t)).status_code == 200
    reloj["ahora"] += timedelta(minutes=30)  # justo 30 min todavía cuenta como activa
    assert client.get("/usuarios/yo", headers=auth(t)).status_code == 200

def test_rnf02_la_inactividad_es_por_sesion(client, reloj):
    vieja = alta_alumno(client)
    reloj["ahora"] += timedelta(minutes=31)
    nueva = token(client, ALUMNO["codigo"], ALUMNO["contrasena"])
    assert client.get("/usuarios/yo", headers=auth(vieja)).status_code == 401
    assert client.get("/usuarios/yo", headers=auth(nueva)).status_code == 200

def test_rnf02_el_logout_borra_la_sesion_activa(client, reloj):
    t = alta_alumno(client)
    assert client.post("/usuarios/logout", headers=auth(t)).status_code == 200
    with Sesion() as db:
        assert db.query(models.SesionActiva).count() == 0

def test_rnf02_al_iniciar_sesion_se_limpian_las_sesiones_vencidas(client, reloj):
    alta_alumno(client)  # una sesión que nunca se cerró
    reloj["ahora"] += timedelta(hours=security.HORAS_SESION, minutes=1)
    token(client, ALUMNO["codigo"], ALUMNO["contrasena"])
    with Sesion() as db:
        assert db.query(models.SesionActiva).count() == 1

# ---------------------------------------------------------------- RNF-03
def test_rnf03_cinco_intentos_fallidos_bloquean_15_minutos(client, reloj):
    alta_alumno(client)
    respuestas = _fallar(client, 5)
    assert [r.status_code for r in respuestas] == [401, 401, 401, 401, 429]
    assert "15 minutos" in respuestas[-1].json()["detail"]
    # bloqueada aunque ahora la contraseña sea la correcta
    r = login(client, ALUMNO["codigo"], ALUMNO["contrasena"])
    assert r.status_code == 429 and "Demasiados intentos fallidos" in r.json()["detail"]
    reloj["ahora"] += timedelta(minutes=10)
    assert "5 minutos" in login(client, ALUMNO["codigo"], ALUMNO["contrasena"]).json()["detail"]

def test_rnf03_el_bloqueo_termina_a_los_15_minutos(client, reloj):
    alta_alumno(client)
    _fallar(client, 5)
    reloj["ahora"] += timedelta(minutes=14, seconds=59)
    assert login(client, ALUMNO["codigo"], ALUMNO["contrasena"]).status_code == 429
    reloj["ahora"] += timedelta(seconds=1)
    assert login(client, ALUMNO["codigo"], ALUMNO["contrasena"]).status_code == 200

def test_rnf03_tras_el_bloqueo_se_cuenta_de_cero(client, reloj):
    alta_alumno(client)
    _fallar(client, 5)
    reloj["ahora"] += timedelta(minutes=15)
    assert [r.status_code for r in _fallar(client, 4)] == [401] * 4
    assert _fallar(client, 1)[0].status_code == 429

def test_rnf03_un_acceso_correcto_reinicia_el_conteo(client, reloj):
    alta_alumno(client)
    _fallar(client, 4)
    token(client, ALUMNO["codigo"], ALUMNO["contrasena"])
    assert [r.status_code for r in _fallar(client, 4)] == [401] * 4  # no consecutivos: no bloquea

def test_rnf03_el_bloqueo_es_por_cuenta(client, reloj):
    alta_alumno(client)
    _fallar(client, 5, codigo="999999999")  # otra cuenta (ni siquiera existe)
    assert login(client, ALUMNO["codigo"], ALUMNO["contrasena"]).status_code == 200

def test_rnf03_no_revela_si_el_codigo_existe(client, reloj):
    alta_alumno(client)
    existe = _fallar(client, 5)
    no_existe = _fallar(client, 5, codigo="999999999")
    assert [r.status_code for r in existe] == [r.status_code for r in no_existe]
    assert existe[-1].json() == no_existe[-1].json()

def test_rnf03_el_codigo_no_distingue_mayusculas(client, reloj):
    _fallar(client, 3, codigo="d-001")
    _fallar(client, 1, codigo="D-001")
    assert _fallar(client, 1, codigo="d-001")[0].status_code == 429
