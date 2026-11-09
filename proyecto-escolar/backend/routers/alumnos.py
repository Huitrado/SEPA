from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

import models
import schemas
import services
from config import TAMANO_MAXIMO_ARCHIVO
from database import get_db
from security import requiere_estudiante

# Lo que hace el alumno dentro de los cursos en los que está inscrito
router = APIRouter(prefix="/alumno", tags=["Alumno"])

@router.get("/cursos", response_model=list[schemas.CursoPublico])
def mis_cursos(db: Session = Depends(get_db), alumno: models.Usuario = Depends(requiere_estudiante)):
    return services.cursos_del_alumno(db, alumno)

@router.get("/cursos/{curso_id}/actividades", response_model=list[schemas.ActividadAlumno])
def actividades_del_curso(curso_id: int, db: Session = Depends(get_db),
                          alumno: models.Usuario = Depends(requiere_estudiante)):
    return services.actividades_del_alumno(db, alumno, curso_id)

@router.post("/actividades/{actividad_id}/entrega", response_model=schemas.ActividadAlumno, status_code=201)
def entregar(actividad_id: int, archivo: UploadFile = File(...), db: Session = Depends(get_db),
             alumno: models.Usuario = Depends(requiere_estudiante)):
    contenido = archivo.file.read(TAMANO_MAXIMO_ARCHIVO + 1)  # no se lee más de lo permitido (RNF-8)
    return services.entregarActividad(db, alumno, actividad_id, archivo.filename, contenido)

@router.delete("/actividades/{actividad_id}/entrega", response_model=schemas.ActividadAlumno)
def cancelar_entrega(actividad_id: int, db: Session = Depends(get_db),
                     alumno: models.Usuario = Depends(requiere_estudiante)):
    return services.cancelarEntrega(db, alumno, actividad_id)

@router.get("/cursos/{curso_id}/calificaciones", response_model=schemas.CalificacionesAlumno)
def mis_calificaciones(curso_id: int, db: Session = Depends(get_db),
                       alumno: models.Usuario = Depends(requiere_estudiante)):
    return services.calificaciones_del_alumno(db, alumno, curso_id)

@router.get("/cursos/{curso_id}/seguimiento", response_model=schemas.SeguimientoPropio)
def mi_seguimiento(curso_id: int, db: Session = Depends(get_db),
                   alumno: models.Usuario = Depends(requiere_estudiante)):
    return services.seguimiento_del_alumno(db, alumno, curso_id)
