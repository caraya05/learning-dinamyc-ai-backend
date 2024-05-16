from bson import ObjectId
from fastapi import HTTPException

from starlette import status

from core.database import db
from scene.models import Scene

from scene.schemas import SchemaCreateScene
from scene.schemas import SchemaPartialUpdateScene

from utils import upload_image

from uuid import uuid4


async def get_scenes_service(script_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of scenes.
    """
    try:
        scenes_db = await db["scene"].find({"script_id": script_id}).skip(skip).limit(limit).to_list(None)
        count_scenes = await db["scene"].count_documents({"script_id": script_id})
        return scenes_db, count_scenes
    except Exception as e:
        print(f"Error in get scenes service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenes not found.")


async def get_scene_service(scene_id: str):
    """
    Get a scene.
    """
    try:
        scene_db = await db["scene"].find_one({"_id": ObjectId(scene_id)})
        # if scene_db.sound_id:
        #     scene.sound = get_sound_by_field(db, "id", scene.sound_id).sound
        return scene_db
    except Exception as e:
        print(f"Error in get scene service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found.")


async def create_scene_service(schema: SchemaCreateScene, user_id: str):
    """
    Create a scene.
    """
    try:
        scene_schema = Scene(**schema.dict())
        if scene_schema.start_image:
            scene_schema.start_image = upload_image(
                url_image=schema.start_image,
                file_name=f"scene/{uuid4()}.jpg",
                size=(512, 896),
            )

        if scene_schema.image_defeat:
            scene_schema.image_defeat = upload_image(
                url_image=schema.image_defeat,
                file_name=f"scene/{uuid4()}.jpg",
                size=(512, 896),
            )

        scene_schema.created_by = user_id
        scene_schema.updated_by = user_id
        scene_created = await db["scene"].insert_one(scene_schema.dict())
        if scene_db := await db["scene"].find_one({"_id": scene_created.inserted_id}):
            return scene_db
    except Exception as e:
        print(f"Error in create scene service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scene not created.")


async def partial_update_scene_service(scene_id: str, schema: SchemaPartialUpdateScene):
    """
    Partially update a scene.
    """
    try:
        scene_db = await db["scene"].find_one({"_id": ObjectId(scene_id)})
        for field, value in schema:
            setattr(scene_db, field, value)
        scene_updated = await db["scene"].update_one({"_id": ObjectId(scene_id)}, {"$set": scene_db})
        if scene_updated.modified_count:
            scene_db = await db["scene"].find_one({"_id": ObjectId(scene_id)})
            return scene_db
    except Exception as e:
        print(f"Error in partial update scene service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scene not updated.")


async def get_last_scene_service(script_id: str, number: int = 4):
    """
    Get the last scene.
    """
    try:
        scene_db = await db["scene"].find_one({"script_id": script_id, "order": number})
        return scene_db
    except AttributeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene not found")


async def delete_scene_service(scene_id: str):
    """
    Delete a scene.
    """
    try:
        scene_deleted = await db["scene"].delete_one({"_id": ObjectId(scene_id)})
        if scene_deleted.deleted_count:
            return True
    except Exception as e:
        print(f"Error in delete scene service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scene not deleted.")
