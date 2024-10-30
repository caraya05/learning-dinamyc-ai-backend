from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from celery_worker import generate_location_task, generate_image_location_task
from core.database import db

from character.services import get_characters_by_location_service
from location.models import Location
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation
from task.services import create_task_service, update_task_service


async def get_locations_service(*, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of locations.
    """
    try:
        locations = (
            await db['location'].find({"game_id": game_id}).skip(skip).limit(limit).to_list(None)
        )
        count_locations = await db['location'].count_documents({"game_id": game_id})
        return locations, count_locations
    except Exception as e:
        print(f"Error in get locations service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locations not found.")


async def get_location_service(*, location_id: str, user_id: str) -> dict:
    """
    Get a location.
    """
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
            if location_db["sound"]:
                location_db["sound"] = await db['sound'].find_one(
                    {"_id": ObjectId(location_db["sound"])}
                )

            if location_db["config"]:
                user_config_found = False
                for config in location_db["config"]:
                    if config["user"] == user_id:
                        location_db["configuration"] = config["config"]
                        user_config_found = True
                        break
                if not user_config_found and location_db["config"]:
                    location_db["configuration"] = location_db["config"][0]["config"]

            if location_db.get("connect", None):
                user_connect_found = False
                for connect in location_db["connect"]:
                    if connect["user"] == user_id:
                        location_db["connections"] = connect["connect"]
                        user_connect_found = True
                        break
                if not user_connect_found and location_db["connect"]:
                    location_db["connections"] = location_db["connect"][0]["connect"]

            if characters_db := await get_characters_by_location_service(
                skip=1, limit=100, location_id=location_id
            ):
                location_db["characters"] = characters_db
            return location_db
    except Exception as e:
        print(f"Error in get location service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")


async def get_locations_v2_service(*, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of locations.
    """
    try:

        game_db = await db['game'].find_one({"_id": ObjectId(game_id)})
        locations = await (
            db['location']
            .find({"_id": {"$in": [ObjectId(i) for i in game_db["locations_id"]]}})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
            .to_list(None)
        )
        count_locations = await db['location'].count_documents(
            {"_id": {"$in": [ObjectId(i) for i in game_db["locations_id"]]}}
        )

        return locations, count_locations
    except Exception as e:
        print(f"Error in get locations service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locations not found.")


async def create_location_service(location: SchemaCreateLocation, user_id: str):
    """
    Create a location.
    """
    try:
        location_schema = Location(**location.dict())
        location_schema.created_by = user_id
        location_schema.updated_by = user_id
        location_created = await db['location'].insert_one(location_schema.dict())

        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=str(location_created.inserted_id),
            _element_type="location",
            _process="generate_location",
        )

        task_celery = generate_location_task.delay(
            _location_id=str(location_created.inserted_id),
            _user_id=user_id,
            _task_id=str(task_db["_id"]),
        )

        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )

        await db['location'].update_one(
            {"_id": location_created.inserted_id},
            {"$set": {"tasks_request": [str(task_celery.id)]}},
        )
        if location_db := await db['location'].find_one({"_id": location_created.inserted_id}):
            location_db["task_id"] = str(task_db["_id"])
            return location_db
    except Exception as e:
        print(f"Error in create location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location not created")


async def partial_update_location_service(
    *, location_id: str, location: SchemaPartialUpdateLocation, user_id: str,
):
    """
    Partially update a location.
    """

    title_or_prompt_user_changed = False
    config_edited = False
    connect_edited = False

    location_db = await db['location'].find_one({"_id": ObjectId(location_id)})

    if location.title and location.title != location_db.get("title"):
        title_or_prompt_user_changed = True
    if location.prompt_user and location.prompt_user != location_db.get("prompt_user"):
        title_or_prompt_user_changed = True

    if location.configuration and location.configuration != location_db.get("config"):
        config_edited = True
    if location.connections and location.connections != location_db.get("connect"):
        connect_edited = True
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
            location_db["updated_by"] = user_id
            if location.title:
                location_db["title"] = location.title
            if location.prompt_user:
                location_db["prompt_user"] = location.prompt_user
            if location.configuration:
                if not location_db["config"]:
                    location_db["config"] = []
                    json_config = {
                        "config": location.configuration,
                        "user": user_id,
                    }
                    location_db["config"].append(json_config)
                else:
                    for i in range(len(location_db["config"])):
                        if location_db["config"][i]["user"] == user_id:
                            location_db["config"][i]["config"] = location.configuration
            if location.connections:
                if not location_db.get("connect", None):
                    location_db["connect"] = []
                    json_connect = {
                        "connect": location.connections,
                        "user": user_id,
                    }
                    location_db["connect"].append(json_connect)
                else:
                    for i in range(len(location_db["connect"])):
                        if location_db["connect"][i]["user"] == user_id:
                            location_db["connect"][i]["connect"] = location.connections
            await db['location'].update_one({"_id": ObjectId(location_id)}, {"$set": location_db})
            location_db = await db['location'].find_one({"_id": ObjectId(location_id)})
            if title_or_prompt_user_changed  or ( not config_edited and not connect_edited and title_or_prompt_user_changed):
                task_db = await create_task_service(
                    _task_id="",
                    _user_id=user_id,
                    _task_data={},
                    _element_id=str(location_id),
                    _element_type="location",
                    _process="update_location",
                )
                task_celery = generate_location_task.delay(
                    _location_id=location_id, _user_id=user_id, _task_id=str(task_db["_id"])
                )
                await update_task_service(
                    _id=str(task_db["_id"]),
                    _task_id=task_celery.id,
                )
                location_db["tasks_request"] = location_db["tasks_request"].append(str(task_db["_id"]))
                await db['location'].update_one(
                    {"_id": ObjectId(location_id)},
                    {"$set": {"tasks_request": location_db["tasks_request"]}},
                )
                location_db = await db['location'].find_one({"_id": ObjectId(location_id)})
                location_db["task_id"] = str(task_db["_id"])
            return location_db
    except Exception as e:
        print(f"Error in partial update location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location not updated.")


async def generate_image_location_service(location_id: str, user_id: str):
    """
    Generate an image for a location.
    """
    try:
        location_db = await db['location'].find_one({"_id": ObjectId(location_id)})
        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=location_id,
            _element_type="location",
            _process="generate_image_location",
        )
        task_celery = generate_image_location_task.delay(
            _location_id=location_id, _user_id=user_id, _task_id=str(task_db["_id"])
        )

        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )

        if not isinstance(location_db["tasks_request"], list):
            location_db["tasks_request"] = []
        location_db["tasks_request"].append(str(task_db["_id"]))

        await db['location'].update_one(
            {"_id": ObjectId(location_id)},
            {"$set": {"tasks_request": location_db["tasks_request"]}},
        )

        location_db["task_id"] = str(task_db["_id"])
        return location_db
    except Exception as e:
        print(f"Error in generate image location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image not generated.")


async def get_all_location_service(user_id: str, skip: int = 1, limit: int = 10):
    try:
        characters_db = await (db["location"]
                               .find({"created_by": user_id})
                               .sort("created_at", -1)
                               .skip((skip - 1) * limit)
                               .limit(limit)
                               .to_list(None))
        count_characters = await db["location"].count_documents({"created_by": user_id})
        return characters_db, count_characters
    except Exception as e:
        print(f"Error in get all character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characters not found",
        )


async def delete_location_service(location_id: str):
    """
    Delete a location.
    """
    try:
        if location_deleted := await db['location'].delete_one({"_id": ObjectId(location_id)}):
            if location_deleted.deleted_count:
                return True
    except Exception as e:
        print(f"Error in delete location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location not deleted.")
