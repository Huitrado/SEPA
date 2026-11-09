from typing import Literal

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

import models
import schemas
import services
from config import TAMANO_MAXIMO_ARCHIVO
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

# ------------------------------------------------------------------ control de asistencia
@router.post("/cursos/{curso_id}/sesiones", response_model=schemas.SesionClaseDetalle, status_code=201)
def generar_sesion(curso_id: int, datos: schemas.SesionClaseCrear | None = None,
                   db: Session = Depends(get_db), docente: models.Usuario = Depends(requiere_docente)):
    return services.generarSesionClase(db, docente, curso_id, datos)

@router.get("/cursos/{curso_id}/sesiones/{sesion_id}", response_model=schemas.SesionClaseDetalle)
def ver_sesion(curso_id: int, sesion_id: int, db: Session = Depends(get_db),
               docente: models.Usuario = Depends(requiere_docente)):
    return services.ver_sesion(db, docente, curso_id, sesion_id)

@router.put("/cursos/{curso_id}/sesiones/{sesion_id}/lista", response_model=schemas.SesionClaseDetalle)
def guardar_lista(curso_id: int, sesion_id: int, datos: schemas.ListaAsistencia,
                  db: Session = Depends(get_db), docente: models.Usuario = Depends(requiere_docente)):
    return services.guardarListaAsistencia(db, docente, curso_id, sesion_id, datos)

@router.get("/cursos/{curso_id}/asistencia", response_model=schemas.CuadriculaAsistencia)
def cuadricula_asistencia(curso_id: int, db: Session = Depends(get_db),
                          docente: models.Usuario = Depends(requiere_docente)):
    return services.cuadricula_asistencia(db, docente, curso_id)

# ------------------------------------------------------------------ categorías de evaluación
@router.get("/cursos/{curso_id}/categorias", response_model=schemas.CategoriasCurso)
def listar_categorias(curso_id: int, db: Session = Depends(get_db),
                      docente: models.Usuario = Depends(requiere_docente)):
    return services.listar_categorias(db, docente, curso_id)

@router.post("/cursos/{curso_id}/categorias", response_model=schemas.CategoriaGuardada, status_code=201)
def crear_categoria(curso_id: int, datos: schemas.CategoriaCrear, db: Session = Depends(get_db),
                    docente: models.Usuario = Depends(requiere_docente)):
    return services.crearCategoria(db, docente, curso_id, datos)

@router.patch("/cursos/{curso_id}/categorias/{categoria_id}", response_model=schemas.CategoriaGuardada)
def editar_categoria(curso_id: int, categoria_id: int, datos: schemas.CategoriaActualizar,
                     db: Session = Depends(get_db), docente: models.Usuario = Depends(requiere_docente)):
    return services.actualizar_categoria(db, docente, curso_id, categoria_id, datos)

@router.delete("/cursos/{curso_id}/categorias/{categoria_id}", response_model=schemas.CategoriasCurso)
def eliminar_categoria(curso_id: int, categoria_id: int, db: Session = Depends(get_db),
                       docente: models.Usuario = Depends(requiere_docente)):
    return services.eliminar_categoria(db, docente, curso_id, categoria_id)

# ------------------------------------------------------------------ actividades
@router.get("/cursos/{curso_id}/actividades", response_model=list[schemas.ActividadSalida])
def listar_actividades(curso_id: int, db: Session = Depends(get_db),
                       docente: models.Usuario = Depends(requiere_docente)):
    return services.listar_actividades(db, docente, curso_id)

@router.post("/cursos/{curso_id}/actividades", response_model=schemas.ActividadSalida, status_code=201)
def crear_actividad(curso_id: int, datos: schemas.ActividadCrear, db: Session = Depends(get_db),
                    docente: models.Usuario = Depends(requiere_docente)):
    return services.crearActividad(db, docente, curso_id, datos)

@router.get("/cursos/{curso_id}/actividades/{actividad_id}", response_model=schemas.ActividadSalida)
def ver_actividad(curso_id: int, actividad_id: int, db: Session = Depends(get_db),
                  docente: models.Usuario = Depends(requiere_docente)):
    return services.ver_actividad(db, docente, curso_id, actividad_id)

@router.patch("/cursos/{curso_id}/actividades/{actividad_id}", response_model=schemas.ActividadSalida)
def editar_actividad(curso_id: int, actividad_id: int, datos: schemas.ActividadActualizar,
                     db: Session = Depends(get_db), docente: models.Usuario = Depends(requiere_docente)):
    return services.actualizar_actividad(db, docente, curso_id, actividad_id, datos)

@router.delete("/cursos/{curso_id}/actividades/{actividad_id}", response_model=list[schemas.ActividadSalida])
def eliminar_actividad(curso_id: int, actividad_id: int, db: Session = Depends(get_db),
                       docente: models.Usuario = Depends(requiere_docente)):
    return services.eliminar_actividad(db, docente, curso_id, actividad_id)

@router.put("/cursos/{curso_id}/actividades/{actividad_id}/archivo", response_model=schemas.ActividadSalida)
def adjuntar_archivo(curso_id: int, actividad_id: int, archivo: UploadFile = File(...),
                     db: Session = Depends(get_db), docente: models.Usuario = Depends(requiere_docente)):
    contenido = archivo.file.read(TAMANO_MAXIMO_ARCHIVO + 1)  # no se lee más de lo permitido (RNF-8)
    return services.adjuntarArchivoActividad(db, docente, curso_id, actividad_id, archivo.filename, contenido)

@router.delete("/cursos/{curso_id}/actividades/{actividad_id}/archivo", response_model=schemas.ActividadSalida)
def quitar_archivo(curso_id: int, actividad_id: int, db: Session = Depends(get_db),
                   docente: models.Usuario = Depends(requiere_docente)):
    return services.quitar_archivo_actividad(db, docente, curso_id, actividad_id)
