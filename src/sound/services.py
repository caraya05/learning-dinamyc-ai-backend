from fastapi import HTTPException
from fastapi import status

from core.database import db


async def get_sounds_service():
    try:
        sounds_db = await db['sound'].find().to_list(None)
        return sounds_db
    except Exception as e:
        print(f"error in get_sounds_service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Error in get sounds service")

