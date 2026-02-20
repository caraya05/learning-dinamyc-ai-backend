from datetime import datetime
import traceback
from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core.database import db

from event.models import Event

from event.schemas import SchemaCreateEventAdmin
from event.schemas import SchemaUpdateEventAdmin

from gpt_ai.utils import openai_generator


async def create_event_service_admin(event: SchemaCreateEventAdmin, user_id: str):
    moderation_user_text = await openai_generator.moderation_text(
        text=event.prompt_user_text,
        user_id=user_id,
    )
    if moderation_user_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The text is not allowed"
        )

    moderation_user_image = await openai_generator.moderation_text(
        text=event.prompt_user_image,
        user_id=user_id,
    )
    if moderation_user_image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The image is not allowed"
        )

    event_schema = Event(
        name=event.name,
        prompt_user_image=event.prompt_user_image,
        prompt_user_text=event.prompt_user_text,
        type_conversation=event.type_conversation,
        option_number=event.option_number,
        character_id=event.character_id,
        character_principal="",
        state_game_init=event.state_game_init,
        state_game_end=event.state_game_end,
        location_state_game_init=event.location_state_game_init,
        location_state_game_end=event.location_state_game_end,
        text_image=event.prompt_user_text,
        image=event.image,
        game_id=event.game_id,
        created_by=user_id,
        updated_by=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    event_created = await db["event"].insert_one(event_schema.dict())

    event_db = await db["event"].find_one({"_id": event_created.inserted_id})
    event_db["_id"] = str(event_db["_id"])
    return event_db


async def get_event_service_admin(event_id: str):
    event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
    if not event_db:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event_db


async def get_events_service_admin(game_id: str):
    if game_id:
        events_db = await db["event"].find({"game_id": game_id}).sort("created_at", -1).to_list(None)
        return events_db
    events_db = await db["event"].find().sort("created_at", -1).to_list(None)
    return events_db


async def update_event_service_admin(event_id: str, event: SchemaUpdateEventAdmin, user_id: str):
    try:
        event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
        if not event_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        update_data = {"updated_at": datetime.utcnow()}

        fields_to_update = [
            "prompt_user_text", "prompt_user_image", "type_conversation",
            "option_number", "state_game_end", "location_state_game_end",
            "character_id", "image"
        ]

        for field in fields_to_update:
            if getattr(event, field):
                update_data[field] = getattr(event, field)

        await db["event"].update_one({"_id": ObjectId(event_id)}, {"$set": update_data})
        event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
        event_db["_id"] = str(event_db["_id"])

        return event_db
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in update event service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not updated",
        )
