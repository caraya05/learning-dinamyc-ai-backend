from fastapi import APIRouter
from fastapi import Depends
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import File, UploadFile, Form
import traceback

from auth.auth import auth
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
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    return await update_event_service(
        event_id=event_id, event=event, user_id=str(user_db.get('_id'))
    )


@router.post("/{event_id}/video/upload/", status_code=status.HTTP_201_CREATED)
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

