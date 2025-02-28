import traceback
from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from character.models import Character
from character.schemas_admin import SchemaAdminCreateCharacter
from character.schemas_admin import SchemaAdminUpdateCharacter

from core.database import db
from utils import update_nested_dict


async def get_character_service_admin(character_id: str):
    try:
        pipeline = [
            {"$match": {"_id": ObjectId(character_id)}},
            {
                "$lookup": {
                    "from": "state_glic",
                    "let": {"character_id": {"$toString": "$_id"}},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$element_id", "$$character_id"]},
                                        {"$eq": ["$type_element", "character"]},
                                    ]
                                }
                            }
                        },
                        {"$addFields": {"_id": {"$toString": "$_id"}}},
                    ],
                    "as": "data",
                }
            },
        ]

        character_db = await db["character"].aggregate(pipeline).to_list(None)
        if not character_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found",
            )

        character_db = character_db[0]
        character_db["_id"] = str(character_db["_id"])
        for character in character_db["data"]:
            character["data"]["created_at"] = character_db["created_at"]
            character["data"]["updated_at"] = character_db["updated_at"]
            character["data"]["created_by"] = character_db["created_by"]
            character["data"]["updated_by"] = character_db["updated_by"]

        return character_db
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in get character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )


async def get_characters_service_admin(skip: int = 0, limit: int = 10000):
    pipeline = [
        {"$match": {"created_at": {"$gte": datetime(2025, 1, 1)}}},
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "state_glic",
                "let": {"character_id": {"$toString": "$_id"}},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$element_id", "$$character_id"]},
                                    {"$eq": ["$type_element", "character"]},
                                ]
                            }
                        }
                    },
                    {"$addFields": {"_id": {"$toString": "$_id"}}},
                    {"$limit": 1},
                ],
                "as": "data",
            }
        },
        {"$unwind": {"path": "$data", "preserveNullAndEmptyArrays": True}},
    ]

    characters_db = await db["character"].aggregate(pipeline).to_list(None)
    for character in characters_db:
        character["_id"] = str(character["_id"])
        if "data" in character and character["data"]:
            character["data"]["_id"] = str(character["data"]["_id"])
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


async def update_character_service_admin(
    character_id: str, character: SchemaAdminUpdateCharacter, user_id: str
):
    try:
        character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
        if not character_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found",
            )
        character = character.dict()
        state = character["state"]
        del character["state"]
        element_state_db = await db["state_glic"].find_one(
            {"element_id": character_id, "type_element": "character", "state": state}
        )
        character_db["updated_by"] = user_id
        character_db["updated_at"] = datetime.utcnow()
        await db["character"].update_one(
            {"_id": ObjectId(character_id)},
            {"$set": character_db},
        )
        data_updated = update_nested_dict(element_state_db["data"], character)
        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {"$set": {"data": data_updated}},
        )
        return True
    except Exception as e:
        print(f"Error in update character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not updated",
        )
