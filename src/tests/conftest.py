import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from pymongo import MongoClient
from main import app
from config import settings
from core.database import db

# Cliente de prueba para FastAPI
@pytest.fixture
def client():
    return TestClient(app)

# Base de datos de prueba
@pytest.fixture(scope="session")
def test_db_name():
    return "test_qwestar_db"

# Cliente de MongoDB para tests
@pytest.fixture(scope="session")
def mongo_client():
    client = MongoClient(settings.DATABASE_URL)
    yield client
    client.close()

# Base de datos de pruebas
@pytest.fixture(scope="function")
async def test_db(mongo_client, test_db_name):
    # Crear base de datos de prueba
    db = mongo_client[test_db_name]

    # Limpiar colecciones antes de cada test
    for collection in await db.list_collection_names():
        await db[collection].delete_many({})

    yield db

    # Limpiar después de cada test
    for collection in await db.list_collection_names():
        await db[collection].delete_many({})

# Sobreescribe la dependencia de base de datos
@pytest.fixture(autouse=True)
async def override_get_db(test_db):
    app.dependency_overrides[db] = lambda: test_db
    yield
    app.dependency_overrides.clear()

# Fixture para token de autenticación
@pytest.fixture
def auth_token():
    # Aquí implementarías la lógica para generar un token válido para pruebas
    return "test_token"

# Fixture para usuario autenticado
@pytest.fixture
async def authenticated_user(test_db):
    # Crear un usuario de prueba
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "hashedpassword123",
        "role": "user"
    }
    user_collection = test_db.users
    result = await user_collection.insert_one(user_data)
    user_data["_id"] = str(result.inserted_id)
    return user_data
