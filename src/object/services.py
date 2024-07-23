from datetime import datetime
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from core.database import db
from starlette import status

from object.models import Object

from object.schemas import SchemaCreateObject, ObjectLocationModel
from object.schemas import SchemaCreateItem
# from object.schemas import SchemaPartialUpdateObject

from utils import upload_image, delete_image


async def get_objects_service(game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of objects.
    """
    try:
        objects_db = await db["object"].find({"game_id": game_id}).skip(skip).limit(limit).to_list(None)
        count_objects = await db["object"].count_documents({"game_id": game_id})
        return objects_db, count_objects
    except Exception as e:
        print(f"Error in get objects service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objects not found",
        )


async def create_object_service(schema: SchemaCreateObject, user_id: str):
    """
    Create a new object.
    """
    try:
        schema_object = Object(**schema.dict())
        if schema.image:
            schema_object.image = upload_image(
                url_image=schema.image,
                file_name=f"object/{uuid4()}.jpg",
                size=(512, 512),
            )
        schema_object.created_by = user_id
        schema_object.updated_by = user_id

        if object_created := await db["object"].insert_one(schema_object.dict()):
            return await db["object"].find_one({"_id": object_created.inserted_id})

    except Exception as e:
        print(f"Error in create object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )


async def retrieve_object_service(object_id: str):
    """
    Retrieve a object.
    """
    try:
        if object_db := await db["object"].find_one({"_id": ObjectId(object_id)}):
            return object_db
    except Exception as e:
        print(f"Error in retrieve object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )


# def partial_update_object_service(object_id: str, object: SchemaPartialUpdateObject):
#     """
#     Partial update a object.
#     """
#     db_object = get_object_by_field(db, "id", object_id)
#     for field, value in object.dict().items():
#         setattr(db_object, field, value) if value else None
#     db.commit()
#     db.refresh(db_object)
#     return db_object


async def delete_object_service(object_id: str):
    """
    Delete a object.
    """
    try:
        item_db = await db["object"].find_one({"_id": ObjectId(object_id)})
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


async def update_image_object_service(object_id: str, image: str):
    """
    Update image of a object.
    """
    try:
        object_db = await db["object"].find_one({"_id": ObjectId(object_id)})
        # if object_db['image']:
        #     delete_image(object_db['image'])
        object_db["image"] = image
        await db["object"].update_one({"_id": ObjectId(object_id)}, {"$set": object_db})
        return await db["object"].find_one({"_id": ObjectId(object_id)})
    except Exception as e:
        print(f"Error in update image object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )


async def create_item_service(schema: SchemaCreateItem, user_id: str):
    """
    Create a new object.
    """
    try:
        schema_object = Object(**schema.dict())
        schema_object.created_by = user_id
        schema_object.updated_by = user_id

        if object_created := await db["object"].insert_one(schema_object.dict()):
            return await db["object"].find_one({"_id": object_created.inserted_id})

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
        item_db = await db["object"].find_one({"_id": ObjectId(object_id)})
        if schema.name:
            item_db["name"] = schema.name
        if schema.prompt_user:
            item_db["prompt_user"] = schema.prompt_user

        item_db["updated_at"] = datetime.utcnow()

        await db["object"].update_one({"_id": ObjectId(object_id)}, {"$set": item_db})
        return await db["object"].find_one({"_id": ObjectId(object_id)})

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

    item_db = await db["object"].find_one({"_id": ObjectId(item_id)})
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})

    if not item_db or not location_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object or location not found",
        )

    existing_entry = await db["object_location"].find_one(
        {"object_id": item_id, "location_id": location_id})
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Object already in location",
        )

    object_location = ObjectLocationModel(
        object_id=item_id,
        location_id=location_id,
        characteristics={},
        created_by=item_db["created_by"],
        updated_by=item_db["updated_by"]
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


async def add_or_edit_item_characteristic_service(item_id: str, location_id: str, characteristics: dict, user_id: str):
    """
    Add or edit a characteristic to a object in a location.
    """

    existing_entry = await db["object_location"].find_one(
        {"object_id": item_id, "location_id": location_id})

    if existing_entry:
        await db["object_location"].update_one(
            {"object_id": item_id, "location_id": location_id},
            {"$set": {"characteristics": characteristics, "updated_at": datetime.utcnow(), "updated_by": user_id}}
        )

        return "Item characteristic updated"
    else:
        object_location = ObjectLocationModel(
            object_id=item_id,
            location_id=location_id,
            characteristics=characteristics,
            created_by=user_id,
            updated_by=user_id
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
        if object_locations_db := await db["object_location"].find({"location_id": location_id}).to_list(
                None):
            objects_db = []
            for object_location in object_locations_db:
                object_db = await db["object"].find_one({"_id": ObjectId(object_location["object_id"])})
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
        objects_db = await (db["object"]
                            .find({"created_by": user_id})
                            .sort("created_at", -1)
                            .skip((skip - 1) * limit)
                            .limit(limit)
                            .to_list(None))
        return objects_db
    except Exception as e:
        print(f"Error in get all object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objects not found",
        )
