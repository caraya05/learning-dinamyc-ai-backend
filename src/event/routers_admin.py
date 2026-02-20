from fastapi import APIRouter
from fastapi import Depends
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from event.schemas import SchemaRetrieveEvent
from event.schemas import SchemaCreateEventAdmin
from event.schemas import SchemaUpdateEventAdmin

from event.services_admin import create_event_service_admin
from event.services_admin import get_event_service_admin
from event.services_admin import get_events_service_admin
from event.services_admin import update_event_service_admin

router = APIRouter(prefix='/event', tags=['event'])


@router.post("/", response_model=SchemaRetrieveEvent, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: SchemaCreateEventAdmin,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    return await create_event_service_admin(event=event, user_id=str(user_db.get('_id')))


@router.get("/{event_id}", response_model=SchemaRetrieveEvent)
async def get_event(
    event_id: str,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    return await get_event_service_admin(event_id=event_id)


@router.get("/", response_model=list[SchemaRetrieveEvent])
async def get_events(
    game_id: str = None,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    return await get_events_service_admin(game_id=game_id)


@router.patch("/{event_id}", response_model=SchemaRetrieveEvent)
async def update_event(
    event_id: str,
    event: SchemaUpdateEventAdmin,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    print(f"event_id: {event_id}")
    print(f"event: {event}")
    return await update_event_service_admin(
        event_id=event_id, event=event, user_id=str(user_db.get('_id'))
    )
