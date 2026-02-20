import pytest
from bson.objectid import ObjectId
from io import BytesIO
from fastapi import UploadFile

# Test para crear un objeto
async def test_create_object(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear juego de prueba primero
    game_collection = test_db.games
    game_data = {
        "name": "Juego para Objeto",
        "description": "Descripción del juego para objeto"
    }
    game_result = await game_collection.insert_one(game_data)
    game_id = str(game_result.inserted_id)

    # Crear ubicación de prueba
    location_collection = test_db.locations
    location_data = {
        "name": "Ubicación para Objeto",
        "description": "Descripción de la ubicación para objeto",
        "game_id": game_id
    }
    location_result = await location_collection.insert_one(location_data)
    location_id = str(location_result.inserted_id)

    # Datos del objeto
    object_data = {
        "name": "Objeto de Prueba",
        "description": "Descripción del objeto de prueba",
        "game_id": game_id,
        "location_id": location_id,
        "is_collectable": True,
        "state_game": "active"
    }

    # Crear archivo de prueba para la imagen
    test_file = BytesIO(b"imagen de prueba")
    file = UploadFile(filename="test_image.jpg", file=test_file)

    # Preparar datos multipart
    files = {"file": file}

    response = client.post(
        "/object/",
        headers=headers,
        data=object_data,
        files=files
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == object_data["name"]
    assert data["description"] == object_data["description"]
    assert data["game_id"] == game_id
    assert data["location_id"] == location_id
    assert data["is_collectable"] == object_data["is_collectable"]
    assert "image_url" in data

# Test para obtener un objeto específico
async def test_get_object(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear un objeto de prueba
    object_collection = test_db.objects
    game_id = str(ObjectId())
    location_id = str(ObjectId())
    object_data = {
        "name": "Objeto Existente",
        "description": "Descripción del objeto existente",
        "game_id": game_id,
        "location_id": location_id,
        "is_collectable": True,
        "image_url": "http://example.com/image.jpg"
    }
    object_result = await object_collection.insert_one(object_data)
    object_id = str(object_result.inserted_id)

    response = client.get(f"/object/{object_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == object_data["name"]
    assert data["description"] == object_data["description"]
    assert data["_id"] == object_id

# Test para listar objetos por ubicación
async def test_list_objects_by_location(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear juego y ubicación de prueba
    game_id = str(ObjectId())
    location_id = str(ObjectId())

    # Crear varios objetos para esa ubicación
    object_collection = test_db.objects
    objects = [
        {
            "name": "Objeto 1",
            "description": "Descripción 1",
            "game_id": game_id,
            "location_id": location_id,
            "is_collectable": True
        },
        {
            "name": "Objeto 2",
            "description": "Descripción 2",
            "game_id": game_id,
            "location_id": location_id,
            "is_collectable": False
        }
    ]

    await object_collection.insert_many(objects)

    response = client.get(f"/object/location/{location_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(obj["name"] == "Objeto 1" for obj in data)
    assert any(obj["name"] == "Objeto 2" for obj in data)
    assert all(obj["location_id"] == location_id for obj in data)

# Test para listar objetos por juego
async def test_list_objects_by_game(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear juego de prueba
    game_id = str(ObjectId())

    # Crear varios objetos para ese juego en diferentes ubicaciones
    object_collection = test_db.objects
    objects = [
        {
            "name": "Objeto Juego 1",
            "description": "Descripción 1",
            "game_id": game_id,
            "location_id": str(ObjectId()),
            "is_collectable": True
        },
        {
            "name": "Objeto Juego 2",
            "description": "Descripción 2",
            "game_id": game_id,
            "location_id": str(ObjectId()),
            "is_collectable": False
        }
    ]

    await object_collection.insert_many(objects)

    response = client.get(f"/object/game/{game_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(obj["name"] == "Objeto Juego 1" for obj in data)
    assert any(obj["name"] == "Objeto Juego 2" for obj in data)
    assert all(obj["game_id"] == game_id for obj in data)

# Test para actualizar un objeto
async def test_update_object(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear un objeto de prueba
    object_collection = test_db.objects
    object_data = {
        "name": "Objeto Original",
        "description": "Descripción original",
        "game_id": str(ObjectId()),
        "location_id": str(ObjectId()),
        "is_collectable": True
    }
    object_result = await object_collection.insert_one(object_data)
    object_id = str(object_result.inserted_id)

    # Datos para actualizar
    update_data = {
        "name": "Objeto Actualizado",
        "description": "Descripción actualizada",
        "is_collectable": False
    }

    response = client.put(f"/object/{object_id}", headers=headers, json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["is_collectable"] == update_data["is_collectable"]

# Test para eliminar un objeto
async def test_delete_object(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear un objeto de prueba
    object_collection = test_db.objects
    object_data = {
        "name": "Objeto a Eliminar",
        "description": "Descripción del objeto a eliminar",
        "game_id": str(ObjectId()),
        "location_id": str(ObjectId()),
        "is_collectable": True
    }
    object_result = await object_collection.insert_one(object_data)
    object_id = str(object_result.inserted_id)

    response = client.delete(f"/object/{object_id}", headers=headers)
    assert response.status_code == 204

    # Verificar que el objeto ya no existe
    object_item = await object_collection.find_one({"_id": ObjectId(object_id)})
    assert object_item is None

# Test para coleccionar un objeto
async def test_collect_object(client, auth_token, test_db):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Crear un objeto coleccionable
    object_collection = test_db.objects
    game_id = str(ObjectId())
    location_id = str(ObjectId())
    user_id = str(ObjectId())

    object_data = {
        "name": "Objeto Coleccionable",
        "description": "Este objeto puede ser coleccionado",
        "game_id": game_id,
        "location_id": location_id,
        "is_collectable": True
    }
    object_result = await object_collection.insert_one(object_data)
    object_id = str(object_result.inserted_id)

    # Datos para coleccionar
    collect_data = {
        "user_id": user_id,
        "object_id": object_id
    }

    response = client.post("/object/collect", headers=headers, json=collect_data)
    assert response.status_code == 200

    # Verificar que el objeto fue agregado a la colección del usuario
    collection_collection = test_db.user_collections
    collection = await collection_collection.find_one({
        "user_id": user_id,
        "object_id": object_id
    })
    assert collection is not None
