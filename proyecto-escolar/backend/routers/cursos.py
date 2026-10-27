from fastapi import APIRouter, Depends
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
