from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core import db
from task.services import create_task_service, update_task_service

# from celery_worker import generate_voice_character_task


async def add_voice_service(voices: list):
    await db["voice"].delete_many({})
    for voice in voices:
        try:
            await db["voice"].insert_one(
                {
                    "voice_id": voice["voice_id"],
                    "name": voice["name"],
                    "age": voice["labels"]["age"],
                    "gender": voice["labels"]["gender"],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
        except Exception as e:
            print(f"Error in add voice service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Error in add voice service",
            )
    return True


async def generate_voice_service(character_id: str, user_id: str):
    try:
        character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
        # TODO: Implementar la generación de voz
        # task_db = await create_task_service(
        #     _task_id="",
        #     _user_id=user_id,
        #     _task_data={},
        #     _element_id=str(character_id),
        #     _element_type="character",
        #     _process="update_character",
        # )
        # task_celery = generate_voice_character_task.delay(
        #     _character_id=str(character_id), _user_id=user_id, _task_id=str(task_db["_id"])
        # )
        # await update_task_service(
        #     _id=str(task_db["_id"]),
        #     _task_id=task_celery.id,
        # )
        # character_db["task_id"] = task_celery.id
        return character_db
    except Exception as e:
        print(f"Error in generate voice service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error in generate voice service",
        )
