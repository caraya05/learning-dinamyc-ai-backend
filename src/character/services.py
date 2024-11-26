from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from celery_worker import generate_character_task, update_character_task
from celery_worker import generate_image_character_task

from character.models import Character
from character.schemas import SchemaCreateCharacter
from character.schemas import CharacterLocationModel

from core.database import db

from task.services import create_task_service
from task.services import update_task_service


async def get_character_service(character_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    return character_db


async def get_characters_service(skip: int = 1, limit: int = 100, game_id: str = None):
    try:
        game_db = await db["game"].find_one({"_id": ObjectId(game_id)})
        if not game_db.get("characters_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Characters not found",
            )
        characters_db = await db["character"].find({"_id":{"$in": [ObjectId(i) for i in game_db["characters_id"]]}}).skip((skip - 1) * limit).limit(limit).to_list(None)
        return characters_db
    except Exception as e:
        print(f"Error in get characters service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characters not found",
        )


async def get_all_character_service(user_id: str, skip: int = 1, limit: int = 10):
    try:
        characters_db = await (
            db["character"]
            .find({"created_by": user_id})
            .sort("created_at", -1)
            .skip((skip - 1) * limit)
            .limit(limit)
            .to_list(None)
        )
        return characters_db
    except Exception as e:
        print(f"Error in get all character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characters not found",
        )





async def get_characters_by_location_service(skip: int = 1, limit: int = 100, location_id: str = None):
    try:
        location_db = await db["location"].find_one({"_id": ObjectId(location_id)})
        if not location_db:
            return []
    except Exception as e:
        print(f"Error finding location: {str(e)}")
        return []

    try:
        characters_locations_db = await db["character_location"].find({"location_id": location_id}).skip((skip - 1) * limit).limit(limit).to_list(None)
        if not characters_locations_db:
            return []
    except Exception as e:
        print(f"Error finding character locations: {str(e)}")
        return []

    characters_db = []
    for character_location in characters_locations_db:
        try:
            character_db = await db["character"].find_one({"_id": ObjectId(character_location["character_id"])})
            if not character_db:
                return []
            character_db["characteristics"] = character_location["characteristics"]
            character_db["_id"] = str(character_db["_id"])
            characters_db.append(character_db)
        except Exception as e:
            print(f"Error finding character: {str(e)}")
            return []

    return characters_db


async def create_character_service(character: SchemaCreateCharacter, user_id: str):
    try:
        character_db = Character(**character.dict())
        character_db.created_by = user_id
        character_db.updated_by = user_id
        character_created = await db["character"].insert_one(character_db.dict())

        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=str(character_created.inserted_id),
            _element_type="character",
            _process="create_character",
        )

        task_celery = generate_character_task.delay(
            _character_id=str(character_created.inserted_id),
            _user_id=user_id,
            _task_id=str(task_db["_id"]),
        )
        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )

        await db["character"].update_one(
            {"_id": character_created.inserted_id},
            {"$set": {"tasks_request": [str(task_db["_id"])]}},
        )

        if character_db := await db["character"].find_one({"_id": character_created.inserted_id}):
            character_db["task_id"] = str(task_db["_id"])
            return character_db
    except Exception as e:
        print(f"Error in create character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not created",
        )


async def get_character_leading_role_service(game_id: str):
    try:
        character_db = await db['character'].find_one({'game_id': game_id, 'type': 'leading role'})
        if not character_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found",
            )
        return character_db
    except Exception as e:
        print(f"Error in get character leading role service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not found",
        )


