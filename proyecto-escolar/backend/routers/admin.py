from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
import services
from database import get_db
from security import requiere_admin

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.post("/docentes", response_model=schemas.UsuarioSalida, status_code=201)
def crear_docente(datos: schemas.DocenteCrear, db: Session = Depends(get_db),
                  _: models.Usuario = Depends(requiere_admin)):
    return services.crear_docente(db, datos)

@router.post("/administradores", response_model=schemas.UsuarioSalida, status_code=201)
def crear_administrador(datos: schemas.AdminCrear, db: Session = Depends(get_db),
                        _: models.Usuario = Depends(requiere_admin)):
    return services.crear_administrador(db, datos)

@router.get("/usuarios", response_model=list[schemas.UsuarioAdminSalida])
def listar_usuarios(rol: Literal["estudiante", "docente", "administrador"] | None = None,
                    estado: Literal["activo", "inactivo", "pendiente"] | None = None,
                    db: Session = Depends(get_db), _: models.Usuario = Depends(requiere_admin)):
    return services.listar_usuarios(db, rol, estado)

@router.patch("/usuarios/{usuario_id}/estado", response_model=schemas.UsuarioAdminSalida)
def cambiar_estado_usuario(usuario_id: int, datos: schemas.EstadoUsuario,
                           db: Session = Depends(get_db),
                           admin: models.Usuario = Depends(requiere_admin)):
    return services.cambiar_estado_usuario(db, admin, usuario_id, datos.estado)

@router.patch("/usuarios/{usuario_id}/contrasena")
def restablecer_contrasena(usuario_id: int, datos: schemas.NuevaContrasena,
                           db: Session = Depends(get_db), _: models.Usuario = Depends(requiere_admin)):
    services.recuperarContrasena(db, usuario_id, datos.nueva_contrasena)
    return {"mensaje": "Contraseña restablecida correctamente"}

@router.post("/carreras", response_model=schemas.CarreraSalida, status_code=201)
def crear_carrera(datos: schemas.CarreraCrear, db: Session = Depends(get_db),
                  _: models.Usuario = Depends(requiere_admin)):
    return services.crear_carrera(db, datos)

@router.post("/ciclos", response_model=schemas.CicloSalida, status_code=201)
def crear_ciclo(datos: schemas.CicloCrear, db: Session = Depends(get_db),
                _: models.Usuario = Depends(requiere_admin)):
    return services.crearCiclo(db, datos)

@router.get("/cursos", response_model=list[schemas.CursoSalida])
def listar_todos_los_cursos(db: Session = Depends(get_db), _: models.Usuario = Depends(requiere_admin)):
    return db.query(models.Curso).order_by(models.Curso.id).all()

@router.patch("/cursos/{curso_id}/docente", response_model=schemas.CursoSalida)
def reasignar_docente(curso_id: int, datos: schemas.ReasignarDocente,
                      db: Session = Depends(get_db), _: models.Usuario = Depends(requiere_admin)):
    return services.reasignar_docente(db, curso_id, datos.docente_id)
