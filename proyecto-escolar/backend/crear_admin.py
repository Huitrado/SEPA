"""Crea el primer administrador (la API no puede, porque para crear uno hace falta ser uno).
Uso, desde la carpeta backend:  python crear_admin.py
"""
import getpass

from fastapi import HTTPException
from pydantic import ValidationError

import models
import schemas
import services
from database import SessionLocal, engine

def main():
    models.Base.metadata.create_all(bind=engine)
    try:
        datos = schemas.AdminCrear(
            nombre=input("Nombre: ").strip(),
            apellidos=input("Apellidos: ").strip(),
            correoInstitucional=input("Correo institucional: ").strip(),
            noEmpleado=input("Número de empleado (será tu código de acceso): ").strip(),
            contrasena=getpass.getpass("Contraseña (8+ caracteres, con mayúscula, minúscula y número): "),
        )
    except ValidationError as e:
        print("\nDatos inválidos:")
        for err in e.errors():
            print(f"  - {err['loc'][0]}: {err['msg']}")
        return
    with SessionLocal() as db:
        try:
            services.sembrar_catalogos(db)
            usuario = services.crear_administrador(db, datos)
        except HTTPException as e:
            print(f"\nNo se pudo crear: {e.detail}")
            return
    print(f"\nAdministrador creado (id {usuario.id}). Inicia sesión con el código {datos.noEmpleado}.")

if __name__ == "__main__":
    main()
