"""Módulo de actividades (RF-29, RF-30, RF-33 a RF-36) y archivos adjuntos (RNF-8)."""
from datetime import datetime

import pytest

import models
import services
from config import TAMANO_MAXIMO_ARCHIVO
from helpers import ALUMNO, ALUMNO_B, CURSO, Sesion, alta_alumno, alta_docente, auth, crear_admin

AHORA = datetime(2026, 10, 25, 12, 0)
PDF = ("instrucciones.pdf", b"%PDF-1.4 contenido de prueba", "application/pdf")

@pytest.fixture(autouse=True)
def carpeta_temporal(monkeypatch, tmp_path):
    """Los archivos de las pruebas van a una carpeta temporal, no a uploads/."""
    monkeypatch.setattr(services, "CARPETA_ARCHIVOS", tmp_path)
    monkeypatch.setattr(services, "ahora", lambda: AHORA)
    return tmp_path

@pytest.fixture()
def curso(client):
    """Curso de t1 con las categorías Tareas (40 %) y Exámenes (60 %); Ana inscrita."""
    ta = crear_admin(client)
    t1 = alta_docente(client, ta, "d1@academicos.udg.mx", "D-1")
    t2 = alta_docente(client, ta, "d2@academicos.udg.mx", "D-2")
    c = client.post("/cursos", json=CURSO, headers=auth(t1)).json()
    url = f"/docente/cursos/{c['id']}"
    cats = {}
    for nombre, peso in (("Tareas", 40), ("Exámenes", 60)):
        r = client.post(f"{url}/categorias", json={"nombre": nombre, "porcentajePeso": peso}, headers=auth(t1))
        cats[nombre] = r.json()["categoria"]["id"]
    ana = alta_alumno(client, ALUMNO)
    client.post("/inscripcion", json={"codigoCurso": c["codigoCurso"]}, headers=auth(ana))
    return {"ta": ta, "t1": t1, "t2": t2, "id": c["id"], "url": f"{url}/actividades",
            "tareas": cats["Tareas"], "examenes": cats["Exámenes"], "ana": ana}

def _crear(client, cur, categoria="tareas", **cambios):
    datos = {"categoriaEvaluacion_id": cur[categoria], "titulo": "Tarea 1", "descripcion": "Resolver ejercicios",
             "fechaHoraLimite": "2026-11-01T23:59:00", "puntuacionMaxima": 10, **cambios}
    return client.post(cur["url"], json=datos, headers=auth(cur["t1"]))

def _subir(client, cur, actividad_id, archivo=PDF, t=None):
    return client.put(f"{cur['url']}/{actividad_id}/archivo", files={"archivo": archivo},
                      headers=auth(t or cur["t1"]))

# ------------------------------------------------------------------ crear, listar, editar y eliminar
def test_crear_actividad(client, curso):
    r = _crear(client, curso)
    assert r.status_code == 201, r.text
    a = r.json()
    assert (a["titulo"], a["categoria"], a["fechaHoraLimite"], a["puntuacionMaxima"]) == \
           ("Tarea 1", "Tareas", "2026-11-01T23:59:00", 10)
    assert (a["valorEnCurso"], a["tieneArchivo"]) == (40, False)

def test_la_descripcion_es_opcional(client, curso):
    r = _crear(client, curso, descripcion=None)
    assert r.status_code == 201
    assert r.json()["descripcion"] is None

@pytest.mark.parametrize("cambio", [
    {"titulo": ""},
    {"puntuacionMaxima": 0},
    {"puntuacionMaxima": -5},
    {"fechaHoraLimite": "mañana"},
    {"categoriaEvaluacion_id": None},
])
def test_datos_invalidos(client, curso, cambio):
    assert _crear(client, curso, **cambio).status_code == 422

def test_la_fecha_limite_debe_ser_futura(client, curso):
    r = _crear(client, curso, fechaHoraLimite="2026-10-25T11:59:00")
    assert r.status_code == 422
    assert r.json()["detail"] == "La fecha límite debe ser posterior a la fecha y hora actuales"

def test_la_categoria_debe_ser_del_curso(client, curso):
    otro = client.post("/cursos", json={**CURSO, "seccion": "D02"}, headers=auth(curso["t1"])).json()
    ajena = client.post(f"/docente/cursos/{otro['id']}/categorias", json={"nombre": "X", "porcentajePeso": 10},
                        headers=auth(curso["t1"])).json()["categoria"]["id"]
    r = _crear(client, curso, categoriaEvaluacion_id=ajena)
    assert r.status_code == 404
    assert r.json()["detail"] == "Categoría no encontrada"

