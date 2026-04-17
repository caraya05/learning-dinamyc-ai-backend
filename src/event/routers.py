from fastapi import APIRouter
from fastapi import Depends
from fastapi import status
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import File, UploadFile, Form
import traceback

from auth.auth import auth, auth_team
from auth.utils import auth_schema

from event.schemas import SchemaRetrieveEvent
from event.schemas import SchemaCreateEvent
from event.schemas import SchemaUpdateEvent

from event.services import create_event_service
from event.services import get_event_service
from event.services import get_events_service
from event.services import update_event_service
from event.services_video import (
    save_event_video_service,
    get_event_video_service,
    delete_event_video_service,
)

from event.text_update_services import EventTextUpdateService
from game.text_update_schemas import (
    SchemaUpdateEvent as SchemaUpdateEventText,
    SchemaEventResponse,
)

from event.image_update_services import EventImageUpdateService
from event.audio_update_services import EventAudioUpdateService

router = APIRouter(prefix='/event', tags=['event'])


@router.post("/", response_model=SchemaRetrieveEvent, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: SchemaCreateEvent,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    return await create_event_service(event=event, user_id=str(user_db.get('_id')))


@router.get("/{event_id}", response_model=SchemaRetrieveEvent)
async def get_event(
    event_id: str,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    return await get_event_service(event_id=event_id)


@router.get("/", response_model=list[SchemaRetrieveEvent])
async def get_events(
    game_id: str = None,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    return await get_events_service(game_id=game_id)


@router.patch("/{event_id}", response_model=SchemaRetrieveEvent)
async def update_event(
    event_id: str,
    event: SchemaUpdateEvent,
    user_db: dict = Depends(auth_team),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    return await update_event_service(
        event_id=event_id, event=event, user_id=str(user_db.get('_id'))
    )


@router.post("/{event_id}/video/upload", status_code=status.HTTP_201_CREATED)
async def upload_event_video(
        event_id: str,
        quality: str = Form("medium", description="Video compression quality: low, medium, high"),
        video_file: UploadFile = File(..., description="Video file to upload"),
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint uploads a video for an event.

    It expects:
    - event_id: The ID of the event (in URL path)
    - quality: Video compression quality (low, medium, high)
    - video_file: The video file to upload

    Returns the uploaded video information and URL.
    """
    try:
        result = await save_event_video_service(
            event_id=event_id,
            video_file=video_file,
            quality=quality
        )
        return result

    except Exception as e:
        print(traceback.print_exc())
        print(f"Error in upload event video: {str(e)}")
        raise


@router.get("/{event_id}/video", status_code=status.HTTP_200_OK)
async def get_event_video(
        event_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves the video information of an event.

    It expects the event's id in the request path.
    Returns the video URL and metadata.
    """
    try:
        result = await get_event_video_service(event_id=event_id)
        return result

    except Exception as e:
        print(f"Error in get event video: {str(e)}")
        raise


@router.delete("/{event_id}/video", status_code=status.HTTP_200_OK)
async def delete_event_video(
        event_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint deletes the video from an event.

    It expects the event's id in the request path.
    Returns a success message.
    """
    try:
        result = await delete_event_video_service(event_id=event_id)
        return result

    except Exception as e:
        print(f"Error in delete event video: {str(e)}")
        raise


# ============ EVENT TEXT UPDATE ENDPOINTS ============

def get_event_text_service():
    """Inyección de dependencias para el servicio de actualización de textos de evento"""
    return EventTextUpdateService()


@router.patch(
    "/{event_id}/text/",
    status_code=status.HTTP_200_OK,
    response_model=SchemaEventResponse,
    tags=["event"]
)
async def update_event_text(
    event_id: str,
    request: SchemaUpdateEventText,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: EventTextUpdateService = Depends(get_event_text_service)
):
    """Actualiza datos de un evento (text_image, description, prompt_user_text)"""
    try:
        if not request.text_image and not request.description and not request.prompt_user_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Validation Error", "message": "At least one field is required", "code": "VALIDATION_ERROR"}
            )

        user_id = str(user.get("_id"))
        result = await service.update_event(event_id, request.dict(exclude_unset=True), user_id)
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


# ============ EVENT IMAGE UPDATE ENDPOINTS ============

def get_event_image_service():
    """Inyección de dependencias para el servicio de imágenes de eventos"""
    return EventImageUpdateService()


@router.patch(
    "/{event_id}/description-image/",
    status_code=status.HTTP_200_OK,
    tags=["event"]
)
async def update_event_description_image(
    event_id: str,
    image: UploadFile = File(..., description="Description image (1024x576px, max 3MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: EventImageUpdateService = Depends(get_event_image_service)
):
    """Actualiza la imagen de descripción de un evento"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_event_description_image(event_id, image, user_id)
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


@router.patch(
    "/{event_id}/image/",
    status_code=status.HTTP_200_OK,
    tags=["event"]
)
async def update_event_image(
    event_id: str,
    image: UploadFile = File(..., description="Event main image (1920x1080px, max 5MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: EventImageUpdateService = Depends(get_event_image_service)
):
    """Actualiza la imagen principal de un evento"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_event_image(event_id, image, user_id)
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


# ============ EVENT AUDIO UPDATE ENDPOINTS ============

def get_event_audio_service():
    """Inyección de dependencias para el servicio de audios de eventos"""
    return EventAudioUpdateService()


@router.patch(
    "/{event_id}/audio/",
    status_code=status.HTTP_200_OK,
    tags=["event"]
)
async def update_event_audio(
    event_id: str,
    audio: UploadFile = File(..., description="Event audio (MP3/WAV/OGG/M4A, max 15MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: EventAudioUpdateService = Depends(get_event_audio_service)
):
    """Actualiza el audio de un evento"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_event_audio(event_id, audio, user_id)
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
