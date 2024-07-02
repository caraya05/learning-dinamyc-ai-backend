import json

from bson import ObjectId
from fastapi import HTTPException
from starlette import status
from uuid import uuid4

from gpt_ai.utils import generate_gpt4o
from weapon.models import Weapon

from weapon.schemas import SchemaCreateWeapon, SchemaCreateWeaponCollectionBD
from weapon.schemas import SchemaPartialUpdateWeapon

from utils import upload_image

from core.database import db


async def get_weapons_service(game_id: str, skip: int = 0, limit: int = 100, character_id: str = None):
    """
    Get a list of weapons.
    """
    weapons_db = await db["weapon"].find({"game_id": game_id}).skip(skip).limit(limit).to_list(None)
    counts = await db["weapon"].count_documents({"game_id": game_id})
    return weapons_db, counts


async def create_weapon_service(schema: SchemaCreateWeapon, user_id: str):
    """
    Create a new weapon.
    """
    weapon_schema = Weapon(**schema.dict())
    if weapon_schema.image:
        weapon_schema.image = upload_image(
            url_image=weapon_schema.image,
            file_name=f"weapon/{uuid4()}.jpg",
            size=(512, 512),
        )
    weapon_schema.created_by = user_id
    weapon_schema.updated_by = user_id
    weapon_created = await db["weapon"].insert_one(weapon_schema.dict())
    return await db["weapon"].find_one({"_id": weapon_created.inserted_id})


async def retrieve_weapon_service(weapon_id: str):
    """
    Retrieve a weapon.
    """
    weapon_db = await db["weapon"].find_one({"_id": ObjectId(weapon_id)})
    return weapon_db


async def partial_update_weapon_service(weapon_id: str, weapon: SchemaPartialUpdateWeapon):
    """
    Partial update a weapon.
    """
    db_weapon = await db["weapon"].find_one({"_id": ObjectId(weapon_id)})
    for var, value in weapon:
        setattr(db_weapon, var, value)
    await db["weapon"].update_one({"_id": ObjectId(weapon_id)}, {"$set": db_weapon})
    return await db["weapon"].find_one({"_id": ObjectId(weapon_id)})


async def delete_weapon_service(weapon_id: str):
    """
    Delete a weapon.
    """
    weapon_deleted = await db["weapon"].delete_one({"_id": ObjectId(weapon_id)})
    if weapon_deleted.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weapon not found",
        )


async def create_weapon_collection_service(*,
                                           user_id: str,
                                           name: str,
                                           prompt_user: str,
                                           weapon_type: str):
    """
    Create a weapon collection.
    """
    json_response = {
        "description": "string (detailed description to generate an image of the weapon)",
    }

    response_collection = generate_gpt4o(
        content_prompt=[
            {
                "role": "system",
                "content": "Crear una descripciona detalle para generar una imagen de un arma, usando el prompt del usuario, "
                           f"prompt_user: {prompt_user}, tipo de arma: {weapon_type},"
                           f"responde con un JSON que contenga el esquema {json_response}",
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt_user}]
            },
        ],
        type_text="collection",
        model="gpt-4o",
        max_tokens=4096
    )

    response = json.loads(response_collection)

    weapon_collection = SchemaCreateWeaponCollectionBD(
        name=name,
        prompt_user=prompt_user,
        type=weapon_type,
        description=response['description'],
        created_by=user_id,
        updated_by=user_id
    )

    weapon_collection_db = await db["weapon"].insert_one(weapon_collection.dict())
    return await db["weapon"].find_one({"_id": weapon_collection_db.inserted_id})


async def get_weapon_by_collection_service(weapon_id: str):
    """
    Get a weapon collection.
    """
    weapon_collection_db = await db["weapon"].find_one({"_id": ObjectId(weapon_id)})
    return weapon_collection_db


async def get_weapons_by_collection_service(collection_id: str):
    """
    Get a list of weapons by collection.
    """
    collection_db = await db["collection_character"].find_one({"_id": ObjectId(collection_id)})

    weapons_db = await db["weapon"].find(
        {"_id": {"$in": [ObjectId(weapon_id) for weapon_id in collection_db['weapons']]}}).to_list(None)

    return weapons_db


async def update_weapon_collection_service(weapon_id: str, name: str, prompt_user: str, weapon_type: str):
    """
    Update a weapon collection.
    """
    collection_db = await db["weapon"].find_one({"_id": ObjectId(weapon_id)})
    if name:
        collection_db['name'] = name
    if prompt_user:
        collection_db['prompt_user'] = prompt_user
        json_response = {
            "description": "string (detailed description to generate an image of the weapon)",
        }

        response_collection = generate_gpt4o(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Crear una descripciona detalle para generar una imagen de un arma, usando el prompt del usuario, "
                               f"prompt_user: {prompt_user}, tipo de arma: {weapon_type},"
                               f"responde con un JSON que contenga el esquema {json_response}",
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt_user}]
                },
            ],
            type_text="collection",
            model="gpt-4o",
            max_tokens=4096
        )

        response = json.loads(response_collection)
        collection_db['description'] = response['description']
    if weapon_type:
        collection_db['type'] = weapon_type

    await db["weapon"].update_one({"_id": ObjectId(weapon_id)}, {"$set": collection_db})
    return await db["weapon"].find_one({"_id": ObjectId(weapon_id)})