def test_no_se_crean_actividades_en_un_curso_archivado(client, curso):
    client.patch(f"/docente/cursos/{curso['id']}/estado", json={"estado": "archivado"}, headers=auth(curso["t1"]))
    r = _crear(client, curso)
    assert r.status_code == 409
    assert r.json()["detail"] == "El curso está archivado"

def test_listar_por_fecha_limite(client, curso):
    _crear(client, curso, titulo="Tarea 2", fechaHoraLimite="2026-11-10T23:59:00")
    _crear(client, curso, "examenes", titulo="Parcial", fechaHoraLimite="2026-11-05T08:00:00", puntuacionMaxima=100)
    _crear(client, curso, titulo="Tarea 1")
    r = client.get(curso["url"], headers=auth(curso["t1"]))
    assert r.status_code == 200
    assert [a["titulo"] for a in r.json()] == ["Tarea 1", "Parcial", "Tarea 2"]

def test_editar_actividad(client, curso):
    aid = _crear(client, curso).json()["id"]
    r = client.patch(f"{curso['url']}/{aid}", headers=auth(curso["t1"]), json={
        "titulo": "Tarea 1 (corregida)", "fechaHoraLimite": "2026-11-03T12:00:00",
        "categoriaEvaluacion_id": curso["examenes"]})
    assert r.status_code == 200, r.text
    a = r.json()
    assert (a["titulo"], a["fechaHoraLimite"], a["categoria"], a["puntuacionMaxima"]) == \
           ("Tarea 1 (corregida)", "2026-11-03T12:00:00", "Exámenes", 10)
    assert client.patch(f"{curso['url']}/{aid}", json={"fechaHoraLimite": "2026-10-01T00:00:00"},
                        headers=auth(curso["t1"])).status_code == 422
    r = client.get(f"{curso['url']}/{aid}", headers=auth(curso["t1"]))
    assert r.json()["titulo"] == "Tarea 1 (corregida)"

def test_eliminar_actividad(client, curso, carpeta_temporal):
    aid = _crear(client, curso).json()["id"]
    _crear(client, curso, titulo="Tarea 2")
    _subir(client, curso, aid)
    r = client.delete(f"{curso['url']}/{aid}", headers=auth(curso["t1"]))
    assert r.status_code == 200
    assert [(a["titulo"], a["valorEnCurso"]) for a in r.json()] == [("Tarea 2", 40)]
    assert list(carpeta_temporal.rglob("*.pdf")) == []  # también se borra su archivo
    assert client.get(f"{curso['url']}/{aid}", headers=auth(curso["t1"])).status_code == 404

def test_no_se_elimina_una_actividad_con_entregas(client, curso):
    aid = _crear(client, curso).json()["id"]
    with Sesion() as db:
        matricula = db.query(models.Matricula).first()
        db.add(models.Entrega(actividad_id=aid, matricula_id=matricula.id,
                              fechaHoraEntrega="2026-10-26T10:00:00", entregadoConRetraso=0))
        db.commit()
    r = client.delete(f"{curso['url']}/{aid}", headers=auth(curso["t1"]))
    assert r.status_code == 409
    assert r.json()["detail"] == "No se puede eliminar una actividad que ya tiene entregas"

# ------------------------------------------------------------------ RF-34: mismo valor dentro de la categoría
def test_rf34_las_actividades_se_reparten_el_peso_de_su_categoria(client, curso):
    for i in range(3):
        _crear(client, curso, titulo=f"Tarea {i + 1}", puntuacionMaxima=10 * (i + 1))
    _crear(client, curso, "examenes", titulo="Parcial", puntuacionMaxima=100)
    valores = {a["titulo"]: a["valorEnCurso"] for a in client.get(curso["url"], headers=auth(curso["t1"])).json()}
    # El valor no depende de la puntuación máxima: 40 % / 3 tareas y 60 % / 1 examen
    assert valores == {"Tarea 1": 13.33, "Tarea 2": 13.33, "Tarea 3": 13.33, "Parcial": 60}
    with Sesion() as db:
        assert sum(services.valores_actividades(db, curso["id"]).values()) == pytest.approx(100)

# ------------------------------------------------------------------ RF-36 / RNF-8: archivo del docente
def test_rf36_adjuntar_y_descargar_archivo(client, curso):
    aid = _crear(client, curso).json()["id"]
    r = _subir(client, curso, aid)
    assert r.status_code == 200, r.text
    assert r.json()["tieneArchivo"] is True
    for t in (curso["t1"], curso["ana"]):  # el docente y un alumno inscrito
        r = client.get(f"/actividades/{aid}/archivo", headers=auth(t))
        assert r.status_code == 200
        assert r.content == PDF[1]
        assert r.headers["content-disposition"].startswith("attachment")

