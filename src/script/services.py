from bson import ObjectId
from fastapi import HTTPException

from fastapi import status

from script.models import Chapter

from core.database import db

from script.schemas import SchemaCreateScript
from script.schemas import SchemaPartialUpdateScript


async def get_script_by_id_service(script_id: str) -> dict:
    """
    Get a script by id.
    """
    if script_db := await db['chapter'].find_one({"_id": ObjectId(script_id)}):
        return script_db
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail="Script not found.")


async def get_script_by_game_id_service(game_id: str) -> dict:
    """
    Get a script by game id.
    """
    if script_db := await db['chapter'].find_one({"game_id": game_id}):
        return script_db
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail="Script not found.")


async def get_scripts_service(game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of scripts.
    """
    try:
        scripts_db = await db['chapter'].find({"game_id": game_id}).skip(skip).limit(limit).to_list(None)
        counts = await db['chapter'].count_documents({"game_id": game_id})
        return scripts_db, counts
    except Exception as e:
        print(f"Error in get scripts service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Scripts not found.")


# def get_script_service(db: Session, script_id: str):
#     """
#     Get a script.
#     """
#     script = get_script_by_field(db, "id", script_id)
#     return script


async def create_chapter_service(schema: SchemaCreateScript, user_id: str, status_script: int = 0):
    """
    Create a script.
    """
    try:
        script = Chapter(**schema.dict())
        script.status = status_script
        script.status_character = status_script
        script.status_location = status_script
        script.status_scene = status_script
        script.created_by = user_id
        script.updated_by = user_id

        if chapter_created := await db['chapter'].insert_one(script.dict()):
            return await db['chapter'].find_one({"_id": chapter_created.inserted_id})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))


async def partial_update_script_service(script_id: str, schema: SchemaPartialUpdateScript) -> dict:
    """
    Partially update a script.
    """
    try:
        if script_db := await db['chapter'].find_one({"_id": ObjectId(script_id)}):
            print("script_db", script_db)
            script_db["status"] = schema.status if schema.status else script_db.get("status")
            script_db["status_character"] = (
                schema.status_character if schema.status_character else script_db.get("status_character")
            )
            script_db["status_location"] = (
                schema.status_location if schema.status_location else script_db.get("status_location")
            )
            script_db["status_scene"] = schema.status_scene if schema.status_scene else script_db.get("status_scene")

            await db['chapter'].update_one({"_id": ObjectId(script_id)}, {"$set": script_db})
            return await db['chapter'].find_one({"_id": ObjectId(script_id)})
    except Exception as e:
        print(f"Error in partial update script service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Script not updated.")


async def delete_script_service(script_id: str):
    """
    Delete a script.
    """
    try:
        script_deleted = await db['chapter'].delete_one({"_id": ObjectId(script_id)})
        if script_deleted.deleted_count:
            return {"message": "Script deleted successfully."}
    except Exception as e:
        print(f"Error in delete script service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Script not deleted.")
