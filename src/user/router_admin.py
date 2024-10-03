from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi import UploadFile
from fastapi import File
from fastapi.security import HTTPAuthorizationCredentials
from uuid import uuid4

from auth.auth import auth_admin
from auth.utils import auth_schema
from core.database import db
from utils import upload_image

from user.services import get_user_by_id_service
from user.services import create_user_service
from user.services import update_photo_service
from user.services import update_attempt_to_create_service

from user.schemas import SchemaRetrieveUser
from user.schemas import SchemaUser

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", status_code=status.HTTP_200_OK)
async def get_users(
    user_db: dict = Depends(auth_admin), Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    users_db = await db["user"].find({"is_superuser": False, "is_staff": False}).to_list(None)
    for user in users_db:
        user["_id"] = str(user["_id"])
        # del user["_id"]
    return users_db
