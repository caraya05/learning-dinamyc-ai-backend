import time
from io import BytesIO

from bson import ObjectId
import traceback
import base64
import os
import requests

from state_game.services import get_state_game_by_game_id
from task.services import update_task_service
from utils import upload_image, upload_file
from openai import BaseModel
from pydantic import Field

from core.database import db
from gpt_ai.utils import openai_generator

from uuid import uuid4

from voice.elevenlabs import generate_audio


class SchemaPromptImage(BaseModel):
    prompt_user_image: str = Field(..., example="prompt_user_image")


async def generate_image_event(
        game_id: str, event_id: str, state_game: str, user_id: str, prompt_user_image: str
):
    if os.environ.get("MODE_TEST", False):
        # En modo test, no generar imagen, solo asignar la imagen estática
        url_image = "https://storage.googleapis.com/qwestar/voxel_.jpg"
        event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
        if not event_db:
            print("Error event not found")
            return False
        event_db["image"] = url_image
        await db["event"].update_one({"_id": event_db["_id"]}, {"$set": {"image": url_image}})
        return True, "Image set to static test image"

    try:
        event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
        if not event_db:
            print("Error event not found")
            return False

        game_db = await db["game"].find_one({"_id": ObjectId(game_id)})
        if not game_db:
            print("Error game not found")
            return False, "Game not found"

        if not state_game:
            state_game_db = await get_state_game_by_game_id(game_id)
            if not state_game_db:
                print("Error state game not found")
                return False, "State game not found"
            state_game = state_game_db["_id"]

        state_game_db = await db["state_game"].find_one({"_id": ObjectId(state_game)})
        if not state_game_db:
            print("Error state game not found")
            return False, "State game not found"

        character_principal_state_game = await db["state_glic"].find_one(
            {"element_id": game_db["character_principal"]}
        )
        if not character_principal_state_game:
            print("Error character principal not found")
            return False, "Character principal not found"

        characters_state_game = (
            await db["state_glic"]
            .find({"data.game_id": game_id, "state": state_game})
            .to_list(None)
        )
        if not characters_state_game:
            print("Error characters not found")
            return False, "Characters not found"

        locations_state_game = (
            await db["state_glic"]
            .find({"data.game_id": game_id, "state": state_game})
            .to_list(None)
        )
        if not locations_state_game:
            print("Error locations not found")
            return False, "Locations not found"

        # state_game_element = await db["state_glic"].find_one({"element_id": event_db["character_id"]})
        # if not state_game_element:
        #     print("Error state game element not found")
        #     return False

        validate_prompt = await openai_generator.moderation_text(
            text=f"Genera una imagen de portada en estilo 3D low poly de proporciones realistas para el juego  {game_db['title']}"
                 f" con el personaje {character_principal_state_game['data']['prompt_user']}. "
                 f"La imagen debe ser portrait y tener el contenido vertical."
                 f"Usa la info que tienes de los personajes y locaciones para crear un prompt para crear la imagen."
                 f" {prompt_user_image}"
                 f"Game: {game_db['title']}\n"
                 f"Character Principal: {character_principal_state_game['data']['prompt_user']}\n"
                 f"Characters: {characters_state_game}\n"
                 f"Locations: {locations_state_game}\n",
        )

        if validate_prompt:
            print("Error validate prompt")
            return False, "Prompt no allowed"

        # Generar audio del texto del evento
        if event_db.get("prompt_user_text"):
            try:
                audio = await generate_audio(
                    text=event_db["prompt_user_text"],
                    user_id=user_id,
                    voice_id="alFofuDn3cOwyoz1i44T"
                )

                if audio:
                        # Actualizar el evento con la URL del audio
                        await db["event"].update_one(
                            {"_id": ObjectId(event_id)},
                            {"$set": {"audio": audio.get("ogg"),
                                      "audio_mp3": audio.get("mp3")}}
                        )
            except Exception as audio_error:
                print(traceback.format_exc())
                print(f"Error generating audio: {audio_error}")
                # No fallar todo el proceso si falla el audio
                pass

        time.sleep(1000)
        # Construir info de personajes y adjuntar imágenes
        personajes_info = []
        personajes_images = []
        for personaje in characters_state_game:
            data = personaje.get('data', {})
            nombre = data.get('name', 'Personaje')
            prompt_personaje = data.get('prompt_user', '')
            imagen = data.get('image') or data.get('image_reference')
            if imagen:
                personajes_info.append(f"{nombre}: {prompt_personaje} (imagen: {imagen})")
                personajes_images.append(imagen)
            else:
                personajes_info.append(f"{nombre}: {prompt_personaje}")
        personajes_str = '\n'.join(personajes_info)

        # Construir el prompt base y la estructura de content_prompt
        prompt_base = (
            f"Genera una imagen de portada en estilo 3D medium poly de proporciones realistas para el juego {game_db['title']} "
            f"con el personaje principal {character_principal_state_game['data']['prompt_user']}. "
            f"La imagen debe ser portrait y tener el contenido vertical. Sin texto. "
            f"Usa la info de los personajes y locaciones para crear la escena.\n"
            f"Personajes en la escena (usa sus imágenes como referencia):\n{personajes_str}\n"
            f"prompt del usuario: {prompt_user_image}"
        )
        content_prompt = [
            {"role": "user", "content": [
                {"type": "input_text", "text": prompt_base}
            ]}
        ]
        # Adjuntar imágenes de personajes
        for imagen in personajes_images:
            try:
                response = requests.get(imagen)
                image_bytes = BytesIO(response.content)
                image_base64 = base64.b64encode(image_bytes.getvalue()).decode('utf-8')
                content_prompt[0]["content"].append({
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{image_base64}"
                })
            except Exception as e:
                print(f"Error adjuntando imagen de personaje: {imagen}", e)
                continue


        response_prompt_image = await openai_generator.generate_gpt(
            content_prompt=content_prompt,
            model="gpt-4.1",
            type_generation="create_prompt_image",
            tools=[{"type": "image_generation"}],
            image=True,
            user_id=user_id,
        )

        image_bytes = base64.b64decode(response_prompt_image)
        image_face = BytesIO(image_bytes)

        image_generated = upload_image(
            img_byte_arr=image_face,
            file_name=f"event/{uuid4()}.jpg",
            size=(512, 896),
        )


        await db["event"].update_one(
            {"_id": ObjectId(event_id)}, {"$set": {"image": image_generated}}
        )

        return True, "Image event generated successfully"
    except Exception as e:
        print("Error in generate image event", e)
        print(traceback.format_exc())
        return False, "Error in generate image event"


async def async_generate_image_event(
        _game_id: str,
        _event_id: str,
        _state_game: str,
        _user_id: str,
        _prompt_user_image: str,
        _task_id: str,
):
    if _task_id:
        await update_task_service(_id=_task_id, _status="pending")

    response_image_event, message = await generate_image_event(
        game_id=_game_id,
        event_id=_event_id,
        state_game=_state_game,
        user_id=_user_id,
        prompt_user_image=_prompt_user_image,
    )

    if not response_image_event:
        if _task_id:
            await update_task_service(
                _id=_task_id,
                _status="failed",
                _message=message,
                _status_updated=1,
            )
        return message
    if _task_id:
        await update_task_service(
            _id=_task_id, _status="completed", _message="Image event generated successfully"
        )
    return "Image event generated successfully"
