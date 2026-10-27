from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Ruta absoluta: no depende de desde dónde ejecutes uvicorn
DB_PATH = Path(__file__).resolve().parent / "sistema_escolar.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def activar_llaves_foraneas(conexion, _):
    conexion.execute("PRAGMA foreign_keys=ON")  # SQLite las ignora si no se activa

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
