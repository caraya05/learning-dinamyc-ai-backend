from bson import ObjectId
from fastapi import HTTPException
from starlette import status
from uuid import uuid4
from weapon.models import Weapon

from weapon.schemas import SchemaCreateWeapon
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
