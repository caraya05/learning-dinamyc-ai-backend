import pytest
from bson.objectid import ObjectId
from io import BytesIO
from fastapi import UploadFile

# Test para crear una ubicación
async def test_create_location(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear juego de prueba primero
    game_collection = test_db.games
    game_data = {
        "name": "Juego para Ubicación",
        "description": "Descripción del juego para ubicación"
    }
    game_result = await game_collection.insert_one(game_data)
    game_id = str(game_result.inserted_id)

    # Datos de la ubicación
    location_data = {
        "name": "Ubicación de Prueba",
        "description": "Descripción de la ubicación de prueba",
        "game_id": game_id,
        "prompt": "Este es un prompt para la ubicación"
    }

    # Crear archivo de prueba para la imagen
    test_file = BytesIO(b"imagen de prueba")
    file = UploadFile(filename="test_image.jpg", file=test_file)

    # Preparar datos multipart
    files = {"file": file}

    response = client.post(
        "/location/",
        headers=headers,
        data=location_data,
        files=files
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == location_data["name"]
    assert data["description"] == location_data["description"]
    assert data["game_id"] == game_id
    assert "image_url" in data

# Test para obtener una ubicación específica
async def test_get_location(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear una ubicación de prueba
    location_collection = test_db.locations
    game_id = str(ObjectId())
    location_data = {
        "name": "Ubicación Existente",
        "description": "Descripción de la ubicación existente",
        "game_id": game_id,
        "image_url": "http://example.com/image.jpg"
    }
    location_result = await location_collection.insert_one(location_data)
    location_id = str(location_result.inserted_id)

    response = client.get(f"/location/{location_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == location_data["name"]
    assert data["description"] == location_data["description"]
    assert data["_id"] == location_id

# Test para listar ubicaciones por juego
async def test_list_locations_by_game(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear juego de prueba
    game_collection = test_db.games
    game_data = {
        "name": "Juego con Ubicaciones",
        "description": "Descripción del juego con ubicaciones"
    }
    game_result = await game_collection.insert_one(game_data)
    game_id = str(game_result.inserted_id)

    # Crear varias ubicaciones para ese juego
    location_collection = test_db.locations
    locations = [
        {
            "name": "Ubicación 1",
            "description": "Descripción 1",
            "game_id": game_id
        },
        {
            "name": "Ubicación 2",
            "description": "Descripción 2",
            "game_id": game_id
        }
    ]

    await location_collection.insert_many(locations)

    response = client.get(f"/location/game/{game_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(loc["name"] == "Ubicación 1" for loc in data)
    assert any(loc["name"] == "Ubicación 2" for loc in data)
    assert all(loc["game_id"] == game_id for loc in data)

# Test para actualizar una ubicación
async def test_update_location(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear una ubicación de prueba
    location_collection = test_db.locations
    location_data = {
        "name": "Ubicación Original",
        "description": "Descripción original",
        "game_id": str(ObjectId())
    }
    location_result = await location_collection.insert_one(location_data)
    location_id = str(location_result.inserted_id)

    # Datos para actualizar
    update_data = {
        "name": "Ubicación Actualizada",
        "description": "Descripción actualizada"
    }

    response = client.put(f"/location/{location_id}", headers=headers, json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]

# Test para eliminar una ubicación
async def test_delete_location(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear una ubicación de prueba
    location_collection = test_db.locations
    location_data = {
        "name": "Ubicación a Eliminar",
        "description": "Descripción de la ubicación a eliminar",
        "game_id": str(ObjectId())
    }
    location_result = await location_collection.insert_one(location_data)
    location_id = str(location_result.inserted_id)

    response = client.delete(f"/location/{location_id}", headers=headers)
    assert response.status_code == 204

    # Verificar que la ubicación ya no existe
    location = await location_collection.find_one({"_id": ObjectId(location_id)})
    assert location is None
