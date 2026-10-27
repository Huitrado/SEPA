from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
import services
from config import DIAS_SEMANA, TIPOS_EVALUACION
from database import get_db

# Públicos: el formulario de registro los necesita antes de iniciar sesión
router = APIRouter(prefix="/catalogos", tags=["Catálogos"])

@router.get("/carreras", response_model=list[schemas.CarreraSalida])
def carreras(db: Session = Depends(get_db)):
    return db.query(models.Carrera).order_by(models.Carrera.nombre).all()

@router.get("/ciclos", response_model=list[schemas.CicloSalida])
def ciclos(estado: Literal["activo", "proximo", "cerrado"] | None = None, db: Session = Depends(get_db)):
    return services.listar_ciclos(db, estado)

@router.get("/ciclo-actual", response_model=schemas.CicloSalida)
def ciclo_actual(db: Session = Depends(get_db)):
    """El ciclo que se muestra (y se exige) en el registro de estudiantes."""
    vigente = services.ciclo_vigente(db)
    if not vigente:
        raise HTTPException(404, "No hay un ciclo escolar en curso registrado")
    return services._ciclo_dict(vigente)

@router.get("/tipos-evaluacion")
def tipos_evaluacion():
    return [{"valor": v, "etiqueta": e} for v, e in TIPOS_EVALUACION.items()]

@router.get("/dias-semana")
def dias_semana():
    return list(DIAS_SEMANA)
