from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from celery_worker import generate_character_task
from celery_worker import generate_image_character_task

from character.models import Character
from character.schemas_admin import SchemaAdminCreateCharacter
from character.schemas_admin import SchemaAdminUpdateCharacter
from character.schemas_admin import SchemaAdminRetrieveCharacter

from core.database import db

from task.services import create_task_service
from task.services import update_task_service


async def get_character_service_admin(character_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )
    character_db["_id"] = str(character_db["_id"])
    return character_db


async def get_characters_service_admin(skip: int = 0, limit: int = 100):
    characters_db = await db["character"].find().skip((skip - 1) * limit).limit(limit).to_list(None)
    for i in range(len(characters_db)):
        characters_db[i]["_id"] = str(characters_db[i]["_id"])
    return characters_db


async def create_character_service_admin(character: SchemaAdminCreateCharacter, user_id: str):
    try:
        character_db = Character(**character.dict())
        character_db.created_by = user_id
        character_db.updated_by = user_id
        character_created = await db["character"].insert_one(character_db.dict())
        #
        # task_db = await create_task_service(
        #     _task_id="",
        #     _user_id=user_id,
        #     _task_data={},
        #     _element_id=str(character_created.inserted_id),
        #     _element_type="character",
        #     _process="create_character",
        # )
        #
        # task_celery = generate_character_task.delay(
        #     _character_id=str(character_created.inserted_id),
        #     _user_id=user_id,
        #     _task_id=str(task_db["_id"]),
        # )
        # await update_task_service(
        #     _id=str(task_db["_id"]),
        #     _task_id=task_celery.id,
        # )
        #
        # await db["character"].update_one(
        #     {"_id": character_created.inserted_id},
        #     {"$set": {"tasks_request": [str(task_db["_id"])]}},
        # )

        if character_db := await db["character"].find_one({"_id": character_created.inserted_id}):
            return character_db
    except Exception as e:
        print(f"Error in create character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not created",
        )


async def update_character_service_admin(character_id: str, character: SchemaAdminUpdateCharacter, user_id: str):
    try:
        character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
        if not character_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found",
            )

        character_db = Character(**character.dict())
        character_db.updated_at = datetime.utcnow()
        character_db.updated_by = user_id
        await db["character"].update_one(
            {"_id": ObjectId(character_id)},
            {"$set": character_db.dict()},
        )
        return character_db
    except Exception as e:
        print(f"Error in update character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not updated",
        )