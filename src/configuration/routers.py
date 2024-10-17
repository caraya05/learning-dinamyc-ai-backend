from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.auth import auth_admin
from auth.utils import auth_schema

from configuration.models import Configuration

from configuration.services import get_configurations_service
from configuration.services import get_configuration_by_id_service
from configuration.services import create_configuration_service
from configuration.services import update_configuration_service
from configuration.services import delete_configuration_service

from configuration.schemas import SchemaRetrieveConfiguration
from configuration.schemas import SchemaCreateConfiguration
from configuration.schemas import SchemaUpdateConfiguration

router = APIRouter(prefix="/configuration", tags=["Configuration"])


@router.get("/", response_model=SchemaRetrieveConfiguration)
async def get_configurations(
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a list of configurations.
    """
    try:
        return await get_configurations_service()

    except Exception as e:
        print(f"Error getting configurations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configurations not found",
        )


@router.get("/{configuration_id}", response_model=SchemaRetrieveConfiguration)
async def get_configuration_by_id(
    configuration_id: str,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a configuration by id.
    """
    try:
        return await get_configuration_by_id_service(configuration_id)

    except Exception as e:
        print(f"Error getting configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )


@router.post("/", response_model=SchemaRetrieveConfiguration)
async def create_configuration(
    configuration: SchemaCreateConfiguration,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a configuration.
    """
    try:
        return await create_configuration_service(
            Configuration(
                **configuration.dict(),
                updated_by=str(user_db.get("_id")),
                created_by=str(user_db.get("_id")),
            )
        )

    except Exception as e:
        print(f"Error creating configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration not created",
        )


@router.put("/{configuration_id}", response_model=SchemaRetrieveConfiguration)
async def update_configuration(
    configuration_id: str,
    configuration: SchemaUpdateConfiguration,
    user_db: dict = Depends(auth_admin),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint updates a configuration.
    """
    try:
        return await update_configuration_service(configuration_id, **configuration.dict())

    except Exception as e:
        print(f"Error updating configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Configuration not updated"
        )


@router.delete("/{configuration_id}")
async def delete_configuration(
    configuration_id: str,
    user_db: dict = Depends(auth_admin),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint deletes a configuration.
    """
    try:
        return await delete_configuration_service(configuration_id)

    except Exception as e:
        print(f"Error deleting configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )


@router.get("/get-current-images/", status_code=status.HTTP_200_OK)
def get_current_images():
    """
    This endpoint retrieves the current images.
    """
    return {
        "splash_screen": "https://qwestar.sfo3.cdn.digitaloceanspaces.com/backend/screen/b80b7060-40b0-47dc-a523-402292d1ef23.jpeg",
        "login_screen": "https://qwestar.sfo3.cdn.digitaloceanspaces.com/backend/screen/f30c6340-2fd9-4f98-9ddc-ce484186f271.jpeg",
    }

