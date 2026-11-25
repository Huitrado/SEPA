from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends
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
def listar_usuarios(rol: Literal["estudiante", "docente", "administrador", "asesor"] | None = None,
                    estado: Literal["activo", "inactivo", "pendiente"] | None = None,
                    db: Session = Depends(get_db), _: models.Usuario = Depends(requiere_admin)):
    return services.listar_usuarios(db, rol, estado)

@router.patch("/usuarios/{usuario_id}/estado", response_model=schemas.UsuarioAdminSalida)
def cambiar_estado_usuario(usuario_id: int, datos: schemas.EstadoUsuario,
                           db: Session = Depends(get_db),
                           admin: models.Usuario = Depends(requiere_admin)):
    return services.cambiar_estado_usuario(db, admin, usuario_id, datos.estado)

@router.patch("/usuarios/{usuario_id}", response_model=schemas.UsuarioAdminSalida)
def editar_usuario(usuario_id: int, datos: schemas.UsuarioAdminActualizar, db: Session = Depends(get_db),
                   _: models.Usuario = Depends(requiere_admin)):
    return services.actualizar_usuario(db, usuario_id, datos)

@router.patch("/usuarios/{usuario_id}/asesor", response_model=schemas.UsuarioAdminSalida)
def cambiar_rol_asesor(usuario_id: int, datos: schemas.RolAsesor, db: Session = Depends(get_db),
                       _: models.Usuario = Depends(requiere_admin)):
    return services.cambiar_rol_asesor(db, usuario_id, datos.asesor)

@router.get("/solicitudes-asesor", response_model=list[schemas.SolicitudAsesorSalida])
def listar_solicitudes_asesor(estado: Literal["pendiente", "aceptada", "rechazada"] | None = None,
                              db: Session = Depends(get_db), _: models.Usuario = Depends(requiere_admin)):
    return services.listar_solicitudes_asesor(db, estado)

@router.patch("/solicitudes-asesor/{solicitud_id}", response_model=schemas.SolicitudAsesorSalida)
def responder_solicitud_asesor(solicitud_id: int, datos: schemas.SolicitudAsesorRespuesta,
                               db: Session = Depends(get_db), admin: models.Usuario = Depends(requiere_admin)):
    return services.responder_solicitud_asesor(db, admin, solicitud_id, datos)

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

# ------------------------------------------------------------------ catálogo de materias (RF-94)
@router.post("/materias", response_model=schemas.MateriaSalida, status_code=201)
def crear_materia(datos: schemas.MateriaCrear, db: Session = Depends(get_db),
                  _: models.Usuario = Depends(requiere_admin)):
    return services.crear_materia(db, datos)

@router.patch("/materias/{materia_id}", response_model=schemas.MateriaSalida)
def editar_materia(materia_id: int, datos: schemas.MateriaActualizar, db: Session = Depends(get_db),
                   _: models.Usuario = Depends(requiere_admin)):
    return services.actualizar_materia(db, materia_id, datos)

@router.delete("/materias/{materia_id}")
def eliminar_materia(materia_id: int, db: Session = Depends(get_db), _: models.Usuario = Depends(requiere_admin)):
    services.eliminar_materia(db, materia_id)
    return {"mensaje": "Materia eliminada correctamente"}


# ------------------------------------------------------------------ riesgo académico y planes de estudio
@router.post("/riesgo/recalcular", status_code=202)
def recalcular_riesgo(tareas: BackgroundTasks, _: models.Usuario = Depends(requiere_admin)):
    """RF-53: pasa al historial los ciclos cerrados y analiza el riesgo, en segundo plano (RNF-05)."""
    tareas.add_task(services.analizar_riesgo_en_segundo_plano)
    return {"mensaje": "El análisis de riesgo académico se está ejecutando en segundo plano"}

@router.get("/mallas", response_model=list[schemas.MallaSalida])
def listar_mallas(db: Session = Depends(get_db), _: models.Usuario = Depends(requiere_admin)):
    return services.listar_mallas(db)

@router.put("/mallas/{malla_id}/materias", status_code=204)
def asignar_materia(malla_id: int, datos: schemas.MateriaEnMalla, db: Session = Depends(get_db),
                    _: models.Usuario = Depends(requiere_admin)):
    services.asignar_materia_a_malla(db, malla_id, datos)

@router.delete("/mallas/{malla_id}/materias/{materia_id}", status_code=204)
def quitar_materia(malla_id: int, materia_id: int, db: Session = Depends(get_db),
                   _: models.Usuario = Depends(requiere_admin)):
    services.quitar_materia_de_malla(db, malla_id, materia_id)
