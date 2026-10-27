from datetime import date

import pytest
from fastapi.testclient import TestClient

import models
import services
from database import get_db
from helpers import db_de_prueba, engine, sembrar_base
from main import app

@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(services, "hoy", lambda: date(2026, 10, 25))  # fecha fija: dentro de 2026-B
    models.Base.metadata.drop_all(engine)
    models.Base.metadata.create_all(engine)
    sembrar_base()
    app.dependency_overrides[get_db] = db_de_prueba
    yield TestClient(app)
    app.dependency_overrides.clear()
