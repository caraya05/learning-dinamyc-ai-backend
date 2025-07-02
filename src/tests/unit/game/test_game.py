import pytest
from bson.objectid import ObjectId
from io import BytesIO
from fastapi import UploadFile

# Test para crear un juego
async def test_create_game(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Datos del juego
    game_data = {
        "name": "Juego de Prueba",
        "description": "Descripción del juego de prueba",
        "category_id": str(ObjectId()),
        "prompt_intro": "Este es un prompt de introducción para el juego"
    }

    # Crear archivo de prueba para la imagen
    test_file = BytesIO(b"imagen de prueba")
    file = UploadFile(filename="test_image.jpg", file=test_file)

    # Preparar datos multipart
    files = {"file": file}

    response = client.post(
        "/game/",
        headers=headers,
        data=game_data,
        files=files
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == game_data["name"]
    assert data["description"] == game_data["description"]
    assert "image_url" in data

# Test para obtener un juego específico
async def test_get_game(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear un juego de prueba
    game_collection = test_db.games
    game_data = {
        "name": "Juego Existente",
        "description": "Descripción del juego existente",
        "user_id": str(ObjectId()),
        "image_url": "http://example.com/image.jpg"
    }
    game_result = await game_collection.insert_one(game_data)
    game_id = str(game_result.inserted_id)

    response = client.get(f"/game/{game_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == game_data["name"]
    assert data["description"] == game_data["description"]
    assert data["_id"] == game_id

# Test para listar juegos
async def test_list_games(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear varios juegos de prueba
    game_collection = test_db.games
    user_id = str(ObjectId())

    games = [
        {
            "name": "Juego 1",
            "description": "Descripción 1",
            "user_id": user_id
        },
        {
            "name": "Juego 2",
            "description": "Descripción 2",
            "user_id": user_id
        }
    ]

    await game_collection.insert_many(games)

    response = client.get("/game/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(game["name"] == "Juego 1" for game in data)
    assert any(game["name"] == "Juego 2" for game in data)

# Test para actualizar un juego
async def test_update_game(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear un juego de prueba
    game_collection = test_db.games
    game_data = {
        "name": "Juego Original",
        "description": "Descripción original",
        "user_id": str(ObjectId())
    }
    game_result = await game_collection.insert_one(game_data)
    game_id = str(game_result.inserted_id)

    # Datos para actualizar
    update_data = {
        "name": "Juego Actualizado",
        "description": "Descripción actualizada"
    }

    response = client.put(f"/game/{game_id}", headers=headers, json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]

# Test para eliminar un juego
async def test_delete_game(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear un juego de prueba
    game_collection = test_db.games
    game_data = {
        "name": "Juego a Eliminar",
        "description": "Descripción del juego a eliminar",
        "user_id": str(ObjectId())
    }
    game_result = await game_collection.insert_one(game_data)
    game_id = str(game_result.inserted_id)

    response = client.delete(f"/game/{game_id}", headers=headers)
    assert response.status_code == 204

    # Verificar que el juego ya no existe
    game = await game_collection.find_one({"_id": ObjectId(game_id)})
    assert game is None

# Test para listar juegos por categoría
async def test_list_games_by_category(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear categoría de prueba
    category_collection = test_db.categories
    category_data = {
        "name": "Categoría de Prueba"
    }
    category_result = await category_collection.insert_one(category_data)
    category_id = str(category_result.inserted_id)

    # Crear juegos en esa categoría
    game_collection = test_db.games
    games = [
        {
            "name": "Juego Categoría 1",
            "description": "Descripción 1",
            "category_id": category_id,
            "user_id": str(ObjectId())
        },
        {
            "name": "Juego Categoría 2",
            "description": "Descripción 2",
            "category_id": category_id,
            "user_id": str(ObjectId())
        }
    ]

    await game_collection.insert_many(games)

    response = client.get(f"/game/category/{category_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(game["category_id"] == category_id for game in data)
