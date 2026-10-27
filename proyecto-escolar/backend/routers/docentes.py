from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
import services
from database import get_db
from security import requiere_docente

# RF-95: todas estas rutas son solo para el docente creador del curso
router = APIRouter(prefix="/docente", tags=["Docente"])

@router.get("/cursos", response_model=list[schemas.CursoSalida])
def mis_cursos(estado: Literal["activo", "archivado"] = "activo", db: Session = Depends(get_db),
               docente: models.Usuario = Depends(requiere_docente)):
    return services.cursos_del_docente(db, docente, estado)

@router.get("/cursos/{curso_id}/alumnos", response_model=list[schemas.AlumnoCurso])
def alumnos_del_curso(curso_id: int, db: Session = Depends(get_db),
                      docente: models.Usuario = Depends(requiere_docente)):
    return services.alumnos_de_curso(db, docente, curso_id)

@router.patch("/cursos/{curso_id}", response_model=schemas.CursoSalida)
def editar_curso(curso_id: int, datos: schemas.CursoActualizar, db: Session = Depends(get_db),
                 docente: models.Usuario = Depends(requiere_docente)):
    return services.actualizar_curso(db, docente, curso_id, datos)

@router.patch("/cursos/{curso_id}/estado", response_model=schemas.CursoSalida)
def cambiar_estado(curso_id: int, datos: schemas.EstadoCurso, db: Session = Depends(get_db),
                   docente: models.Usuario = Depends(requiere_docente)):
    return services.cambiar_estado_curso(db, docente, curso_id, datos.estado)
