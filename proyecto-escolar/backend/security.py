import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import models
from database import get_db

SECRET_KEY = os.environ.get("SECRET_KEY", "clave-de-desarrollo-solo-local")
ALGORITMO = "HS256"
HORAS_SESION = 8
bearer = HTTPBearer()

def hashear(contrasena: str) -> str:
    return bcrypt.hashpw(contrasena.encode(), bcrypt.gensalt()).decode()

def verificar(contrasena: str, hash_guardado: str) -> bool:
    return bcrypt.checkpw(contrasena.encode(), hash_guardado.encode())

def crear_token(usuario_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=HORAS_SESION)
    # "jti" identifica la sesión: sirve para invalidarla al cerrar sesión (RF-06)
    return jwt.encode({"sub": str(usuario_id), "exp": exp, "jti": uuid.uuid4().hex}, SECRET_KEY, ALGORITMO)

def datos_token(cred: HTTPAuthorizationCredentials = Depends(bearer),
                db: Session = Depends(get_db)) -> dict:
    try:
        payload = jwt.decode(cred.credentials, SECRET_KEY, [ALGORITMO])
    except jwt.PyJWTError:
        raise HTTPException(401, "Sesión inválida o expirada")
    jti = payload.get("jti")
    if not jti or db.get(models.TokenRevocado, jti):
        raise HTTPException(401, "La sesión ya no es válida; inicia sesión de nuevo")
    return payload

def usuario_actual(payload: dict = Depends(datos_token),
                   db: Session = Depends(get_db)) -> models.Usuario:
    try:
        uid = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(401, "Sesión inválida")
    usuario = db.get(models.Usuario, uid)
    if not usuario or usuario.estado != "activo":
        raise HTTPException(401, "Usuario no válido")
    return usuario

def requiere_admin(usuario: models.Usuario = Depends(usuario_actual),
                   db: Session = Depends(get_db)) -> models.Usuario:
    if not db.get(models.Administrador, usuario.id):
        raise HTTPException(403, "Se requiere rol de administrador")
    return usuario

def requiere_docente(usuario: models.Usuario = Depends(usuario_actual),
                     db: Session = Depends(get_db)) -> models.Usuario:
    if not db.get(models.Docente, usuario.id):
        raise HTTPException(403, "Se requiere rol de docente")
    return usuario
