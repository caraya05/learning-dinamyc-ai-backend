from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
import requests
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
from configuration.schemas import SchemaListConfiguration
from configuration.schemas import SchemaCreateConfiguration
from configuration.schemas import SchemaUpdateConfiguration

from core.database import db
from utils import upload_image_from_url
from utils import upload_audio
from pydub import AudioSegment
from io import BytesIO
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
async def traverse_structure(data, collection_name: str):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                data[key] = await traverse_structure(value, collection_name)
            elif isinstance(value, str) and "https://" in value:
                print(f"Key: {key}, Value: {value.split('backend/')[-1]}")
                if key == "image" or key == "image_minimalist":
                    # new_value = upload_image_from_url(
                    #     url_image=value,
                    #     file_name=value.split('backend/')[-1],
                    # )
                    new_value = value.replace("storage.cloud.google.com", "storage.googleapis.com").split("?")[0]
                    data[key] = new_value  # Actualizar el valor en el diccionario
                elif key == "audio":
                    try:
                        # Descargar el audio desde la URL
                        # response = requests.get(value)
                        # if response.status_code != 200:
                        #     raise HTTPException(
                        #         status_code=status.HTTP_400_BAD_REQUEST,
                        #         detail="No se pudo descargar el audio desde la URL.",
                        #     )

                        # Convertir el contenido descargado a un objeto BytesIO
                        # audio_in_memory = BytesIO(response.content)
                        # audio_in_memory.seek(0)

                        # Subir el audio descargado
                        # new_value = upload_audio(
                        #     file_name=value.split('backend/')[-1],
                        #     audio_byte_arr=audio_in_memory,
                        # )
                        new_value = value.replace("storage.cloud.google.com", "storage.googleapis.com").split("?")[0]

                        data[key] = new_value
                    except Exception as e:
                        print(f"Error procesando el audio para la clave '{key}': {e}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al procesar el archivo de audio.",
                        )
    elif isinstance(data, list):
        for index, item in enumerate(data):
            data[index] = await traverse_structure(item, collection_name)

    return data

@router.get("/transfer-statics/", status_code=status.HTTP_200_OK)
async def transfer_statics():
    """
    This endpoint transfers the statics.
    """
    all_state_glic = await db["state_glic"].find({}).to_list(None)
    for i in all_state_glic:
        updated_data = await traverse_structure(i, "state_glic")
        if "_id" in updated_data:
            await db["state_glic"].update_one(
                {"_id": updated_data["_id"]}, {"$set": updated_data}
            )

    all_games = await db["game"].find({}).to_list(None)
    for i in all_games:
        updated_data = await traverse_structure(i, "game")
        if "_id" in updated_data:
            await db["game"].update_one(
                {"_id": updated_data["_id"]}, {"$set": updated_data}
            )
    all_events = await db["event"].find({}).to_list(None)
    for i in all_events:
        updated_data = await traverse_structure(i, "event")
        if "_id" in updated_data:
            await db["event"].update_one(
                {"_id": updated_data["_id"]}, {"$set": updated_data}
            )

    return {"message": "Transfer statics completed successfully."}