from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core.database import db


async def get_customize_by_id_service(customize_id: str):
    try:
        customize_db = await db["customize"].find_one({"_id": ObjectId(customize_id)})
        return customize_db
    except Exception as e:
        print(f"Error in get customize by id service: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customize not found",
        )


async def get_customize_by_type_character_service(gender: str, type_customize: str):
    gender = gender.lower()
    try:
        customize_all = await db["customize"].find({"gender": gender, "type_customize": type_customize}).to_list(None)
        count_customize = await db["customize"].count_documents({})
        return customize_all, count_customize

    except Exception as e:
        print(f"Error in get customize by type character service: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customize not found",
        )
