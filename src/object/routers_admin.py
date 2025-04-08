from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from object.schemas import SchemaListObjectAdmin
from object.schemas import SchemaRetrieveObjectAdmin
from object.schemas import SchemaCreateItemAdmin
from object.schemas import SchemaRetrieveObject
from object.schemas import SchemaCreateObject

from object.services_admin import get_objects_service_admin

from object.services_admin import create_object_service_admin
from object.services_admin import update_object_service_admin
from object.services_admin import get_object_service_admin

router = APIRouter(prefix="/item", tags=["Items"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListObjectAdmin)
async def get_objects(
        page: int = 1,
        limit: int = 100000,
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all objects.

    It returns a list of objects.
    """

    objects_db = await get_objects_service_admin(skip=page, limit=limit)

    return SchemaListObjectAdmin(results=objects_db, count=len(objects_db))


@router.get("/{item_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveObjectAdmin)
async def retrieve_object(
        item_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a object.

    It returns a object.
    """

    object_db = await get_object_service_admin(object_id=item_id)

    return object_db


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveObject)
async def create_object(
        object_: SchemaCreateObject,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a new object.

    It returns the created object.
    """

    try:
        object_db = await create_object_service_admin(object_, str(user_db.get("_id")))
        return object_db

    except Exception as e:
        print(f"Error in create object: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )


@router.patch("/{item_id}", status_code=status.HTTP_200_OK)
async def update_item(
        item_id: str,
        object_: SchemaCreateItemAdmin,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint updates a object.

    It returns the updated object.
    """

    try:
        object_db = await update_object_service_admin(item_id, object_, str(user_db.get("_id")))
        return "item updated"

    except Exception as e:
        print(f"Error in create object: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )
