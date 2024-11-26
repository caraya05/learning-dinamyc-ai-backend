from datetime import datetime
from uuid import uuid4

from bson import ObjectId
from dill import objects
from fastapi import HTTPException
from redis.commands.search.reducers import count

from core.database import db
from starlette import status

from object.models import Object

from object.schemas import SchemaCreateObject, ObjectLocationModel
from object.schemas import SchemaCreateItem
from task.services import create_task_service, update_task_service
from user.services import validate_star_user_service, disable_user_service

# from object.schemas import SchemaPartialUpdateObject

from utils import upload_image, delete_image

from celery_worker import generate_item_task, updated_item_task


async def get_objects_service(game: str = None,
                              location: str = None,
                              user: str = None,
                              skip: int = 0,
                              limit: int = 100):
    """
    Get a list of objects.
    """
    try:
        if location:
            objects_db = (
                await db["item"]
                .find({"locations_id": {"$in": [location]}})
                .skip((skip - 1) * limit)
                .limit(limit)
                .to_list(None)
            )
            count_objects = (
                await db["item"]
                .count_documents({"locations_id": {"$in": [location]}})
            )
        elif game:
            objects_db = (
                await db["item"]
                .find({"games_id": {"$in": [game]}})
                .skip((skip - 1) * limit)
                .limit(limit)
                .to_list(None)
            )
            count_objects = (
                await db["item"]
                .count_documents({"games_id": {"$in": [game]}})
            )
        else:
            objects_db = (
                await db["item"]
                .find({"created_by": user})
                .skip(skip)
                .limit(limit)
                .to_list(None)
            )
            count_objects = (
                await db["item"]
                .count_documents({"created_by": user})
            )
        if objects_db:
            for object_db in objects_db:
                object_db["_id"] = str(object_db["_id"])
                item_characteristics = await db["object_location"].find(
                    {"item_id": object_db["_id"]}).to_list(None)
                if item_characteristics:
                    for item_characteristic in item_characteristics:
                        del item_characteristic["_id"]
                        del item_characteristic["item_id"]
                        del item_characteristic["updated_at"]
                        del item_characteristic["updated_by"]
                        del item_characteristic["created_at"]
                        del item_characteristic["created_by"]
                    object_db["characteristics"] = item_characteristics
        return objects_db, count_objects
    except Exception as e:
        print(f"Error in get objects service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objects not found",
        )


