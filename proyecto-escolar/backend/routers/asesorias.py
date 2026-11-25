from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
import services
from database import get_db
from security import requiere_asesor, requiere_estudiante

# RF-78 a RF-80: el tablero lo ven los estudiantes · RF-74 a RF-77: lo administran los asesores
router = APIRouter(prefix="/asesorias", tags=["Asesorías"])

@router.get("", response_model=list[schemas.PublicacionSalida])
def tablero(materia: str | None = None, modalidad: Literal["presencial", "virtual"] | None = None,
            q: str | None = None, db: Session = Depends(get_db),
            alumno: models.Usuario = Depends(requiere_estudiante)):
    return services.tablero_asesorias(db, alumno, materia, modalidad, q)

@router.get("/mias", response_model=list[schemas.PublicacionSalida])
def mis_publicaciones(db: Session = Depends(get_db), asesor: models.Usuario = Depends(requiere_asesor)):
    return services.mis_asesorias(db, asesor)

# Solicitud para ser asesor (antes de "/{publicacion_id}" para que "solicitud" no se lea como id)
@router.get("/solicitud", response_model=schemas.SolicitudAsesorSalida | None)
def mi_solicitud(db: Session = Depends(get_db), alumno: models.Usuario = Depends(requiere_estudiante)):
    return services.mi_solicitud_asesor(db, alumno)

@router.post("/solicitud", response_model=schemas.SolicitudAsesorSalida, status_code=201)
def solicitar(datos: schemas.SolicitudAsesorCrear, db: Session = Depends(get_db),
              alumno: models.Usuario = Depends(requiere_estudiante)):
    return services.enviar_solicitud_asesor(db, alumno, datos)

@router.get("/{publicacion_id}", response_model=schemas.PublicacionSalida)
def detalle(publicacion_id: int, db: Session = Depends(get_db),
            alumno: models.Usuario = Depends(requiere_estudiante)):
    return services.ver_asesoria(db, alumno, publicacion_id)

@router.post("", response_model=schemas.PublicacionSalida, status_code=201)
def publicar(datos: schemas.PublicacionCrear, db: Session = Depends(get_db),
             asesor: models.Usuario = Depends(requiere_asesor)):
    return services.crearPublicacion(db, asesor, datos)

@router.patch("/{publicacion_id}", response_model=schemas.PublicacionSalida)
def modificar(publicacion_id: int, datos: schemas.PublicacionActualizar, db: Session = Depends(get_db),
              asesor: models.Usuario = Depends(requiere_asesor)):
    return services.modificarPublicacion(db, asesor, publicacion_id, datos)

@router.delete("/{publicacion_id}")
def eliminar(publicacion_id: int, db: Session = Depends(get_db), asesor: models.Usuario = Depends(requiere_asesor)):
    services.desactivarPublicacion(db, asesor, publicacion_id)
    return {"mensaje": "Publicación eliminada"}
