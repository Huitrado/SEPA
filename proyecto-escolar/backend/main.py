from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

import models
import services
from database import SessionLocal, engine
from errores import errores_de_validacion
from routers import admin, catalogos, cursos, docentes, usuarios

models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(_):
    with SessionLocal() as db:
        services.sembrar_catalogos(db)  # carreras iniciales si el catálogo está vacío
    yield

app = FastAPI(title="API SEPA", lifespan=lifespan)
app.add_exception_handler(RequestValidationError, errores_de_validacion)

# Ajusta los orígenes al puerto donde sirvas el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def sin_cache(request, call_next):
    # RF-06: el navegador no debe guardar respuestas de la API para mostrarlas con "atrás"
    respuesta = await call_next(request)
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta

app.include_router(usuarios.router)
app.include_router(catalogos.router)
app.include_router(cursos.router)
app.include_router(docentes.router)
app.include_router(admin.router)
