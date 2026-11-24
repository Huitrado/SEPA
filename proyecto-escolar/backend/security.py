import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import models
from config import MINUTOS_INACTIVIDAD
from database import get_db

SECRET_KEY = os.environ.get("SECRET_KEY", "clave-de-desarrollo-solo-local")
ALGORITMO = "HS256"
HORAS_SESION = 8
bearer = HTTPBearer()

def hashear(contrasena: str) -> str:
    return bcrypt.hashpw(contrasena.encode(), bcrypt.gensalt()).decode()

def verificar(contrasena: str, hash_guardado: str) -> bool:
    return bcrypt.checkpw(contrasena.encode(), hash_guardado.encode())

def ahora_utc() -> datetime:  # las pruebas lo reemplazan para simular el paso del tiempo
    return datetime.now(timezone.utc)

def crear_token(usuario_id: int, jti: str, exp: datetime) -> str:
    # "jti" identifica la sesión: sirve para invalidarla al cerrar sesión (RF-06) o por inactividad (RNF-02)
    return jwt.encode({"sub": str(usuario_id), "exp": exp, "jti": jti}, SECRET_KEY, ALGORITMO)

def abrir_sesion(db: Session, usuario_id: int) -> str:
    """Genera el token y registra la sesión para medir su inactividad (RNF-02)."""
    ahora = ahora_utc()
    jti, exp = uuid.uuid4().hex, ahora + timedelta(hours=HORAS_SESION)
    # limpieza: las sesiones cuyo token ya venció se rechazan solas por "exp"
    db.query(models.SesionActiva).filter(models.SesionActiva.expira < ahora.isoformat()).delete()
    db.add(models.SesionActiva(jti=jti, usuario_id=usuario_id, ultimaActividad=ahora.isoformat(),
                               expira=exp.isoformat()))
    db.commit()
    return crear_token(usuario_id, jti, exp)

def datos_token(cred: HTTPAuthorizationCredentials = Depends(bearer),
                db: Session = Depends(get_db)) -> dict:
    try:
        payload = jwt.decode(cred.credentials, SECRET_KEY, [ALGORITMO])
    except jwt.PyJWTError:
        raise HTTPException(401, "Sesión inválida o expirada")
    jti = payload.get("jti")
    sesion = db.get(models.SesionActiva, jti) if jti else None
    if not sesion or db.get(models.TokenRevocado, jti):
        raise HTTPException(401, "La sesión ya no es válida; inicia sesión de nuevo")
    # RNF-02: cada petición cuenta como actividad; tras MINUTOS_INACTIVIDAD sin ninguna, la sesión se cierra
    ahora = ahora_utc()
    if ahora - datetime.fromisoformat(sesion.ultimaActividad) > timedelta(minutes=MINUTOS_INACTIVIDAD):
        db.delete(sesion)
        db.commit()
        raise HTTPException(401, "Tu sesión se cerró por inactividad; inicia sesión de nuevo")
    sesion.ultimaActividad = ahora.isoformat()
    db.commit()
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

def requiere_estudiante(usuario: models.Usuario = Depends(usuario_actual),
                        db: Session = Depends(get_db)) -> models.Usuario:
    if not db.get(models.Estudiante, usuario.id):
        raise HTTPException(403, "Se requiere rol de estudiante")
    return usuario

def requiere_asesor(usuario: models.Usuario = Depends(requiere_estudiante),
                    db: Session = Depends(get_db)) -> models.Usuario:
    """RF-73, RF-92: un estudiante al que el administrador asignó el rol de asesor."""
    tiene = (db.query(models.Rol).join(models.usuario_rol, models.usuario_rol.c.rol_id == models.Rol.id)
             .filter(models.usuario_rol.c.usuario_id == usuario.id, models.Rol.nombre == "asesor").first())
    if not tiene:
        raise HTTPException(403, "Se requiere rol de asesor")
    return usuario
