from datetime import datetime
import traceback
from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core.database import db

from event.models import Event

from event.schemas import SchemaCreateEvent
from event.schemas import SchemaUpdateEvent
from task.services import create_task_service, update_task_service

from celery_worker import generate_image_event_task


async def create_event_service(event: SchemaCreateEvent, user_id: str):
    event_schema = Event(
        name=event.name,
        prompt_user_image=event.prompt_user_image,
        prompt_user_text=event.prompt_user_text,
        type_conversation=None,
        option_number=None,
        character_id=None,
        character_principal="",
        state_game_init=event.state_game_init,
        state_game_end=None,
        location_state_game_init=event.location_state_game_init,
        location_state_game_end=None,
        text_image=event.prompt_user_text,
        image=None,
        game_id=event.game_id,
        created_by=user_id,
        updated_by=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    event_created = await db["event"].insert_one(event_schema.dict())

    task_db = await create_task_service(
        _task_id="",
        _user_id=user_id,
        _task_data={},
        _element_id=str(event_created.inserted_id),
        _element_type="event",
        _process="generate_event_image",
    )

    task_celery = generate_image_event_task.delay(
        game_id=event.game_id,
        event_id=str(event_created.inserted_id),
        state_game=event.state_game_init,
        user_id=user_id,
        prompt_user_image=event.prompt_user_image,
        task_id=str(task_db["_id"]),
    )

    await update_task_service(
        _id=str(task_db["_id"]),
        _task_id=task_celery.id,
    )

    event_db = await db["event"].find_one({"_id": event_created.inserted_id})
    event_db["_id"] = str(event_db["_id"])
    event_db["task_id"] = str(task_db["_id"])
    return event_db


async def get_event_service(event_id: str):
    event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
    if not event_db:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    return event_db


async def get_events_service(game_id: str):
    if game_id:
        events_db = await db["event"].find({"game_id": game_id}).to_list(None)
        return events_db
    events_db = await db["event"].find().to_list(None)
    return events_db


async def update_event_service(event_id: str, event: SchemaUpdateEvent, user_id: str):
    event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
    if not event_db:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    generate_image = event_db["image"]
    brand = False
    if event_db["prompt_user_image"] != event.prompt_user_image:
        brand = True



    event_db["name"] = event.name
    event_db["prompt_user_image"] = event.prompt_user_image
    event_db["prompt_user_text"] = event.prompt_user_text
    event_db["type_conversation"] = event.type_conversation
    event_db["option_number"] = event.option_number
    event_db["state_game_init"] = event.state_game_init
    event_db["state_game_end"] = event.state_game_end
    event_db["location_state_game_init"] = event.location_state_game_init
    event_db["location_state_game_end"] = event.location_state_game_end
    event_db["image"] = generate_image
    event_db["updated_by"] = user_id
    event_db["updated_at"] = datetime.utcnow()

    await db["event"].update_one({"_id": ObjectId(event_id)}, {"$set": event_db})
    event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
    event_db["_id"] = str(event_db["_id"])

    if brand:
        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=event_id,
            _element_type="event",
            _process="generate_event_image",
        )

        task_celery = generate_image_event_task.delay(
            game_id=event_db["game_id"],
            event_id=event_id,
            state_game=event_db["state_game_init"],
            user_id=user_id,
            prompt_user_image=event_db["prompt_user_image"],
            task_id=str(task_db["_id"]),
        )

        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )

        event_db["task_id"] = str(task_db["_id"])

    return event_db
