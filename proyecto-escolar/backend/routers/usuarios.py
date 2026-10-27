from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
import services
from config import MENSAJE_RECUPERACION, rol_por_correo
from database import get_db
from security import datos_token, usuario_actual

router = APIRouter(prefix="/usuarios", tags=["Registro y sesión"])

@router.post("/registro", response_model=schemas.RegistroSalida, status_code=201)
def registrar_usuario(usuario: schemas.UsuarioCrear, db: Session = Depends(get_db)):
    nuevo = services.registrarse(db, usuario)
    mensaje = ("Cuenta creada correctamente" if nuevo.estado == "activo"
               else "Cuenta creada; un administrador debe aprobarla antes de que puedas entrar")
    return {**schemas.UsuarioSalida.model_validate(nuevo).model_dump(),
            "estado": nuevo.estado, "rol": rol_por_correo(nuevo.correoInstitucional),
            "mensaje": mensaje}

@router.post("/login", response_model=schemas.SesionSalida)
def iniciar_sesion(credenciales: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    return services.iniciarSesion(db, credenciales)

@router.post("/logout")
def cerrar_sesion(payload: dict = Depends(datos_token), db: Session = Depends(get_db)):
    services.cerrarSesion(db, payload)
    return {"mensaje": "Sesión cerrada correctamente"}

@router.get("/yo", response_model=schemas.PerfilSalida)
def mi_perfil(usuario: models.Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return services.perfil_de(db, usuario)

@router.get("/recuperar-contrasena")
def recuperar_contrasena():
    return {"mensaje": MENSAJE_RECUPERACION}