def test_rf36_reemplazar_y_quitar_el_archivo(client, curso, carpeta_temporal):
    aid = _crear(client, curso).json()["id"]
    _subir(client, curso, aid)
    _subir(client, curso, aid, ("guia.zip", b"PK\x03\x04zip", "application/zip"))
    assert [p.suffix for p in carpeta_temporal.rglob("*.*")] == [".zip"]  # el PDF anterior se borró
    r = client.delete(f"{curso['url']}/{aid}/archivo", headers=auth(curso["t1"]))
    assert r.status_code == 200
    assert r.json()["tieneArchivo"] is False
    assert list(carpeta_temporal.rglob("*.*")) == []
    r = client.get(f"/actividades/{aid}/archivo", headers=auth(curso["t1"]))
    assert r.status_code == 404
    assert r.json()["detail"] == "La actividad no tiene archivo adjunto"

@pytest.mark.parametrize("nombre", ["foto.PNG", "a.jpg", "a.jpeg", "a.gif", "a.doc", "a.docx", "a.zip", "a.pdf"])
def test_rnf8_tipos_permitidos(client, curso, nombre):
    aid = _crear(client, curso).json()["id"]
    assert _subir(client, curso, aid, (nombre, b"datos", "application/octet-stream")).status_code == 200

@pytest.mark.parametrize("nombre", ["virus.exe", "pagina.html", "script.js", "sin_extension", "a.pdf.exe"])
def test_rnf8_tipos_no_permitidos(client, curso, nombre):
    aid = _crear(client, curso).json()["id"]
    r = _subir(client, curso, aid, (nombre, b"datos", "application/octet-stream"))
    assert r.status_code == 415
    assert r.json()["detail"].startswith("Tipo de archivo no permitido")

def test_rnf8_tamano_maximo_10_mb(client, curso, carpeta_temporal):
    aid = _crear(client, curso).json()["id"]
    assert _subir(client, curso, aid, ("max.pdf", b"x" * TAMANO_MAXIMO_ARCHIVO, "application/pdf")).status_code == 200
    r = _subir(client, curso, aid, ("grande.pdf", b"x" * (TAMANO_MAXIMO_ARCHIVO + 1), "application/pdf"))
    assert r.status_code == 413
    assert r.json()["detail"] == "El archivo supera el tamaño máximo de 10 MB"
    assert len(list(carpeta_temporal.rglob("*.pdf"))) == 1  # el rechazado no se guardó

def test_rnf8_archivo_vacio(client, curso):
    aid = _crear(client, curso).json()["id"]
    r = _subir(client, curso, aid, ("vacio.pdf", b"", "application/pdf"))
    assert r.status_code == 422
    assert r.json()["detail"] == "El archivo está vacío"

def test_rf36_quien_no_es_del_curso_no_descarga(client, curso):
    aid = _crear(client, curso).json()["id"]
    _subir(client, curso, aid)
    beto = alta_alumno(client, ALUMNO_B)  # no inscrito
    for t in (beto, curso["t2"], curso["ta"]):
        r = client.get(f"/actividades/{aid}/archivo", headers=auth(t))
        assert r.status_code == 403
        assert r.json()["detail"] == "No tienes acceso a esta actividad"
    assert client.get("/actividades/999/archivo", headers=auth(curso["t1"])).status_code == 404

# ------------------------------------------------------------------ RF-95: solo el docente creador
def test_rf95_solo_el_docente_creador_crea_tareas(client, curso):
    aid = _crear(client, curso).json()["id"]
    cuerpo = {"categoriaEvaluacion_id": curso["tareas"], "titulo": "X",
              "fechaHoraLimite": "2026-11-01T23:59:00", "puntuacionMaxima": 10}
    for t in (curso["t2"], curso["ta"], curso["ana"]):
        assert client.get(curso["url"], headers=auth(t)).status_code == 403
        assert client.post(curso["url"], json=cuerpo, headers=auth(t)).status_code == 403
        assert client.get(f"{curso['url']}/{aid}", headers=auth(t)).status_code == 403
        assert client.patch(f"{curso['url']}/{aid}", json={"titulo": "Y"}, headers=auth(t)).status_code == 403
        assert client.delete(f"{curso['url']}/{aid}", headers=auth(t)).status_code == 403
        assert _subir(client, curso, aid, t=t).status_code == 403
        assert client.delete(f"{curso['url']}/{aid}/archivo", headers=auth(t)).status_code == 403

def test_actividad_de_otro_curso_no_se_encuentra(client, curso):
    aid = _crear(client, curso).json()["id"]
    otro = client.post("/cursos", json={**CURSO, "seccion": "D02"}, headers=auth(curso["t1"])).json()
    r = client.get(f"/docente/cursos/{otro['id']}/actividades/{aid}", headers=auth(curso["t1"]))
    assert r.status_code == 404
    assert r.json()["detail"] == "Actividad no encontrada"
