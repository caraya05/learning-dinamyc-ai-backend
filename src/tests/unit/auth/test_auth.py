import pytest
from fastapi.testclient import TestClient
import json
from bson.objectid import ObjectId

# Test de registro de usuario
async def test_user_registration(client):
    user_data = {
        "name": "Nuevo Usuario",
        "email": "nuevo@example.com",
        "password": "contraseña123"
    }

    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == user_data["name"]
    assert data["email"] == user_data["email"]
    # No debería devolver la contraseña
    assert "password" not in data

# Test de inicio de sesión
async def test_user_login(client, test_db):
    # Crear un usuario primero
    user_collection = test_db.users
    hashed_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "contraseña123" hasheada

    user_data = {
        "name": "Usuario Existente",
        "email": "existente@example.com",
        "password": hashed_password
    }
    await user_collection.insert_one(user_data)

    # Intento de inicio de sesión
    login_data = {
        "email": "existente@example.com",
        "password": "contraseña123"
    }

    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"

# Test de inicio de sesión fallido
async def test_failed_login(client):
    login_data = {
        "email": "noexiste@example.com",
        "password": "contraseña123"
    }

    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 401

# Test de perfil de usuario
async def test_get_user_profile(client, auth_token, authenticated_user):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == authenticated_user["email"]
    assert data["name"] == authenticated_user["name"]

# Test de actualización de perfil
async def test_update_profile(client, auth_token, authenticated_user):
    headers = {"Authorization": f"Bearer {auth_token}"}
    update_data = {
        "name": "Nombre Actualizado"
    }

    response = client.put("/auth/me", headers=headers, json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["email"] == authenticated_user["email"]  # Email no cambió
