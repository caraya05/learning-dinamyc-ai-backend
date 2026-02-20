import pytest
import json
from bson.objectid import ObjectId
from fastapi import UploadFile
from io import BytesIO

# Test para crear un personaje
async def test_create_character(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear juego de prueba primero
    game_collection = test_db.games
    game_data = {
        "name": "Juego de Prueba",
        "description": "Descripción del juego"
    }
    game_result = await game_collection.insert_one(game_data)
    game_id = str(game_result.inserted_id)

    # Crear ubicación de prueba
    location_collection = test_db.locations
    location_data = {
        "name": "Ubicación de Prueba",
        "game_id": game_id
    }
    location_result = await location_collection.insert_one(location_data)
    location_id = str(location_result.inserted_id)

    # Datos para crear un personaje
    options_dialog = {
        "type": "multiple_choice",
        "options": [
            {"text": "Opción 1", "next_id": "1"},
            {"text": "Opción 2", "next_id": "2"}
        ]
    }

    character_data = {
        "name": "Personaje de Prueba",
        "prompt_user": "Este es un prompt de prueba",
        "prompt_user_dialog": "Diálogo de prueba",
        "conversation_type": "multiple_choice",
        "options_dialog": json.dumps(options_dialog),
        "game_id": game_id,
        "location_id": location_id,
        "state_game": "active"
    }

    # Crear un archivo de prueba para la imagen
    test_file = BytesIO(b"imagen de prueba")
    file = UploadFile(filename="test_image.jpg", file=test_file)

    # Preparar datos multipart
    files = {"file": file}

    response = client.post(
        "/character/",
        headers=headers,
        data=character_data,
        files=files
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == character_data["name"]
    assert data["game_id"] == game_id
    assert data["location_id"] == location_id

# Test para obtener un personaje específico
async def test_get_character(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear un personaje de prueba
    character_collection = test_db.characters
    character_data = {
        "name": "Personaje Existente",
        "prompt_user": "Prompt de prueba",
        "game_id": str(ObjectId()),
        "user_id": str(ObjectId())
    }
    character_result = await character_collection.insert_one(character_data)
    character_id = str(character_result.inserted_id)

    response = client.get(f"/character/{character_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == character_data["name"]
    assert data["_id"] == character_id

# Test para listar personajes
async def test_list_characters(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear varios personajes de prueba
    character_collection = test_db.characters
    game_id = str(ObjectId())
    user_id = str(ObjectId())

    characters = [
        {
            "name": "Personaje 1",
            "game_id": game_id,
            "user_id": user_id
        },
        {
            "name": "Personaje 2",
            "game_id": game_id,
            "user_id": user_id
        }
    ]

    await character_collection.insert_many(characters)

    response = client.get("/character/game/" + game_id, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(char["name"] == "Personaje 1" for char in data)
    assert any(char["name"] == "Personaje 2" for char in data)

# Test para actualizar un personaje
async def test_update_character(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear un personaje de prueba
    character_collection = test_db.characters
    character_data = {
        "name": "Personaje Original",
        "prompt_user": "Prompt original",
        "game_id": str(ObjectId()),
        "user_id": str(ObjectId())
    }
    character_result = await character_collection.insert_one(character_data)
    character_id = str(character_result.inserted_id)

    # Datos para actualizar
    update_data = {
        "name": "Personaje Actualizado",
        "prompt_user": "Prompt actualizado"
    }

    response = client.put(f"/character/{character_id}", headers=headers, json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["prompt_user"] == update_data["prompt_user"]

# Test para eliminar un personaje
async def test_delete_character(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear un personaje de prueba
    character_collection = test_db.characters
    character_data = {
        "name": "Personaje a Eliminar",
        "game_id": str(ObjectId()),
        "user_id": str(ObjectId())
    }
    character_result = await character_collection.insert_one(character_data)
    character_id = str(character_result.inserted_id)

    response = client.delete(f"/character/{character_id}", headers=headers)
    assert response.status_code == 204

    # Verificar que el personaje ya no existe
    character = await character_collection.find_one({"_id": ObjectId(character_id)})
    assert character is None
