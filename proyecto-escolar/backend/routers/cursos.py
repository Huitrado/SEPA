from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
import schemas
import services
from database import get_db
from security import requiere_docente, usuario_actual

router = APIRouter(tags=["Gestión Académica"])

@router.post("/cursos", response_model=schemas.CursoSalida, status_code=201)
def crear_curso(curso: schemas.CursoCrear, db: Session = Depends(get_db),
                docente: models.Usuario = Depends(requiere_docente)):
    return services.crearCurso(db, docente, curso)

@router.get("/cursos", response_model=list[schemas.CursoPublico])
def obtener_cursos(db: Session = Depends(get_db), _: models.Usuario = Depends(usuario_actual)):
    return db.query(models.Curso).filter_by(estado="activo").all()

@router.post("/inscripcion", status_code=201)
def inscribir_alumno(datos: schemas.InscripcionCrear, db: Session = Depends(get_db),
                     usuario: models.Usuario = Depends(usuario_actual)):
    curso = services.inscribirseCurso(db, usuario, datos.codigoCurso)
    return {"mensaje": "Inscripción exitosa", "curso": curso.nombreMateria}

@router.get("/actividades/{actividad_id}/archivo", response_class=FileResponse)
def descargar_archivo_actividad(actividad_id: int, db: Session = Depends(get_db),
                                usuario: models.Usuario = Depends(usuario_actual)):
    """RF-36: el docente del curso y sus alumnos activos descargan el archivo de la actividad."""
    ruta, nombre = services.archivo_de_actividad(db, usuario, actividad_id)
    return FileResponse(ruta, filename=nombre)  # se envía como descarga, nunca se muestra en línea
