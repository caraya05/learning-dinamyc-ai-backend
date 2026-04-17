from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import File, UploadFile, Form, Request
import traceback
from typing import Optional

from auth.auth import auth, auth_team
from auth.utils import auth_schema
from game.services import GameService

from location.schemas import SchemaListLocation, SchemaDeactivateLocation
from location.schemas import SchemaRetrieveLocation
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation

from location.services import (
    get_locations_v2_service,
    get_all_location_service,
    deactivate_location_service,
)
from location.services import get_location_service
from location.services import create_location_service
from location.services import partial_update_location_service

from location.text_update_services import LocationTextUpdateService
from game.text_update_schemas import (
    SchemaUpdateLocationData,
    SchemaLocationStateDataResponse,
)

from location.image_update_services import LocationImageUpdateService

from tasks_shared import process_interaction_video_task
# TODO: falta implemntar el desconteo de estrellas
from user.services import validate_star_user_service

router = APIRouter(prefix="/location", tags=["Location"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListLocation)
async def get_locations(
        game_id: str = None,
        publish: bool = False,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        game_service=Depends(GameService)
):
    """
    This endpoint retrieves all locations.

    It returns a list of locations.
    """
    if publish:
        try:
            locations_db = await game_service.get_locations_game_publish_service(game_id=game_id)

            for location in locations_db:
                location["_id"] = f'{location["_id"]}_{game_id}'

            return SchemaListLocation(results=locations_db, count=len(locations_db))
        except Exception as e:
            print(f"Error in get locations: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Locations not found",
            )
    else:
        try:
            locations_db, count_locations = await get_locations_v2_service(
                skip=0, limit=100, game_id=game_id
            )

            for location in locations_db:
                location["_id"] = str(location["_id"])

            return SchemaListLocation(results=locations_db, count=count_locations)

        except Exception as e:
            print(f"Error in get locations: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Locations not found",
            )


@router.get("/{location_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveLocation)
async def get_location(
        location_id: str,
        publish: bool = False,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a location.

    It expects the location's id in the request path.
    If the location is successfully retrieved, it returns the location's information.
    """

    try:

        location_db = await get_location_service(
            location_id=location_id, user_id=str(user_db['_id'])
        )
        print(location_db)
        return location_db

    except Exception as e:
        print(f"Error in get location: {traceback.print_exc()}")
        print(f"Error in get location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location not found",
        )


@router.get("/me/", status_code=status.HTTP_200_OK, response_model=SchemaListLocation)
async def get_locations_all(
        user_db: dict = Depends(auth),
        page: int = 1,
        count: int = 10,
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all locations.

    It returns a list of locations.
    """

    try:
        locations_db, count_locations = await get_all_location_service(
            skip=page, limit=count, user_id=str(user_db['_id'])
        )

        for location in locations_db:
            location["_id"] = str(location["_id"])

        return SchemaListLocation(results=locations_db, count=count_locations)

    except Exception as e:
        print(f"Error in get locations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Locations not found",
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveLocation)
async def create_location(
        request: Request,
        title: Optional[str] = Form(None, example="Forest"),
        prompt_user: Optional[str] = Form(None, example="A dark forest with tall trees"),
        game_id: Optional[str] = Form(None, example="game_id"),
        state_game: Optional[str] = Form(None, example="state_game"),
        file: Optional[UploadFile] = File(None),
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a location.

    It expects the location's information in the request body.
    If the location is successfully created, it returns the location's information.
    """
    await validate_star_user_service(user_id=str(user_db.get("_id")))

    try:
        # Intenta procesar el cuerpo como JSON
        try:
            json_body = await request.json()
            title = json_body.get("title")
            prompt_user = json_body.get("prompt_user")
            game_id = json_body.get("game_id")
            state_game = json_body.get("state_game")
        except Exception:
            # Si no es JSON, los datos se procesan como form-data
            pass

        location_db = await create_location_service(
            location=SchemaCreateLocation(
                title=title,
                prompt_user=prompt_user,
                prompt_user_description=None,
                game_id=game_id,
                state_game=state_game,
                url_image_reference=None
            ),
            user_id=str(user_db['_id']),
            file=file
        )
        return location_db

    except Exception as e:
        print(f"Error in create location: {e}")
        print(traceback.print_exc())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location not created",
        )


@router.patch(
    "/{location_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveLocation
)
async def partial_update_location(
        location_id: str,
        schema: SchemaPartialUpdateLocation,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint partially updates a location.

    It expects the location's id in the request path.
    It expects the location's information in the request body.
    If the location is successfully updated, it returns the location's information.
    """

    try:
        location_db = await partial_update_location_service(
            location_id=location_id, location=schema, user_id=str(user_db['_id'])
        )
        # if location_db["config"]:
        #     for config in location_db["config"]:
        #         if config["user"] == str(user_db['_id']):
        #             location_db["configuration"] = config["config"]
        return location_db

    except Exception as e:
        print(f"Error in partial update location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location not updated",
        )


# @router.get("/generate_image/{location_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveLocation)
# async def generate_image_location(
#     location_id: str,
#     user_db: dict = Depends(auth),
#     Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     """
#     This endpoint generates an image for a location.
#
#     It expects the location's id in the request path.
#     If the location is successfully updated, it returns the location's information.
#     """
#     try:
#         location_db = await generate_image_location_service(
#             location_id=location_id, user_id=str(user_db['_id'])
#         )
#         return location_db
#
#     except Exception as e:
#         print(f"Error in generate image location: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Location not updated",
#         )


@router.post("/disable/{location_id}", status_code=status.HTTP_200_OK)
async def disable_location(
        location_id: str,
        location: SchemaDeactivateLocation,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint disables a location.

    It expects the location's id in the request path.
    If the location is successfully disabled, it returns a success message.
    """
    try:
        location_db = await deactivate_location_service(
            location_id=location_id, state_game=location.state_game, active=location.is_active
        )
        return {"message": location_db}

    except Exception as e:
        print(f"Error in disable location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location not disabled",
        )


@router.post("/interaction-video/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_interaction_video(
        location_id: str = Form(..., description="Location ID"),
        state: str = Form(..., description="State/State Game ID"),
        dialog_number: int = Form(..., description="Dialog number in the interaction"),
        quality: str = Form("medium", description="Video compression quality: low, medium, high"),
        video_file: UploadFile = File(..., description="Video file to upload"),
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint uploads a compressed video for a location interaction dialog asynchronously.

    It expects:
    - location_id: The ID of the location
    - state: The state/state_game ID
    - dialog_number: The dialog number in the interaction
    - quality: Video compression quality (low, medium, high)
    - video_file: The video file to upload

    Returns immediately with a task_id for polling the status.
    The video is processed asynchronously in the background.
    """
    try:
        # Validar que el archivo sea un video
        if video_file.content_type not in ['video/mp4', 'video/quicktime', 'video/avi', 'video/x-msvideo']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se permiten videos (mp4, mov, avi)",
            )

        # Leer el contenido del archivo
        video_bytes = await video_file.read()

        # Enviar a la cola de Celery para procesamiento asíncrono
        task = process_interaction_video_task.delay(
            location_id=location_id,
            state=state,
            dialog_number=dialog_number,
            video_bytes=video_bytes,
            quality=quality
        )

        return {
            "status": "processing",
            "message": "Video is being processed in the background",
            "task_id": task.id,
            "location_id": location_id,
            "state": state,
            "dialog_number": dialog_number
        }

    except HTTPException:
        raise
    except Exception as e:
        print(traceback.print_exc())
        print(f"Error in upload interaction video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error uploading interaction video",
        )


@router.get("/interaction-video/status/{task_id}", status_code=status.HTTP_200_OK)
async def get_video_upload_status(
        task_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves the status of a video upload task.

    It expects:
    - task_id: The Celery task ID returned from the upload endpoint

    Returns the current status of the video processing task.
    Possible statuses: PENDING, STARTED, SUCCESS, FAILURE, RETRY
    """
    try:
        from celery.result import AsyncResult
        from location.tasks import process_interaction_video_task

        # Obtener el resultado de la tarea
        task_result = AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": task_result.status,
        }

        if task_result.state == 'PENDING':
            response["message"] = "Task is waiting to be processed"
            response["progress"] = 0
        elif task_result.state == 'STARTED':
            response["message"] = "Video is being processed"
            response["progress"] = 50
        elif task_result.state == 'SUCCESS':
            response["message"] = "Video processed successfully"
            response["progress"] = 100
            response["result"] = task_result.result
        elif task_result.state == 'FAILURE':
            response["message"] = "Video processing failed"
            response["error"] = str(task_result.info)
            response["progress"] = 0
        elif task_result.state == 'RETRY':
            response["message"] = "Video processing is retrying"
            response["progress"] = 25
        else:
            response["message"] = f"Unknown status: {task_result.state}"

        return response

    except Exception as e:
        print(f"Error getting task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error retrieving task status",
        )


# ============ LOCATION TEXT UPDATE ENDPOINTS ============

def get_location_text_service():
    """Inyección de dependencias para el servicio de actualización de textos de locación"""
    return LocationTextUpdateService()


@router.patch(
    "/{location_id}/state/{state_id}/",
    status_code=status.HTTP_200_OK,
    response_model=SchemaLocationStateDataResponse,
    tags=["Location"]
)
async def update_location_data(
    location_id: str,
    state_id: str,
    request: SchemaUpdateLocationData,
    user: dict = Depends(auth_team),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: LocationTextUpdateService = Depends(get_location_text_service)
):
    """Actualiza datos de una locación (título y/o descripción)"""
    try:
        if not request.title and not request.description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Validation Error", "message": "At least one field is required", "code": "VALIDATION_ERROR"}
            )

        user_id = str(user.get("_id"))
        result = await service.update_location_data(location_id, state_id, request.dict(exclude_unset=True), user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


# ============ LOCATION INTERACTION VIDEO DELETE ENDPOINT ============

@router.delete(
    "/{location_id}/state/{state_id}/interaction-video/{dialog_number}/",
    status_code=status.HTTP_200_OK,
    tags=["Location"]
)
async def delete_interaction_video(
    location_id: str,
    state_id: str,
    dialog_number: int,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """Elimina el video de una interacción de locación"""
    try:
        from location.services_video import delete_interaction_video_service
        result = await delete_interaction_video_service(location_id, state_id, dialog_number)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


# ============ LOCATION IMAGE UPDATE ENDPOINTS ============

def get_location_image_service():
    """Inyección de dependencias para el servicio de imágenes de locaciones"""
    return LocationImageUpdateService()


@router.patch(
    "/{location_id}/state/{state_id}/image/",
    status_code=status.HTTP_200_OK,
    tags=["Location"]
)
async def update_location_image(
    location_id: str,
    state_id: str,
    image: UploadFile = File(..., description="Location image (1920x1080px, max 5MB)"),
    user: dict = Depends(auth_team),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: LocationImageUpdateService = Depends(get_location_image_service)
):
    """Actualiza la imagen de una locación"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_location_image(location_id, state_id, image, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})