async def retrieve_object_service(object_id: str):
    """
    Retrieve a object.
    """
    try:
        if object_db := (await db["item"].find_one({"_id": ObjectId(object_id)})):
            object_db["characteristics"] = await db["object_location"].find_one(
                {"item_id": object_id}
            )
            if object_db:
                item_characteristics = await db["object_location"].find(
                    {"item_id": object_id}).to_list(None)
                if item_characteristics:
                    for i in range(len(item_characteristics)):
                        del item_characteristics[i]["_id"]
                        del item_characteristics[i]["item_id"]
                        del item_characteristics[i]["updated_at"]
                        del item_characteristics[i]["updated_by"]
                        del item_characteristics[i]["created_at"]
                        del item_characteristics[i]["created_by"]
                    object_db["characteristics"] = item_characteristics
            return object_db
    except Exception as e:
        print(f"Error in retrieve object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )


async def delete_object_service(object_id: str):
    """
    Delete a object.
    """
    try:
        item_db = await db["item"].find_one({"_id": ObjectId(object_id)})
        # if item_db['image']:
        #     delete_image(item_db['image'])
        object_deleted = await db["object"].delete_one({"_id": ObjectId(object_id)})
        if object_deleted.deleted_count:
            return True
    except Exception as e:
        print(f"Error in delete object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )


async def create_item_service(schema: SchemaCreateObject, user_id: str):
    """
    Create a new object.
    """
    try:
        schema_object = Object(**schema.dict())
        schema_object.created_by = user_id
        schema_object.updated_by = user_id
        object_created = await db["item"].insert_one(schema_object.dict())
        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=str(object_created.inserted_id),
            _element_type="item",
            _process="generate image item",
        )

        task_celery = generate_item_task.delay(
            _item_id=str(object_created.inserted_id),
            _user_id=user_id,
            _task_id=str(task_db["_id"]),
        )
        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )
        await db["item"].update_one({"_id": object_created.inserted_id},
                                    {"$set": {"tasks_request": [str(task_db["_id"])]}})
        object_db = await db["item"].find_one({"_id": object_created.inserted_id})
        object_db["task_id"] = str(task_db["_id"])
        return object_db

    except Exception as e:
        print(f"Error in create object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )


async def update_item_service(object_id: str, schema: SchemaCreateItem):
    """
    Update a object.
    """
    try:
        updated_prompt_user = False
        updated_dialog = False
        item_db = await db["item"].find_one({"_id": ObjectId(object_id)})
        if schema.name:
            item_db["name"] = schema.name
        if schema.prompt_user:
            if item_db["prompt_user"] != schema.prompt_user:
                updated_prompt_user = True
            item_db["prompt_user"] = schema.prompt_user
        if schema.prompt_user_dialog:
            if item_db["prompt_user_dialog"] != schema.prompt_user_dialog:
                updated_dialog = True
            item_db["prompt_user_dialog"] = schema.prompt_user_dialog

        item_db["updated_at"] = datetime.utcnow()
        await db["item"].update_one({"_id": ObjectId(object_id)}, {"$set": item_db})
        if updated_dialog or updated_prompt_user:
            await validate_star_user_service(user_id=item_db["created_by"])
            await  disable_user_service(user_id=item_db["created_by"], section="item")
            task_db = await create_task_service(
                _task_id="",
                _user_id=item_db["created_by"],
                _task_data={},
                _element_id=object_id,
                _element_type="item",
                _process="generate image item",
            )
            task_celery = updated_item_task.delay(
                _item_id=object_id,
                _user_id=item_db["created_by"],
                _task_id=str(task_db["_id"]),
                _updated_prompt_user=updated_prompt_user,
                _updated_dialog=updated_dialog,
            )
            await update_task_service(
                _id=str(task_db["_id"]),
                _task_id=task_celery.id,
            )
            await db["item"].update_one({"_id": ObjectId(object_id)},
                                        {"$set": {"tasks_request": [str(task_db["_id"])]}})

            object_db = await db["item"].find_one({"_id": ObjectId(object_id)})
            object_db["task_id"] = str(task_db["_id"])
            return object_db

        return await db["item"].find_one({"_id": ObjectId(object_id)})

    except Exception as e:
        print(f"Error in update object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not updated",
        )


async def add_item_location_service(item_id: str, location_id: str):
    """
    Add a object to a location.
    """

    item_db = await db["item"].find_one({"_id": ObjectId(item_id)})
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})

    if not item_db or not location_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item or location not found",
        )
    if "locations_id" in item_db and item_db.get("locations_id"):
        if location_id not in item_db.get("locations_id", []):
            item_db["locations_id"].append(location_id)
    else:
        item_db["locations_id"] = [location_id]

    await db["item"].update_one({"_id": ObjectId(item_id)}, {"$set": {"locations_id": item_db["locations_id"]}})

    existing_entry = await db["object_location"].find_one(
        {"item_id": item_id, "location_id": location_id}
    )
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Object already in location",
        )

    object_location = ObjectLocationModel(
        item_id=item_id,
        location_id=location_id,
        characteristics={},
        created_by=item_db["created_by"],
        updated_by=item_db["updated_by"],
    )
    try:
        await db["object_location"].insert_one(object_location.dict())

        return "item added to location"

    except Exception as e:
        print(f"Error in add item location service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not added to location",
        )


async def add_or_edit_item_characteristic_service(
        item_id: str, location_id: str, characteristics: dict, user_id: str
):
    """
    Add or edit a characteristic to a object in a location.
    """
    existing_entry = await db["object_location"].find_one(
        {"item_id": item_id, "location_id": location_id}
    )
    if existing_entry:
        await db["object_location"].update_one(
            {"_id": existing_entry["_id"]},
            {
                "$set": {
                    "characteristics": characteristics,
                    "updated_at": datetime.utcnow(),
                    "updated_by": user_id,
                }
            },
        )

        return "Item characteristic updated"
    else:
        object_location = ObjectLocationModel(
            item_id=item_id,
            location_id=location_id,
            characteristics=characteristics,
            created_by=user_id,
            updated_by=user_id,
        )

        await db["object_location"].insert_one(object_location.dict())

        return "Item characteristic added"


async def get_item_by_location_service(location_id: str):
    """
    Get a list of objects in a location.
    """
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})
    if not location_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )
    try:
        if (
                object_locations_db := await db["object_location"]
                        .find({"location_id": location_id})
                        .to_list(None)
        ):
            objects_db = []
            for object_location in object_locations_db:
                object_db = await db["item"].find_one(
                    {"_id": ObjectId(object_location["object_id"])}
                )
                object_db["characteristics"] = object_location["characteristics"]
                object_db["_id"] = str(object_db["_id"])
                objects_db.append(object_db)
            return objects_db
    except Exception as e:
        print(f"Error in get item by location service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objects not found",
        )


async def get_all_object_service(user_id: str, skip: int = 1, limit: int = 10):
    """
    Get all objects.
    """
    try:
        objects_db = await (
            db["object"]
            .find({"created_by": user_id})
            .sort("created_at", -1)
            .skip((skip - 1) * limit)
            .limit(limit)
            .to_list(None)
        )
        return objects_db
    except Exception as e:
        print(f"Error in get all object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objects not found",
        )
