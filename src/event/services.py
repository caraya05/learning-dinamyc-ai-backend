from datetime import datetime
from http.client import responses
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status
from openai import BaseModel
from pydantic import Field

from core.database import db
from gpt_ai.utils import openai_generator

from event.models import Event

from event.schemas import SchemaCreateEvent
from event.schemas import SchemaRetrieveEvent
from event.schemas import SchemaUpdateEvent
from utils import upload_image


async def create_event_service(event: SchemaCreateEvent, user_id: str):
    event_schema = Event(
        name=event.name,
        prompt_user_image=event.prompt_user_image,
        prompt_user_text=event.prompt_user_text,
        conversation_type=event.conversation_type,
        option_number=event.option_number,
        character_principal="",
        state_game_init=event.state_game_init,
        state_game_end=None,
        location_state_game_init=event.location_state_game_init,
        location_state_game_end=None,
        text_image=None,
        image=None,
        game_id=event.game_id,
        created_by=user_id,
        updated_by=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    event_created = await db["event"].insert_one(event_schema.dict())

    generate_image = await generate_image_event(
        game_id=event.game_id,
        event_id=str(event_created.inserted_id),
        state_game=event.state_game_init,
        user_id=user_id,
        prompt_user_image=event.prompt_user_image,
    )

    if not generate_image:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error generating image")

    return event_created


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

    if event_db["prompt_user_image"] != event.prompt_user_image:
        generate_image = await generate_image_event(
            game_id=event_db["game_id"],
            event_id=event_id,
            state_game=event_db["state_game_init"],
            user_id=user_id,
            prompt_user_image=event.prompt_user_image,
        )

        if not generate_image:
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error generating image")

    event_db["name"] = event.name
    event_db["prompt_user_image"] = event.prompt_user_image
    event_db["prompt_user_text"] = event.prompt_user_text
    event_db["conversation_type"] = event.conversation_type
    event_db["option_number"] = event.option_number
    event_db["state_game_init"] = event.state_game_init
    event_db["state_game_end"] = event.state_game_end
    event_db["location_state_game_init"] = event.location_state_game_init
    event_db["location_state_game_end"] = event.location_state_game_end
    event_db["image"] = generate_image
    event_db["updated_by"] = user_id
    event_db["updated_at"] = datetime.utcnow()

    event_db = await db["event"].update_one({"_id": ObjectId(event_id)}, {"$set": event_db})

    return event_db

class SchemaPromptImage(BaseModel):
    prompt_user_image: str = Field(..., example="prompt_user_image")


async def generate_image_event(game_id: str, event_id: str, state_game: str, user_id: str, prompt_user_image: str):
    event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
    if not event_db:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    game_db = await db["game"].find_one({"_id": ObjectId(game_id)})
    if not game_db:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    state_game_db = await db["state_game"].find_one({"_id": ObjectId(state_game)})
    if not state_game_db:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State Game not found")

    character_principal_state_game = await db["state_glic"].find_one({"element_id": game_db["character_principal"]})
    if not character_principal_state_game:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character Principal not found")

    characters_state_game = await db["state_glic"].find(
        {"data.game_id": game_id, "data.state_game": state_game}).to_list(None)

    if not characters_state_game:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Characters not found")

    locations_state_game = await db["state_glic"].find(
        {"data.game_id": game_id, "data.state_game": state_game}).to_list(None)

    if not locations_state_game:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locations not found")

    response_prompt_image = await openai_generator.generate_gpt(
        content_prompt=[
            {
                "role": "system",
                "content": f"Eres un diseñador de videojuegos y te han encargado crear una imagen de portada en estilo de "
                           f"animación 3D de calidad extraordinaria para el juego {game_db['title']}"
                           f" con el personaje {character_principal_state_game['prompt_user']}. La escena debe representar un momento lleno de acción"
                           f" que capture la esencia del juego."
                           f"Usa la info que tienes de los personajes y locaciones para crear un prompt para crear la imagen."
            },
            {
                "role": "assistant",
                "content": f"Game: {game_db['title']}\n"
                           f"Character Principal: {character_principal_state_game['prompt_user']}\n"
                           f"Characters: {characters_state_game}\n"
                           f"Locations: {locations_state_game}\n"
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt_user_image}]
            }
        ],
        model="gpt-4o-mini-2024-07-18",
        max_tokens=4096,
        response_format=SchemaPromptImage,
        type_generation="create_prompt_image",
        user_id=user_id,
    )

    response_image = await openai_generator.generate_image(
        prompt=response_prompt_image.prompt_user_image,
        quality="hd",
        size="1024x1792",
        user_id=user_id,
        type_generation="generate image cover game",
    )

    image_generated = upload_image(
        url_image=response_image,
        file_name=f"event/{uuid4()}.jpg",
        size=(512, 896),
    )

    event_db["image"] = image_generated

    await db["event"].update_one({"_id": ObjectId(event_id)}, {"$set": event_db})

    return True



