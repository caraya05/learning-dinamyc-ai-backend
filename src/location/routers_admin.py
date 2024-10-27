from bson import ObjectId
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth_admin
from auth.utils import auth_schema
from core import db

from location.schemas_admin import SchemaUpdateLocation

from location.services_admin import get_locations_service_admin
from location.services_admin import get_location_service_admin
from location.services_admin import update_location_service_admin

router = APIRouter(prefix="/location", tags=["Location"])


@router.get("/", status_code=status.HTTP_200_OK)
async def get_locations(
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    return await get_locations_service_admin()


@router.get("/{location_id}", status_code=status.HTTP_200_OK)
async def get_location(
        location_id: str,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    if location_db := await get_location_service_admin(location_id):
        return location_db
    raise HTTPException(status_code=404, detail="Location not found")


@router.put("/{location_id}", status_code=status.HTTP_200_OK)
async def update_location(
        location_id: str,
        location: SchemaUpdateLocation,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    if location_db := await update_location_service_admin(location_id, location, user_db["_id"]):
        return location_db
    raise HTTPException(status_code=404, detail="Location not found")