async def update_character_service(
        character_id: str, user_id: str, name: str = None, prompt_user: str = None, dialog: str = None, type_dialog: str = None
):
    name_or_prompt_user_changed = False
    dialog_changed = False
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})

    if prompt_user != character_db["prompt_user"]:
        name_or_prompt_user_changed = True

    if  dialog != character_db["prompt_user_dialog"]:
        dialog_changed = True

    if type_dialog != character_db["conversation_type"]:
        dialog_changed = True

    try:
        if character_db := await db["character"].find_one({"_id": ObjectId(character_id)}):
            update_fields = {"updated_at": datetime.utcnow()}
            if name is not None:
                update_fields["name"] = name
            if prompt_user is not None:
                update_fields["prompt_user"] = prompt_user
            await db["character"].update_one(
                {"_id": ObjectId(character_id)}, {"$set": update_fields}
            )
            character_db = await db["character"].find_one({"_id": ObjectId(character_id)})

            if not character_db["game_id"]:
                game_db = await db["game"].find_one({"characters_id": {"$in": [character_id]}})
                if game_db:
                    character_db["game_id"] = str(game_db["_id"])

            if name_or_prompt_user_changed or dialog_changed:

                task_db = await create_task_service(
                    _task_id="",
                    _user_id=user_id,
                    _task_data={},
                    _element_id=str(character_id),
                    _element_type="character",
                    _process="update_character",
                )
                task_celery = update_character_task.delay(
                    _character_id=str(character_id), _user_id=user_id, _task_id=str(task_db["_id"]), _game_id=character_db["game_id"], _updated_data=name_or_prompt_user_changed, _updated_voice=dialog_changed
                )
                await update_task_service(
                    _id=str(task_db["_id"]),
                    _task_id=task_celery.id,
                )
                character_db["tasks_request"].append(str(task_db["_id"]))
                await db["character"].update_one(
                    {"_id": ObjectId(character_id)},
                    {"$set": {"tasks_request": character_db["tasks_request"]}},
                )
                character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
                character_db["task_id"] = str(task_db["_id"])
            return character_db
    except Exception as e:
        print(f"Error in update character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not updated",
        )


async def generate_image_character_service(character_id: str, user_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    try:
        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=character_id,
            _element_type="character",
            _process="generate_image_character",
        )
        task_celery = generate_image_character_task.delay(
            _character_id=character_id, _user_id=user_id, _task_id=str(task_db["_id"])
        )
        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery,
        )
        character_db["tasks_request"].append(str(task_db["_id"]))
        await db["character"].update_one(
            {"_id": ObjectId(character_id)},
            {"$set": {"tasks_request": character_db["request_tasks"]}},
        )

        character_db["task_id"] = str(task_db["_id"])
        return character_db
    except Exception as e:
        # print(f"Error in generate image character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not generated",
        )


async def delete_character_service(character_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )
    # if character_db['image']:
    #     delete_image(character_db['image'])
    if (
            character_location_db := await db["character_location"]
                    .find({"character_id": character_id})
                    .to_list(None)
    ):
        for character_location in character_location_db:
            await db["character_location"].delete_one({"_id": character_location["_id"]})
    delete_character = await db["character"].delete_one({"_id": ObjectId(character_id)})
    if delete_character:
        return True
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Character not found",
    )


async def add_character_to_location_service(character_id: str, location_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})

    if not character_db or not location_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character or Location not found",
        )
    try:
        existing_entry = await db["character_location"].find_one(
            {"character_id": character_id, "location_id": location_id}
        )
        if existing_entry:
            return "Character already added to location"

        character_location_data = CharacterLocationModel(
            character_id=character_id,
            location_id=location_id,
            characteristics={},
            created_by=character_db["created_by"],
            updated_by=character_db["updated_by"],
        )
        await db["character_location"].insert_one(character_location_data.dict())

    except Exception as e:
        print(f"Error in add character to location service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not added to location",
        )

    return "character added to location"


async def add_or_edit_character_location(
        character_id: str, location_id: str, characteristics: dict, user_id: str
):
    existing_entry = await db["character_location"].find_one(
        {"character_id": character_id, "location_id": location_id}
    )

    if existing_entry:
        await db["character_location"].update_one(
            {"_id": existing_entry["_id"]},
            {
                "$set": {
                    "characteristics": characteristics,
                    "updated_by": user_id,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return "Character location updated successfully"
    else:
        character_location_data = CharacterLocationModel(
            character_id=character_id,
            location_id=location_id,
            characteristics=characteristics,
            created_by=user_id,
            updated_by=user_id,
        )
        await db["character_location"].insert_one(character_location_data.dict())
        return "Character location added successfully"


async def remove_character_location(character_id: str, location_id: str):
    existing_entry = await db["character_location"].find_one(
        {"character_id": character_id, "location_id": location_id}
    )

    if existing_entry:
        await db["character_location"].delete_one({"_id": existing_entry["_id"]})
        return "Character location removed successfully"
    return "Character location not found"