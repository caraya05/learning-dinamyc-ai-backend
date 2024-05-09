from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from core.database import db
from starlette import status

from object.models import Object

from object.schemas import SchemaCreateObject
# from object.schemas import SchemaPartialUpdateObject

from utils import upload_image


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
        object_db["image"] = image
        await db["object"].update_one({"_id": ObjectId(object_id)}, {"$set": object_db})
        return await db["object"].find_one({"_id": ObjectId(object_id)})
    except Exception as e:
        print(f"Error in update image object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )
