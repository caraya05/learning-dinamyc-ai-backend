import asyncio
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

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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
            .find({"data.game_id": game_id, "state": state_game, "type_element": "character"})
            .to_list(None)
        )
        if not characters_state_game:
            print("Error characters not found")
            return False, "Characters not found"
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
        )

        if validate_prompt:
            print("Error validate prompt")
            return False, "Prompt no allowed"

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


async def _generate_image_event(_user_id, _prompt_user_image, _id_event, _game_provisional, is_init=False, _url_image_reference=None):
    try:
        game_db = await db["game_provisional"].find_one({"_id": ObjectId(_game_provisional)})
        characters = game_db.get("characters", [])

        # Si is_init es True, esperar a que los dos primeros personajes tengan imagen
        if is_init:
            while True:
                game_db = await db["game_provisional"].find_one({"_id": ObjectId(_game_provisional)})
                events = game_db.get("events", [])
                event = next((e for e in events if e.get("id") == _id_event), None)
                if not event:
                    await asyncio.sleep(1)
                    continue

                character_ids = event.get("id_characters", [])
                characters = game_db.get("characters", [])
                personajes_evento = [p for p in characters if p.get("id") in character_ids]

                images_ready = all(personaje.get("image") for personaje in personajes_evento)
                if images_ready:
                    break
                await asyncio.sleep(1)

        personajes_info = []
        personajes_images = []
        for personaje in characters[:2]:
            data = personaje.get('data', {})
            nombre = data.get('name', 'Personaje')
            prompt_personaje = data.get('visual_description', '')
            imagen = personaje.get('image')
            if imagen:
                personajes_info.append(f"{nombre}: {prompt_personaje}")
                personajes_images.append(imagen)
            else:
                personajes_info.append(f"{nombre}: {prompt_personaje}")
        personajes_str = '\n'.join(personajes_info)

        prompt_reference = ""
        if _url_image_reference:
            prompt_reference = f"\nUsa la siguiente imagen de referencia para mantener coherencia visual y estilo de la escena."

        prompt_base = (
            f"Genera una imagen de portada en estilo 3D medium poly  "
            f"La imagen debe ser portrait y tener el contenido vertical. Sin texto. "
            f"Usa la info de los personajes para crear la escena.\n"
            f"Personajes en la escena (usa sus imágenes como referencia):\n{personajes_str}\n"
            f"descripcion de la escena: {_prompt_user_image}"
            f"{prompt_reference}"
        )
        content_prompt = [
            {"role": "user", "content": [
                {"type": "input_text", "text": prompt_base}
            ]}
        ]
        # Agregar imagen de referencia del evento si está disponible
        if _url_image_reference:
            try:
                response = requests.get(_url_image_reference)
                image_bytes = BytesIO(response.content)
                image_base64 = base64.b64encode(image_bytes.getvalue()).decode('utf-8')
                content_prompt[0]["content"].append({
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{image_base64}"
                })
            except Exception as e:
                print(f"Error adjuntando imagen de referencia del evento: {_url_image_reference}", e)

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

        # Si existe referencia de imagen, usar generate_image(), sino usar generate_gpt()
        response_prompt_image = None
        if _url_image_reference:
            # Usar generate_image con la referencia en el prompt
            simple_prompt = (
                f"Genera una imagen de portada en estilo 3D medium poly. "
                f"La imagen debe ser portrait y tener el contenido vertical. Sin texto. "
                f"Personajes en la escena: {personajes_str}. "
                f"Descripción de la escena: {_prompt_user_image}. "
                f"Basándote en el estilo visual de esta referencia ({_url_image_reference}), "
                f"mantén coherencia visual y estilo con esa imagen de referencia."
            )
            try:
                response_prompt_image = await openai_generator.generate_image(
                    prompt=simple_prompt,
                    size="1024x1536",
                    user_id=_user_id,
                    model="gpt-image-1",
                    style=None,
                    type_generation="event_image"
                )
            except Exception as e:
                logger.warning(f"Error generando imagen con referencia: {str(e)}, usando fallback generate_gpt")
                response_prompt_image = None

        # Si no hay respuesta, usar método original con generate_gpt como fallback
        if not response_prompt_image:
            response_prompt_image = await openai_generator.generate_gpt(
                content_prompt=content_prompt,
                model="gpt-4.1",
                type_generation="create_prompt_image",
                tools=[{"type": "image_generation", "size": "1024x1536"}],
                image=True,
                user_id=_user_id,
            )

        if not response_prompt_image:
            logger.error("La respuesta de la generación de imagen es None")
            return "Error: No se pudo generar la imagen del evento"

        image_bytes = base64.b64decode(response_prompt_image)
        image_face = BytesIO(image_bytes)

        image_generated = upload_image(
            img_byte_arr=image_face,
            file_name=f"event/{uuid4()}.jpg",
            size=(512, 896),
        )

        events = game_db.get("events", [])
        index_found = next((i for i, e in enumerate(events) if e.get("id") == _id_event), None)
        if index_found is None:
            return "Failure: Event not found in game provisional"

        await db["game_provisional"].update_one(
            {"_id": ObjectId(_game_provisional)},
            {f"$set": {f"events.{index_found}.image": image_generated}}
        )

        return "Image event generated successfully"
    except Exception as e:
        logger.error(f"Error in get images event service: {traceback.format_exc()}")
        return "Error in generate image event"

async def async_generate_event_audio(event_id: str, user_id: str, text: str = None):
    """
    Genera audio para un evento específico
    """
    try:
        event_db = await db["event"].find_one({"_id": ObjectId(event_id)})
        if not event_db:
            print(f"Event not found: {event_id}")
            return "Event not found"

        # Usar el texto proporcionado o el texto del evento
        audio_text = text or event_db.get("prompt_user_text")

        if not audio_text:
            print(f"No text available for audio generation for event: {event_id}")
            return "No text available for audio generation"

        try:
            audio = await generate_audio(
                text=audio_text,
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
                print(f"Audio generated successfully for event: {event_id}")
                return "Audio generated successfully"
            else:
                print(f"Failed to generate audio for event: {event_id}")
                return "Failed to generate audio"

        except Exception as audio_error:
            print(f"Error generating audio for event {event_id}: {audio_error}")
            print(traceback.format_exc())
            return f"Error generating audio: {str(audio_error)}"

    except Exception as e:
        print(f"Error in async_generate_event_audio: {e}")
        print(traceback.format_exc())
        return f"Error in audio generation: {str(e)}"


