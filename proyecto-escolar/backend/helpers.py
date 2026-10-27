"""Datos y utilidades compartidas por las pruebas (base de datos temporal en memoria)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
import schemas
import services

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Sesion = sessionmaker(bind=engine, autoflush=False)

def db_de_prueba():
    db = Sesion()
    try:
        yield db
    finally:
        db.close()

def sembrar_base():
    """Catálogos mínimos: carrera INFO y ciclo 2026-B (id 1). Las pruebas fijan la fecha en 25/oct/2026."""
    with Sesion() as db:
        db.add(models.Carrera(clave="INFO", nombre="Ingeniería Informática"))
        db.add(models.CicloEscolar(nombreOficial="2026-B", fechaInicio="2026-07-16",
                                   fechaTermino="2026-12-16", estado="activo"))
        db.commit()

ALUMNO = {"codigo": "123456789", "nombre": "Ana", "apellidos": "López", "carrera": "INFO",
          "ciclo": "2026-B", "correoInstitucional": "ana@alumnos.udg.mx",
          "contrasena": "Secreto123", "confirmarContrasena": "Secreto123"}
ALUMNO_B = {**ALUMNO, "codigo": "987654321", "nombre": "Beto", "correoInstitucional": "beto@alumnos.udg.mx"}
DOCENTE = {"nombre": "Luis", "apellidos": "Pérez", "correoInstitucional": "luis@academicos.udg.mx",
           "contrasena": "Docente123", "confirmarContrasena": "Docente123",
           "noEmpleado": "D-001", "departamento": "Sistemas"}
CURSO = {"nombreMateria": "Bases de datos", "seccion": "D01", "descripcion": "Curso de SQL",
         "cicloEscolar_id": 1, "tipoEvaluacion": "numerica", "diasSemana": ["lunes", "miercoles"],
         "horaInicio": "08:00", "horaFin": "10:00"}

def auth(token):
    return {"Authorization": f"Bearer {token}"}

def login(client, codigo, contrasena):
    return client.post("/usuarios/login", json={"codigo": codigo, "contrasena": contrasena})

def token(client, codigo, contrasena):
    r = login(client, codigo, contrasena)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

def registrar(client, datos):
    return client.post("/usuarios/registro", json=datos)

def crear_admin(client):
    with Sesion() as db:
        services.crear_administrador(db, schemas.AdminCrear(
            nombre="Root", apellidos="Admin", correoInstitucional="admin@escuela.mx",
            contrasena="Admin12345", noEmpleado="A-001"))
    return token(client, "A-001", "Admin12345")

def alta_docente(client, ta, correo, no_empleado):
    r = client.post("/admin/docentes", headers=auth(ta), json={
        "nombre": "Doc", "apellidos": "Ente", "correoInstitucional": correo,
        "contrasena": "Docente123", "noEmpleado": no_empleado, "departamento": "Sistemas"})
    assert r.status_code == 201, r.text
    return token(client, no_empleado, "Docente123")

def alta_alumno(client, datos=ALUMNO):
    assert registrar(client, datos).status_code == 201
    return token(client, datos["codigo"], datos["contrasena"])
