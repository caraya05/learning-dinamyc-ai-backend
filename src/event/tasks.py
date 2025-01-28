from bson import ObjectId
import traceback
from task.services import update_task_service
from utils import upload_image
from openai import BaseModel
from pydantic import Field

from core.database import db
from gpt_ai.utils import openai_generator

from uuid import uuid4


class SchemaPromptImage(BaseModel):
    prompt_user_image: str = Field(..., example="prompt_user_image")


async def generate_image_event(game_id: str, event_id: str, state_game: str, user_id: str, prompt_user_image: str):
    try:
        event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
        if not event_db:
            print("Error event not found")
            return False

        game_db = await db["game"].find_one({"_id": ObjectId(game_id)})
        if not game_db:
            print("Error game not found")
            return False, "Game not found"

        state_game_db = await db["state_game"].find_one({"_id": ObjectId(state_game)})
        if not state_game_db:
            print("Error state game not found")
            return False, "State game not found"

        character_principal_state_game = await db["state_glic"].find_one({"element_id": game_db["character_principal"]})
        if not character_principal_state_game:
            print("Error character principal not found")
            return False, "Character principal not found"

        characters_state_game = await db["state_glic"].find(
            {"data.game_id": game_id, "state": state_game}).to_list(None)
        if not characters_state_game:
            print("Error characters not found")
            return False, "Characters not found"

        locations_state_game = await db["state_glic"].find(
            {"data.game_id": game_id, "state": state_game}).to_list(None)
        if not locations_state_game:
            print("Error locations not found")
            return False, "Locations not found"

        # state_game_element = await db["state_glic"].find_one({"element_id": event_db["character_id"]})
        # if not state_game_element:
        #     print("Error state game element not found")
        #     return False

        validate_prompt = await openai_generator.moderation_text(
            text=f"Eres un diseñador de videojuegos y te han encargado crear una imagen de portada en estilo de "
                 f"animación 3D de calidad extraordinaria para el juego {game_db['title']}"
                 f" con el personaje {character_principal_state_game['data']['prompt_user']}. La escena debe representar un momento lleno de acción"
                 f" que capture la esencia del juego."
                 f"Usa la info que tienes de los personajes y locaciones para crear un prompt para crear la imagen."
                 f" {prompt_user_image}"
                 f"Game: {game_db['title']}\n"
                 f"Character Principal: {character_principal_state_game['data']['prompt_user']}\n"
                 f"Characters: {characters_state_game}\n"
                 f"Locations: {locations_state_game}\n"
            ,
        )

        if validate_prompt:
            print("Error validate prompt")
            return False, "Prompt no allowed"

        response_prompt_image = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f"Eres un diseñador de videojuegos y te han encargado crear una imagen de portada en estilo de "
                               f"animación 3D de calidad extraordinaria para el juego {game_db['title']}"
                               f" con el personaje {character_principal_state_game['data']['prompt_user']}. La escena debe representar un momento lleno de acción"
                               f" que capture la esencia del juego."
                               f"Usa la info que tienes de los personajes y locaciones para crear un prompt para crear la imagen."
                },
                {
                    "role": "assistant",
                    "content": f"Game: {game_db['title']}\n"
                               f"Character Principal: {character_principal_state_game['data']['prompt_user']}\n"
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

        validate_prompt = await openai_generator.moderation_text(
            text=response_prompt_image.prompt_user_image,
        )

        if validate_prompt:
            return False, "Prompt no allowed"

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

        # event_db["image"] = image_generated

        await db["event"].update_one({"_id": ObjectId(event_id)}, {"$set": {"image": image_generated}})

        return True, "Image event generated successfully"
    except Exception as e:
        print("Error in generate image event", e)
        print(traceback.format_exc())
        return False, "Error in generate image event"


async def async_generate_image_event(_game_id: str, _event_id: str, _state_game: str, _user_id: str,
                                     _prompt_user_image: str, _task_id: str):
    await update_task_service(_id=_task_id, _status="pending")

    response_image_event, message = await generate_image_event(
        game_id=_game_id,
        event_id=_event_id,
        state_game=_state_game,
        user_id=_user_id,
        prompt_user_image=_prompt_user_image,
    )

    if not response_image_event:
        await update_task_service(_id=_task_id,
                                  _status="failed",
                                  _message=message,
                                  _status_updated=1,
                                  )
        return message
    print("paso", response_image_event)
    await update_task_service(_id=_task_id,
                              _status="completed",
                              _message="Image event generated successfully")
    return "Image event generated successfully"
