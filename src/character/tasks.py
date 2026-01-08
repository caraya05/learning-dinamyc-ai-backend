import random
import traceback
import requests
import base64
import os
import logging

from uuid import uuid4

from bson import ObjectId

from pydantic import BaseModel
from pydantic import Field

from core.database import db

from gpt_ai.utils import openai_generator

from task.services import update_task_service
from utils import upload_image
from voice.elevenlabs import generate_audio
from voice.utils import get_variants_service

from io import BytesIO

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SchemaVoiceIdentification(BaseModel):
    age: str = Field(..., description="Age of the voice according to the description")
    genre: str = Field(..., description="Genre of the voice according to the description")
    accent: str = Field(..., description="Accent of the voice according to the description")


async def generate_voice_character(
        game_id,
        character_id: str,
        user_id: str,
        location_id: str,
        state_game: str,
        type_conversation: str,
        prompt_user_dialog: str = None,
        options_dialog: dict = None,
):
    try:
        voice = {}
        character_state_db = await db["state_glic"].find_one(
            {"element_id": character_id, "state": state_game}
        )
        if not character_state_db["data"].get("voice_id"):
            variants_voices = await get_variants_service()
            response_generated = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": "Utilizando la siguiente descripción, identificar la voz que mejor se ajuste a la descripción. "
                                   f"Respondiendo con la edad y género de la voz,",
                    },
                    {
                        "role": "assistant",
                        "content": f"Variantes de voces a identificar: {variants_voices}",
                    },
                    {
                        "role": "user",
                        "content": f"Descripción del personaje: {character_state_db['data']['description']}"
                                   f"Genero del personaje: {character_state_db['data']['genre']}",
                    },
                ],
                response_format=SchemaVoiceIdentification,
                type_generation="Voice Identification",
                max_tokens=2000,
                model="gpt-4o-mini",
                user_id=user_id,
            )

            # Filtra por género
            voice_by_gender = await db["voice"].find({"gender": response_generated.genre}).to_list(None)
            # Filtra por edad dentro del género
            voice_by_age = [voice for voice in voice_by_gender if voice["age"] == response_generated.age]
            # Filtra por acento dentro de género y edad
            voice_by_accent = [voice for voice in voice_by_age if voice["accent"] == "North American"]

            if voice_by_accent:
                voice = voice_by_accent[0]
            elif voice_by_age:
                voice = voice_by_age[0]
            else:
                # Buscar por género y acento
                voice_by_gender_accent = [voice for voice in voice_by_gender if voice["accent"] == "North American"]
                if voice_by_gender_accent:
                    voice = voice_by_gender_accent[0]
                elif voice_by_gender:
                    voice = voice_by_gender[0]
                else:
                    # Si no hay nada, elige cualquiera
                    voice = await db["voice"].find_one()
            await db["character"].update_one(
                {"_id": ObjectId(character_id)}, {"$set": {"voice_id": str(voice["voice_id"])}}
            )
        else:
            voice["voice_id"] = character_state_db["data"].get("voice_id")
        character_state_db["data"]["voice_id"] = str(voice["voice_id"])
        character_state_db["data"]["prompt_user_dialog"] = prompt_user_dialog
        character_state_db["data"]["conversation_type"] = type_conversation
        character_state_db["data"]["options"] = options_dialog["options"] if options_dialog and options_dialog.get(
            "options") else None
        character_state_db["data"]["prompt_user_question"] = options_dialog[
            "prompt_user_question"] if options_dialog and options_dialog.get("prompt_user_question") else None
        character_state_db["data"]["options_dialog"] = options_dialog
        if character_state_db["data"].get("locations_id"):
            locations_array = character_state_db["data"]["locations_id"]
            if location_id not in locations_array:
                locations_array.append(location_id)
            character_state_db["data"]["locations_id"] = locations_array
        else:
            character_state_db["data"]["locations_id"] = [location_id]
        await db["state_glic"].update_one(
            {"_id": character_state_db["_id"]},
            {
                "$set": {
                    "data": character_state_db["data"],
                }
            },
        )

        match type_conversation:
            case "one_way":
                await generate_monologue_character(
                    _game_id=game_id,
                    _character_id=character_id,
                    _user_id=user_id,
                    _location_id=location_id,
                    _state_game_id=state_game,
                )
            case "two_way":
                await generate_conversation_character(
                    _game_id=game_id,
                    _character_id=character_id,
                    _user_id=user_id,
                    _location_id=location_id,
                    _state_game_id=state_game,
                )
            case "option_multiple":
                await generate_option_character(
                    _game_id=game_id,
                    _character_id=character_id,
                    _user_id=user_id,
                    _location_id=location_id,
                    _state_game_id=state_game,
                )

            case "open_question":
                print("Generating open question character voice...")
                await generate_open_question_character(
                    _game_id=game_id,
                    _character_id=character_id,
                    _user_id=user_id,
                    _location_id=location_id,
                    _state_game_id=state_game,
                )

            case "open_talk":
                await generate_open_talk_character(
                    _game_id=game_id,
                    _character_id=character_id,
                    _user_id=user_id,
                    _location_id=location_id,
                    _state_game_id=state_game,
                )

        if (
                type_conversation != "none"
                and type_conversation != "option_multiple"
                and type_conversation != "open_question"
                and type_conversation != "open_talk"
        ):
            character_state_db = await db["state_glic"].find_one({"_id": character_state_db["_id"]})
            if character_state_db["data"]["interaction"]:
                for i in range(len(character_state_db["data"]["interaction"])):
                    if (
                            character_state_db["data"]["interaction"][i]["location_id"] == location_id
                            and character_state_db["data"]["interaction"][i]["state_game"] == state_game
                    ):
                        for j in range(
                                len(character_state_db["data"]["interaction"][i]["conversation"])
                        ):
                            character_state_db_ = await db["state_glic"].find_one(
                                {
                                    "element_id": character_state_db["data"]["interaction"][i][
                                        "conversation"
                                    ][j]['id_character'],
                                    "state": state_game,
                                }
                            )

                            try:
                                audio = await generate_audio(
                                    text=character_state_db["data"]["interaction"][i]["conversation"][j]["dialog"],
                                    voice_id=character_state_db_["data"]["voice_id"],
                                    user_id=user_id,
                                )

                                character_state_db["data"]["interaction"][i]["conversation"][j]["audio"] = audio.get("ogg")
                                character_state_db["data"]["interaction"][i]["conversation"][j]["audio_mp3"] = audio.get("mp3")
                            except Exception as e:
                                print(traceback.format_exc())
                                print(f"Error in generate voice service 1: {str(e)}")
                                pass

                await db["state_glic"].update_one(
                    {"_id": character_state_db["_id"]},
                    {
                        "$set": {
                            "data": character_state_db["data"],
                        }
                    },
                )
            return True

        if type_conversation == "option_multiple":

            character_state_db = await db["state_glic"].find_one(
                {"_id": ObjectId(character_state_db["_id"])}
            )
            if character_state_db["data"]["interaction"]:
                for i in range(len(character_state_db["data"]["interaction"])):
                    if (character_state_db["data"]["interaction"][i]["location_id"] == location_id and character_state_db["data"]["interaction"][i]["state_game"] == state_game):
                        for j in range(len(character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"])):
                            character_state_db_ = await db["state_glic"].find_one(
                                {
                                    "element_id": character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][j]['id_character'],
                                    "state": state_game,
                                }
                            )
                            audio = await generate_audio(
                                text=character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][j]["dialog"],
                                voice_id=character_state_db_["data"]["voice_id"],
                                user_id=user_id,
                            )
                            character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][j]["audio"] = audio.get("ogg")
                            character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][j]["audio_mp3"] = audio.get("mp3")

                        for j in range(len(character_state_db["data"]["interaction"][i]["options_dialog"]["options"])):
                            character_state_db_ = await db["state_glic"].find_one(
                                {
                                    "element_id": character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]['prompt_user_option']['id_character'],
                                    "state": state_game,
                                }
                            )
                            audio = await generate_audio(
                                text=character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]["prompt_user_option"]["dialog"],
                                voice_id=character_state_db_["data"]["voice_id"],
                                user_id=user_id,
                            )
                            print("audio generated for option:", audio, type(audio))
                            character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]['prompt_user_option']["audio"] = audio.get("ogg")

                            character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]['prompt_user_option']["audio_mp3"] = audio.get("mp3")

                            audio = await generate_audio(
                                text=character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]["prompt_user_answer"]["dialog"],
                                voice_id=character_state_db["data"]["voice_id"],
                                user_id=user_id,
                            )
                            character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]['prompt_user_answer']["audio"] = audio.get("ogg")

                            character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]['prompt_user_answer']["audio_mp3"] = audio.get("mp3")

                await db["state_glic"].update_one(
                    {"_id": character_state_db["_id"]},
                    {
                        "$set": {
                            "data": character_state_db["data"],
                        }
                    },
                )
            return True
        if type_conversation == "open_question":
            print("DEBUG: interaction found", character_state_db["data"])
            character_state_db = await db["state_glic"].find_one({"_id": ObjectId(character_state_db["_id"])})
            if character_state_db["data"]["interaction"]:
                for i in range(len(character_state_db["data"]["interaction"])):
                    if (character_state_db["data"]["interaction"][i]["location_id"] == location_id and character_state_db["data"]["interaction"][i]["state_game"] == state_game):
                        for j in range(len(character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"])):
                            character_state_db_ = await db["state_glic"].find_one(
                                {
                                    "element_id": character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][j]['id_character'],
                                    "state": state_game,
                                }
                            )
                            audio = await generate_audio(
                                text=character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][j]["dialog"],
                                voice_id=character_state_db_["data"]["voice_id"],
                                user_id=user_id,
                            )
                            character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][j]["audio"] = audio.get("ogg")

                            character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][j]["audio_mp3"] = audio.get("mp3")

                        for j in range(len(character_state_db["data"]["interaction"][i]["options_dialog"]["options"])):
                            character_state_db_ = await db["state_glic"].find_one(
                                {
                                    "element_id": character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]["prompt_user_answer"]['id_character'],
                                    "state": state_game,
                                }
                            )
                            audio = await generate_audio(
                                text=character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]["prompt_user_answer"]["dialog"],
                                voice_id=character_state_db_["data"]["voice_id"],
                                user_id=user_id,
                            )
                            character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]['prompt_user_answer']["audio"] = audio.get("ogg")

                            character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j]['prompt_user_answer']["audio_mp3"] = audio.get("mp3")

                await db["state_glic"].update_one(
                    {"_id": character_state_db["_id"]},
                    {
                        "$set": {
                            "data": character_state_db["data"],
                        }
                    },
                )
        if type_conversation == "open_talk":

            character_state_db = await db["state_glic"].find_one(
                {"_id": ObjectId(character_state_db["_id"])}
            )
            if character_state_db["data"]["interaction"]:
                for i in range(len(character_state_db["data"]["interaction"])):
                    if (
                            character_state_db["data"]["interaction"][i]["location_id"] == location_id
                            and character_state_db["data"]["interaction"][i]["state_game"] == state_game
                    ):
                        for j in range(len(character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"])):
                            character_state_db_ = await db["state_glic"].find_one(
                                {
                                    "element_id": character_state_db["data"]["interaction"][i][
                                        "options_dialog"
                                    ]["prompt_user_question"][j]['id_character'],
                                    "state": state_game,
                                }
                            )
                            audio = await generate_audio(
                                text=character_state_db["data"]["interaction"][i]["options_dialog"][
                                    "prompt_user_question"
                                ][j]["dialog"],
                                voice_id=character_state_db_["data"]["voice_id"],
                                user_id=user_id,
                            )
                            character_state_db["data"]["interaction"][i]["options_dialog"][
                                "prompt_user_question"
                            ][j]["audio"] = audio.get("ogg")

                            character_state_db["data"]["interaction"][i]["options_dialog"][
                                "prompt_user_question"
                            ][j]["audio_mp3"] = audio.get("mp3")

                await db["state_glic"].update_one(
                    {"_id": character_state_db["_id"]},
                    {
                        "$set": {
                            "data": character_state_db["data"],
                        }
                    },
                )
        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generate voice service 2: {str(e)}")
        return False


async def generate_image_character_face(_character_id, _user_id, _state_game_id) -> tuple:
    if os.environ.get("MODE_TEST", False):
        # En modo test, no generar imagen, solo asignar la imagen estática
        url_image = "https://storage.googleapis.com/qwestar/voxel_.jpg"
        _character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
        character_state_db = await db["state_glic"].find_one({"element_id": _character_id, "state": _state_game_id})
        character_state_db["data"]["image"] = url_image
        await db["state_glic"].update_one({"_id": character_state_db["_id"]},
                                          {"$set": {"data": character_state_db["data"]}})
        return True, "Image set to static test image"

    try:
        _character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})

        character_state_db = await db["state_glic"].find_one(
            {"element_id": _character_id, "state": _state_game_id}
        )

        validate_prompt = await openai_generator.moderation_text(
            text=f"Genera una imagen cuadrada en vista frontal de {character_state_db['data']['prompt_user']},"
                 " de ojos vivos, rasgos faciales exagerados y expresivos, de la "
                 "cintura para arriba, en estilo 3D Cel-shaded que Imita el aspecto "
                 "de los dibujos animados 2D, utilizando colores planos pero vivos y "
                 f"contornos marcados. Con fondo Blanco.",
            user_id=_user_id,
        )
        if validate_prompt:
            return False, "Prompt not allowed"

        if character_state_db["data"]["image_reference"] and character_state_db["data"]["image_reference"] != "" and \
                character_state_db['data']['prompt_user']:
            image_reference = character_state_db['data']['image_reference']
            response = requests.get(image_reference)
            image_bytes = BytesIO(response.content)

            image_base64 = base64.b64encode(image_bytes.getvalue()).decode('utf-8')

            image_face = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Genera una imagen cuadrada de 1024x1024 de un personaje en estilo 3D low poly,"
                                        " de la cintura para arriba,  con fondo de color solido que contraste."
                                        " Utilizando la imagen de referencia.",
                            },
                            {
                                "type": "input_text",
                                "text": f"nombre del personaje: {character_state_db['data']['name']} y descripción del personaje por "
                                        f"parte del usuario: {character_state_db['data']['prompt_user']}"
                                        f"genero: {character_state_db['data']['genre']}",
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{image_base64}",
                            }
                        ],
                    },
                ],
                model="gpt-4.1",
                user_id=_user_id,
                type_generation="character_face_with_reference",
                image=True,
                tools=[{"type": "image_generation"}]
            )

            image_data = base64.b64decode(image_face)

            image_face = BytesIO(image_data)

            image_generated = upload_image(
                img_byte_arr=image_face,
                file_name=f"characters/{uuid4()}.jpg",
                size=(512, 512),
            )

            character_state_db["data"]["image"] = image_generated

            await db["state_glic"].update_one(
                {"_id": character_state_db["_id"]},
                {
                    "$set": {
                        "data": character_state_db["data"],
                    }
                },
            )

            return True, "Image generated successfully with reference"

        if not character_state_db['data']['image_reference'] and character_state_db['data']['prompt_user']:
            image_face = await openai_generator.generate_image(
                prompt=f"Genera una imagen en vista frontal cuadrada de 1024x1024 de un personaje,"
                       f" ({character_state_db['data']['prompt_user']}) en estilo 3D low poly, de la cintura para "
                       f"arriba mirando al frente con los brazos hacia abajo, con fondo de color solido que contraste."
                       f"genero: {character_state_db['data']['genre']}, "
                       f" Utilizando la imagen de referencia.",
                size="1024x1024",
                user_id=_user_id,
                model="gpt-image-1",
                style=None,
                type_generation="character_face",
            )

            image_bytes = base64.b64decode(image_face)

            image_generated = upload_image(
                img_byte_arr=image_bytes,
                file_name=f"characters/{uuid4()}.jpg",
                size=(512, 512),
            )

            character_state_db["data"]["image"] = image_generated

            await db["state_glic"].update_one(
                {"_id": character_state_db["_id"]},
                {
                    "$set": {
                        "data": character_state_db["data"],
                    }
                },
            )

            return True, "Image generated successfully"

        if character_state_db['data']['image_reference'] and not character_state_db['data']['prompt_user']:
            character_state_db["data"]["image"] = character_state_db['data']['image_reference']
            await db["state_glic"].update_one(
                {"_id": character_state_db["_id"]},
                {
                    "$set": {
                        "data": character_state_db["data"],
                    }
                },
            )
            return True, "Image generated successfully with reference but no prompt user"

        return False, "No prompt user provided for character image generation"
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in get images character service: {str(e)}")
        return False, "Error in generate image character"


class SchemaSelectBodyType(BaseModel):
    body_type: str = Field(
        ...,
        example="body_type",
        description="body type of the character according to the description",
    )
    genre: str = Field(
        ..., example="genre", description="genre of the character according to the description"
    )


class SchemaCharacterCreate(BaseModel):
    description: str = Field(
        ...,
        example="description",
        description="description to identify the colors that the character has, it is necessary "
                    "to know the colors of clothes, shoes, hair, skin, eyes and lips",
    )
    description_shoulder_up: str = Field(
        ...,
        example="description_shoulder_up",
        description="string (15-word description cut from the head to the waist of"
                    " the character, to generate an image of the character",
    )


class SchemaSelectCharacterType(BaseModel):
    character_type: str = Field(
        ..., example="type_body", description="type of character according to the description"
    )


async def generate_character_body_type(_character_id, _user_id, _state_game_id):
    try:
        character_state_db = await db["state_glic"].find_one(
            {"element_id": _character_id, "state": _state_game_id}
        )

        response_type_genre = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Eres un identificador de genero y tipo de cuerpo de un personaje, "
                               "los generos son: man, woman o null, los tipos de cuerpo son: "
                               " adult, child o animal, no te debes salir de estos generos y tipos de cuerpo "
                               "y tampoco debes inventar un tipo que no este.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"nombre del personaje: {character_state_db['data']['name']} y descripción del personaje por "
                                    f"parte del usuario: {character_state_db['data']['prompt_user']}",
                        },
                    ],
                },
            ],
            model="gpt-4o-mini-2024-07-18",
            max_tokens=4096,
            response_format=SchemaSelectBodyType,
            type_generation="detect_body_type__genre",
            user_id=_user_id,
        )

        character_type_db = (
            await db["character_type"]
            .find({"body_type": response_type_genre.body_type, "genre": response_type_genre.genre})
            .to_list(None)
        )

        response_character_type = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content":
                        "Eres un identificador de tipo de personaje, no te debes salir de los tipos de cuerpo de personajes que se envian."
                        f"escoge uno de los siquientes tipos de personajes: {character_type_db}"},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"nombre del personaje: {character_state_db['data']['name']} y descripción del personaje por "
                                    f"parte del usuario: {character_state_db['data']['prompt_user']}",
                        }
                    ],
                },
            ],
            model="gpt-4o-mini-2024-07-18",
            max_tokens=4096,
            response_format=SchemaSelectCharacterType,
            type_generation="detect_character_type",
            user_id=_user_id,
        )

        body_type_selected = await  db["character_type"].find_one(
            {"character_type": response_character_type.character_type}
        )

        if not body_type_selected:
            if response_type_genre.genre == "man":
                body_type_selected = "man_casual"
            elif response_type_genre.genre == "woman":
                body_type_selected = "woman_casual"
            else:
                body_type_selected = "man_casual"
        else:
            body_type_selected = body_type_selected.get("character_type", None)

        character_state_db["data"]["body_type"] = response_type_genre.body_type
        character_state_db["data"]["genre"] = response_type_genre.genre
        character_state_db["data"]["character_type"] = body_type_selected

        await db["state_glic"].update_one(
            {"_id": character_state_db["_id"]},
            {
                "$set": {
                    "data": character_state_db["data"],
                }
            },
        )

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in get character body type service: {str(e)}")
        return False


class SchemaCharacterPart(BaseModel):
    section: str = Field(..., example="section", description="section of the character")
    color: str = Field(..., example="color", description="color of the section in hexadecimal")
    equal: str = Field(..., example="equal", description="equal of the section")


class SchemaCharacterPersonalization(BaseModel):
    personalization: list[SchemaCharacterPart] = Field(None, description="personalization of the section")


async def generate_character_personalization(_character_id, _user_id, _state_game_id):
    try:
        element_state_db = await (db["state_glic"]
        .find_one(
            {"element_id": _character_id, "state": _state_game_id}
        ))

        body_type_db = await (db["character_type"].
        find_one(
            {"character_type": element_state_db["data"]["character_type"]}
        ))

        if not body_type_db.get("personalization"):
            element_state_db["data"]["personalization"] = []

            await db["state_glic"].update_one(
                {"_id": element_state_db["_id"]},
                {
                    "$set": {
                        "data": element_state_db["data"],
                    }
                },
            )
            return True

        response_analyze = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f"Analiza cuidadosamente la imagen proporcionada y detecta los colores de las diferentes partes del personaje que se indican. "
                               f"Debes proporcionar una descripción muy detallada de los colores, incluyendo tonos y matices específicos. "
                               f"Las partes del personaje a analizar son: {str(body_type_db['personalization'])} "
                               f"Asegúrate de ser lo más preciso posible en la definición de los colores, describe colores pastel u oscurecidos,"
                               f"si hay section que tengas 'equal' deben tener el mismo color de es seccion o prenda.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": element_state_db["data"]["image"]}
                        },
                        {
                            "type": "text",
                            "text": f"parte de la IA: {element_state_db['data']['description']}",
                        }
                    ],
                },
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            type_generation="analyze_character_personalization",
            user_id=_user_id,
            vision=True,
        )

        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Eres un generador de personalización de personajes, "
                               "debes generar una lista de personalización de personajes, "
                               "como colores. describe colores pastel u oscurecidos, y los colores deben estar en formato hexadecimal."
                               "paleta de tonos de piel: Piel muy clara: #F9E0D9, Piel clara: #F1C27D, Piel media: #C68642, Piel oscura: #8D5524."
                               "paleta de tonos de cabello: Rubio claro: #F4E1B3, Castaño claro: #A9745B, Castaño oscuro: #5C4033, Negro azabache: #2C2220, Pelirrojo: #B55239"
                               """
                               Usa la siguiente paleta de colores para la ropa:
                                Tonos neutros:
                                - Blanco puro (#FFFFFF)
                                - Marfil (#F8F4E3)
                                - Beige (#F5F5DC)
                                - Gris claro (#D3D3D3)
                                - Gris medio (#808080)
                                - Gris oscuro (#4B4B4B)
                                - Negro (#000000)
                                
                                Tonos pasteles:
                                - Rosa pastel (#F8C8DC)
                                - Azul pastel (#AEC6CF)
                                - Verde menta (#98FF98)
                                - Amarillo suave (#FFFACD)
                                - Lavanda (#E6E6FA)
                                - Durazno (#FFDAB9)
                                
                                Tonos vivos:
                                - Rojo carmín (#B22222)
                                - Naranja brillante (#FF7F00)
                                - Amarillo intenso (#FFD700)
                                - Verde esmeralda (#50C878)
                                - Azul real (#4169E1)
                                - Púrpura profundo (#800080)
                                - Fucsia (#FF00FF)
                                
                                Tonos oscuros:
                                - Burdeos (#800020)
                                - Verde botella (#006400)
                                - Azul marino (#000080)
                                - Marrón chocolate (#4B3621)
                                - Mostaza oscura (#B8860B)
                                - Teal oscuro (#008080)
                               """,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"analisis de colores de la imagen del personaje: {response_analyze},"
                                    f"partes del personaje a analizar:{str(body_type_db['personalization'])}",
                        },
                    ],
                },
            ],
            model="gpt-4o-mini-2024-07-18",
            max_tokens=4096,
            response_format=SchemaCharacterPersonalization,
            type_generation="generate_character_personalization",
            user_id=_user_id,
        )

        response_result = []
        if response.personalization:
            for personalization in response.personalization:
                matching_section = next(
                    (p_db for p_db in body_type_db["personalization"] if p_db["section"] == personalization.section),
                    None
                )
                if matching_section:
                    personalization.color = personalization.color or "#000000"
                    response_result.append(personalization.dict())

        element_state_db["data"]["personalization"] = response_result

        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {
                "$set": {
                    "data": element_state_db["data"],
                }
            },
        )

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in get character personalization service: {str(e)}")
        return False


async def generate_character_description(_character_id, _user_id, _state_game_id):
    try:

        character_state_db = await db["state_glic"].find_one(
            {"element_id": _character_id, "state": _state_game_id}
        )

        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "create 3 descriptions for the character, one for the character description, one for the "
                               "game description and one for the description for the generation of a picture of the character.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Name character: {character_state_db['data']['prompt_user']}",
                        },
                        {
                            "type": "text",
                            "text": f"Description of the role of character in history: {character_state_db['data']['prompt_user']}",
                        },
                        # ,{"type": "text", "text": f"Description visual of the character: {_character_db['prompt_user']}"}
                    ],
                },
            ],
            model="gpt-4o-mini-2024-07-18",
            max_tokens=4096,
            response_format=SchemaCharacterCreate,
            user_id=_user_id,
            type_generation="create_description_character",
        )

        character_state_db["data"]["description"] = response.description
        character_state_db["data"]["description_shoulder_up"] = response.description_shoulder_up

        await db["state_glic"].update_one(
            {"_id": character_state_db["_id"]},
            {
                "$set": {
                    "data": character_state_db["data"],
                }
            },
        )

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in get character description service: {str(e)}")
        return False


class SchemaCharacterConversation(BaseModel):
    id_character: str = Field(..., example="id_character", description="id of the character")
    dialog: str = Field(
        ...,
        example="dialog",
        description="dialog of the character and be a maximum of 15-30 words.",
    )


class SchemaCharacterConversations(BaseModel):
    conversation: list[SchemaCharacterConversation] = Field(
        ..., example=[{"key": "value"}], description="conversation of the character"
    )


async def generate_conversation_character(
        _game_id, _character_id, _user_id, _location_id, _state_game_id
):
    game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_principal_db = await db["character"].find_one(
        {"_id": ObjectId(game_db["character_principal"])}
    )
    character_other_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    element_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id}
    )
    language_detection = await generate_language_detection(
        element_state_db['data']['prompt_user_dialog'], _user_id
    )
    try:

        # response = await openai_generator.generate_gpt(
        #     content_prompt=[
        #         {
        #             "role": "system",
        #             "content": f" You are a character dialogue extractor, according to a text where there is a conversation between two characters as follows. "
        #                        + "1. hello. how are you?"
        #                        + "2. hello, well how are you?"
        #                        + "where 1 is the main character and 2 is the other character, transform it to a"
        #                          "replace 1 with the id of the main character and 2 with the id of the other character, "
        #                          " conversation according to the json schema and the data provided by the user, and "
        #                          f"correct the spelling of the dialogue text in the {language_detection} language.",
        #         },
        #         {
        #             "role": "user",
        #             "content": [
        #                 {
        #                     "type": "text",
        #                     "text": f"Main character id: {str(character_principal_db['_id'])}",
        #                 },
        #                 {
        #                     "type": "text",
        #                     "text": f"Other character id: {str(character_other_db['_id'])}",
        #                 },
        #                 {
        #                     "type": "text",
        #                     "text": f"Conversation of the character: {element_state_db['data']['prompt_user_dialog']}",
        #                 },
        #             ],
        #         },
        #     ],
        #     model="gpt-4o-mini-2024-07-18",
        #     max_tokens=4096,
        #     response_format=SchemaCharacterConversations,
        #     user_id=_user_id,
        #     type_generation="create_conversation_character",
        # )
        # conversation_ = [
        #     {"id_character": dialog.id_character, "dialog": dialog.dialog, "audio": None, "audio_mp3": None, }
        #     for dialog in response.conversation
        # ]

        interaction_exists = False

        if "interaction" not in element_state_db["data"]:
            element_state_db["data"]["interaction"] = []

        for interaction in element_state_db["data"]["interaction"]:
            if (
                    interaction["location_id"] == _location_id
                    and interaction["state_game"] == _state_game_id
            ):
                interaction["conversation"] = element_state_db["data"]["conversation"]
                interaction["prompt_user_dialog"] = element_state_db["data"]["prompt_user_dialog"]
                interaction["type_conversation"] = "two_way"
                interaction_exists = True
                break

        if not interaction_exists:
            element_state_db["data"]["interaction"].append(
                {
                    "location_id": _location_id,
                    "state_game": _state_game_id,
                    "type_conversation": "two_way",
                    "prompt_user_dialog": element_state_db["data"]["prompt_user_dialog"],
                    "conversation": element_state_db["data"]["conversation"],
                }
            )

        element_state_db["data"]["conversation"] = element_state_db["data"]["conversation"]

        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {
                "$set": {
                    "data": element_state_db["data"],
                }
            },
        )

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating character conversation: {str(e)}")
        return False


class SchemaCharacterConversationPrompt(BaseModel):
    is_conversation: bool = Field(..., example=True, description="is conversation prompt")


async def identify_prompt_conversation(_prompt_dialog, _user_id):
    try:
        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Identifica si el texto es una conversación, respondiendo con un valor booleano."
                               "para saber si es una conversación o no, si tiene la siquiente estructura por ejemplo: "
                               "1. hello. how are you?"
                               + "2. hello, well how are you?"
                               + "es una conversación.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Prompt: {_prompt_dialog}",
                        },
                    ],
                },
            ],
            model="gpt-4o-mini",
            max_tokens=500,
            response_format=SchemaCharacterConversationPrompt,
            user_id=_user_id,
            type_generation="identify_prompt_conversation",
        )
        return response
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating character conversation: {str(e)}")
        return False


async def generate_option_character(
        _game_id, _character_id, _user_id, _location_id, _state_game_id
):
    game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_principal_db = await db["character"].find_one(
        {"_id": ObjectId(game_db["character_principal"])}
    )
    if not character_principal_db:
        print(f"Error not found character principal: {game_db['character_principal']}")
        return False
    character_other_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    element_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id}
    )
    # language_detection = await generate_language_detection(
    #     element_state_db['data']['options_dialog'], _user_id
    # )

    # try:
    #
    #     question_ic = await identify_prompt_conversation(
    #         element_state_db['data']['options_dialog']["prompt_user_question"], _user_id
    #     )
    #
    #     if question_ic.is_conversation:
    #         response = await openai_generator.generate_gpt(
    #             content_prompt=[
    #                 {
    #                     "role": "system",
    #                     "content": f" You are a character dialogue extractor, according to a text where there is a conversation between two characters as follows. "
    #                                + "1. hello. how are you?"
    #                                + "2. hello, well how are you?"
    #                                + "where 1 is the main character and 2 is the other character, transform it to a"
    #                                  "replace 1 with the id of the main character and 2 with the id of the other character, "
    #                                  " conversation according to the json schema and the data provided by the user, and "
    #                                  f"correct the spelling of the dialogue text in the {language_detection} language.",
    #                 },
    #                 {
    #                     "role": "user",
    #                     "content": [
    #                         {
    #                             "type": "text",
    #                             "text": f"Main character id: {str(character_principal_db['_id'])}",
    #                         },
    #                         {
    #                             "type": "text",
    #                             "text": f"Other character id: {str(character_other_db['_id'])}",
    #                         },
    #                         {
    #                             "type": "text",
    #                             "text": f"Conversation of the character: {element_state_db['data']['options_dialog']['prompt_user_question']}",
    #                         },
    #                     ],
    #                 },
    #             ],
    #             model="gpt-4o-mini-2024-07-18",
    #             max_tokens=4096,
    #             response_format=SchemaCharacterConversations,
    #             user_id=_user_id,
    #             type_generation="create_conversation_character",
    #         )
    #         conversation_ = [
    #             {"id_character": dialog.id_character, "dialog": dialog.dialog, "audio": None}
    #             for dialog in response.conversation
    #         ]
    #         element_state_db["data"]['options_dialog']['prompt_user_question'] = conversation_
    #     else:
    #         response = await openai_generator.generate_gpt(
    #             content_prompt=[
    #                 {
    #                     "role": "system",
    #                     "content": f" Correct spelling on the text of the dialogue in the {language_detection} language. ",
    #                 },
    #                 {
    #                     "role": "user",
    #                     "content": [
    #                         {
    #                             "type": "text",
    #                             "text": f"character dialog: {element_state_db['data']['options_dialog']['prompt_user_question']}"
    #                                     f"id: {str(character_other_db['_id'])}",
    #                         },
    #                     ],
    #                 },
    #             ],
    #             model="gpt-4o-mini-2024-07-18",
    #             max_tokens=4096,
    #             response_format=SchemaCharacterConversations,
    #             user_id=_user_id,
    #             type_generation="create_monologue_character",
    #         )
    #
    #         conversation_ = [
    #             {
    #                 "id_character": str(character_other_db["_id"]),
    #                 "dialog": element_state_db['data']['options_dialog']['prompt_user_question'],
    #                 "audio": None,
    #                 "audio_mp3": None,
    #             }
    #         ]
    #
    #         element_state_db["data"]['options_dialog']['prompt_user_question'] = conversation_
    #
    # except Exception as e:
    #     print(traceback.format_exc())
    #     print(f"Error in generating character option (question): {str(e)}")
    #     return False

    for option in range(len(element_state_db["data"]['options_dialog']['options'])):
        try:

            # response = await openai_generator.generate_gpt(
            #     content_prompt=[
            #         {
            #             "role": "system",
            #             "content": f"transcribe the text of the dialog in the language {language_detection}, don't overwrite the text, send it as it is"
            #         },
            #         {
            #             "role": "user",
            #             "content": [
            #                 {
            #                     "type": "text",
            #                     "text": f"character dialog: {element_state_db['data']['options_dialog']['options'][option]['prompt_user_option']}"
            #                             f"id: {str(character_other_db['_id'])}",
            #                 },
            #             ],
            #         },
            #     ],
            #     model="gpt-4o-mini-2024-07-18",
            #     max_tokens=4096,
            #     response_format=SchemaCharacterConversations,
            #     user_id=_user_id,
            #     type_generation="create_monologue_character",
            # )

            print("debug.. ",element_state_db["data"]["options_dialog"]["options"][option], option)

            conversation_ = {
                "id_character": str(character_principal_db["_id"]),
                "dialog": element_state_db['data']['options_dialog']['options'][option]['prompt_user_option']["dialog"],
                "audio": None,
                "audio_mp3": None,
            }

            element_state_db["data"]['options_dialog']['options'][option]['prompt_user_option'] = conversation_

            # response = await openai_generator.generate_gpt(
            #     content_prompt=[
            #         {
            #             "role": "system",
            #             "content": f"transcribe the text of the dialog in the language {language_detection}, don't overwrite the text, send it as it is "
            #         },
            #         {
            #             "role": "user",
            #             "content": [
            #                 {
            #                     "type": "text",
            #                     "text": f"character dialog: {element_state_db['data']['options_dialog']['options'][option]['prompt_user_answer']}"
            #                             f"id: {str(character_other_db['_id'])}",
            #                 },
            #             ],
            #         },
            #     ],
            #     model="gpt-4o-mini-2024-07-18",
            #     max_tokens=4096,
            #     response_format=SchemaCharacterConversations,
            #     user_id=_user_id,
            #     type_generation="create_monologue_character",
            # )

            conversation_ = {
                "id_character": str(character_other_db["_id"]),
                "dialog": element_state_db['data']['options_dialog']['options'][option]['prompt_user_answer']["dialog"],
                "audio": None,
                "audio_mp3": None,
            }

            element_state_db["data"]['options_dialog']['options'][option]['prompt_user_answer'] = conversation_

        except Exception as e:
            print(traceback.format_exc())
            print(f"Error in generating character option (answer): {str(e)}")
            return False

    interaction_exists = False

    if "interaction" not in element_state_db["data"]:
        element_state_db["data"]["interaction"] = []

    for interaction in element_state_db["data"]["interaction"]:
        if (interaction["location_id"] == _location_id and interaction["state_game"] == _state_game_id):
            interaction["options_dialog"] = element_state_db["data"]["options_dialog"]
            interaction["prompt_user_dialog"] = None
            interaction["type_conversation"] = "option_multiple"
            interaction["options"] = element_state_db["data"]["options"]
            interaction["prompt_user_question"] = element_state_db["data"]["prompt_user_question"]
            interaction["prompt_user_guideline"] = element_state_db["data"]["prompt_user_guideline"]
            interaction_exists = True
            break

    if not interaction_exists:
        element_state_db["data"]["interaction"].append(
            {
                "location_id": _location_id,
                "state_game": _state_game_id,
                "type_conversation": "option_multiple",
                "prompt_user_dialog": None,
                "options": element_state_db["data"]["options"],
                "prompt_user_question": element_state_db["data"]["prompt_user_question"],
                "options_dialog": element_state_db["data"]["options_dialog"],
            }
        )

    try:

        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {
                "$set": {
                    "data": element_state_db["data"],
                }
            },
        )

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating character conversation: {str(e)}")
        return False


async def generate_open_talk_character(
        _game_id, _character_id, _user_id, _location_id, _state_game_id
):
    game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_principal_db = await db["character"].find_one(
        {"_id": ObjectId(game_db["character_principal"])}
    )
    character_other_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    element_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id}
    )
    language_detection = await generate_language_detection(
        element_state_db['data']['options_dialog']['prompt_user_question'], _user_id
    )
    try:

        question_ic = await identify_prompt_conversation(
            element_state_db['data']['options_dialog']["prompt_user_question"], _user_id
        )

        if question_ic.is_conversation:
            response = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": f" You are a character dialogue extractor, according to a text where there is a conversation between two characters as follows. "
                                   + "1. hello. how are you?"
                                   + "2. hello, well how are you?"
                                   + "where 1 is the main character and 2 is the other character, transform it to a"
                                     "replace 1 with the id of the main character and 2 with the id of the other character, "
                                     " conversation according to the json schema and the data provided by the user, and "
                                     f"correct the spelling of the dialogue text in the {language_detection} language.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Main character id: {str(character_principal_db['_id'])}",
                            },
                            {
                                "type": "text",
                                "text": f"Other character id: {str(character_other_db['_id'])}",
                            },
                            {
                                "type": "text",
                                "text": f"Conversation of the character: {element_state_db['data']['options_dialog']['prompt_user_question']}",
                            },
                        ],
                    },
                ],
                model="gpt-4o-mini-2024-07-18",
                max_tokens=4096,
                response_format=SchemaCharacterConversations,
                user_id=_user_id,
                type_generation="create_conversation_character",
            )
            conversation_ = [
                {"id_character": dialog.id_character, "dialog": dialog.dialog, "audio": None}
                for dialog in response.conversation
            ]
            element_state_db["data"]['options_dialog']['prompt_user_question'] = conversation_
        else:
            response = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": f" Correct spelling on the text of dialogue in the {language_detection} language. ",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"character dialog: {element_state_db['data']['options_dialog']['prompt_user_question']}"
                                        f"id: {str(character_other_db['_id'])}",
                            },
                        ],
                    },
                ],
                model="gpt-4o-mini-2024-07-18",
                max_tokens=4096,
                response_format=SchemaCharacterConversations,
                user_id=_user_id,
                type_generation="create_monologue_character",
            )

            conversation_ = [
                {
                    "id_character": str(character_other_db["_id"]),
                    "dialog": element_state_db['data']['options_dialog']['prompt_user_question'],
                    "audio": None,
                    "audio_mp3": None,
                }
            ]

            element_state_db["data"]['options_dialog']['prompt_user_question'] = conversation_
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating character conversation: {str(e)}")
        return False

    interaction_exists = False
    if "interaction" not in element_state_db["data"]:
        element_state_db["data"]["interaction"] = []

    for interaction in element_state_db["data"]["interaction"]:
        if (
                interaction["location_id"] == _location_id
                and interaction["state_game"] == _state_game_id
        ):
            interaction["options_dialog"] = element_state_db["data"]["options_dialog"]
            interaction["prompt_user_dialog"] = None
            interaction["type_conversation"] = "open_talk"
            interaction["options"] = element_state_db["data"]["options_dialog"]["options"]
            interaction["num_interaction"] = element_state_db["data"]["options_dialog"]["num_interaction"]
            interaction["prompt_user_question"] = element_state_db["data"]["options_dialog"]["prompt_user_question"]
            interaction["prompt_user_guideline"] = element_state_db["data"]["options_dialog"]["prompt_user_guideline"]
            interaction_exists = True
            break

    if not interaction_exists:
        element_state_db["data"]["interaction"].append(
            {
                "location_id": _location_id,
                "state_game": _state_game_id,
                "type_conversation": "open_talk",
                "prompt_user_dialog": None,
                "num_interaction": element_state_db["data"]["options_dialog"]["num_interaction"],
                "options_dialog": element_state_db["data"]["options_dialog"],
                "options": element_state_db["data"]["options_dialog"]["options"],
                "prompt_user_question": element_state_db["data"]["options_dialog"]["prompt_user_question"],
                "prompt_user_guideline": element_state_db["data"]["options_dialog"]["prompt_user_guideline"],
            }
        )

    try:
        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {
                "$set": {
                    "data": element_state_db["data"],
                }
            },
        )

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating character conversation: {str(e)}")
        return False


async def generate_open_question_character(
        _game_id, _character_id, _user_id, _location_id, _state_game_id
):
    game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_principal_db = await db["character"].find_one(
        {"_id": ObjectId(game_db["character_principal"])}
    )
    character_other_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    element_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id}
    )
    # language_detection = await generate_language_detection(
    #     element_state_db['data']['options_dialog'], _user_id
    # )

    # try:

        # question_ic = await identify_prompt_conversation(
        #     element_state_db['data']['options_dialog']["prompt_user_question"], _user_id
        # )
        #
        # if question_ic.is_conversation:
        #     response = await openai_generator.generate_gpt(
        #         content_prompt=[
        #             {
        #                 "role": "system",
        #                 "content": f" You are a character dialogue extractor, according to a text where there is a conversation between two characters as follows. "
        #                            + "1. hello. how are you?"
        #                            + "2. hello, well how are you?"
        #                            + "where 1 is the main character and 2 is the other character, transform it to a"
        #                              "replace 1 with the id of the main character and 2 with the id of the other character, "
        #                              " conversation according to the json schema and the data provided by the user, and "
        #                              f"correct the spelling of the dialogue text in the {language_detection} language.",
        #             },
        #             {
        #                 "role": "user",
        #                 "content": [
        #                     {
        #                         "type": "text",
        #                         "text": f"Main character id: {str(character_principal_db['_id'])}",
        #                     },
        #                     {
        #                         "type": "text",
        #                         "text": f"Other character id: {str(character_other_db['_id'])}",
        #                     },
        #                     {
        #                         "type": "text",
        #                         "text": f"Conversation of the character: {element_state_db['data']['options_dialog']['prompt_user_question']}",
        #                     },
        #                 ],
        #             },
        #         ],
        #         model="gpt-4o-mini-2024-07-18",
        #         max_tokens=4096,
        #         response_format=SchemaCharacterConversations,
        #         user_id=_user_id,
        #         type_generation="create_conversation_character",
        #     )
        #     conversation_ = [
        #         {"id_character": dialog.id_character, "dialog": dialog.dialog, "audio": None, "audio_mp3": None}
        #         for dialog in response.conversation
        #     ]
        #     element_state_db["data"]['options_dialog']['prompt_user_question'] = conversation_
        #
        # else:
            # response = await openai_generator.generate_gpt(
            #     content_prompt=[
            #         {
            #             "role": "system",
            #             "content": f" Correct spelling on the text of dialogue in the {language_detection} language."
            #                        f"no cambies el texto, envíalo tal cual."
            #         },
            #         {
            #             "role": "user",
            #             "content": [
            #                 {
            #                     "type": "text",
            #                     "text": f"character dialog: {element_state_db['data']['options_dialog']['prompt_user_question']}"
            #                             f"id: {str(character_other_db['_id'])}",
            #                 },
            #             ],
            #         },
            #     ],
            #     model="gpt-4o-mini-2024-07-18",
            #     max_tokens=4096,
            #     response_format=SchemaCharacterConversations,
            #     user_id=_user_id,
            #     type_generation="create_monologue_character",
            # )

    # conversation_ = [
    #     {
    #         "id_character": str(character_other_db["_id"]),
    #         "dialog": element_state_db['data']['options_dialog']['prompt_user_question']["dialog"],
    #         "audio": None,
    #         "audio_mp3": None,
    #     }
    # ]
    #
    # print("prompt_user_question conversation_: ", conversation_)
    #
    # element_state_db["data"]['options_dialog']['prompt_user_question'] = conversation_

    # except Exception as e:
    #     print(f"Error in generating character option (question): {str(e)}")
    #     return False

    for option in range(len(element_state_db["data"]['options_dialog']['options'])):
        try:
            # response = await openai_generator.generate_gpt(
            #     content_prompt=[
            #         {
            #             "role": "system",
            #             "content": f"transcribe the text of the dialog in the language {language_detection}, don't overwrite the text, send it as it is "
            #         },
            #         {
            #             "role": "user",
            #             "content": [
            #                 {
            #                     "type": "text",
            #                     "text": f"character dialog: {element_state_db['data']['options_dialog']['options'][option]['prompt_user_answer']}"
            #                             f"id: {str(character_other_db['_id'])}",
            #                 },
            #             ],
            #         },
            #     ],
            #     model="gpt-4o-mini-2024-07-18",
            #     max_tokens=4096,
            #     response_format=SchemaCharacterConversations,
            #     user_id=_user_id,
            #     type_generation="create_monologue_character",
            # )

            conversation_ = {
                "id_character": str(character_other_db["_id"]),
                "dialog": element_state_db['data']['options_dialog']['options'][option]['prompt_user_answer']['dialog'],
                "audio": None,
                "audio_mp3": None,
            }

            element_state_db["data"]['options_dialog']['options'][option]['prompt_user_answer'] = conversation_

        except Exception as e:
            print(f"Error in generating character option (answer): {str(e)}")
            return False

    # python
    print("DEBUG: open_question - entering block", {"_location_id": _location_id, "_state_game_id": _state_game_id})

    interaction_exists = False

    if "interaction" not in element_state_db["data"]:
        print("DEBUG: 'interaction' not in element_state_db['data'], creating empty list")
        element_state_db["data"]["interaction"] = []
    else:
        print("DEBUG: existing interactions count:", len(element_state_db["data"]["interaction"]))

    for idx, interaction in enumerate(element_state_db["data"]["interaction"]):
        print(f"DEBUG: checking interaction {idx} -> location_id={interaction.get('location_id')} state_game={interaction.get('state_game')}")
        if (
                interaction["location_id"] == _location_id
                and interaction["state_game"] == _state_game_id
        ):
            print("DEBUG: match found at index", idx)
            print("DEBUG: before update interaction:", interaction)
            interaction["options_dialog"] = element_state_db["data"]["options_dialog"]
            interaction["prompt_user_dialog"] = None
            interaction["type_conversation"] = "open_question"
            interaction["options"] = element_state_db["data"]["options"]
            interaction["prompt_user_question"] = element_state_db["data"]["prompt_user_question"]
            interaction_exists = True
            print("DEBUG: after update interaction:", interaction)
            break

    if not interaction_exists:
        new_interaction = {
            "location_id": _location_id,
            "state_game": _state_game_id,
            "type_conversation": "open_question",
            "prompt_user_dialog": None,
            "options": element_state_db["data"]["options"],
            "prompt_user_question": element_state_db["data"]["prompt_user_question"],
            "options_dialog": element_state_db["data"]["options_dialog"],
        }
        element_state_db["data"]["interaction"].append(new_interaction)
        print("DEBUG: appended new interaction:", new_interaction)

    print("DEBUG: total interactions after operation:", len(element_state_db["data"]["interaction"]))

    try:

        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {
                "$set": {
                    "data": element_state_db["data"],
                }
            },
        )

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating character conversation: {str(e)}")
        return False


async def generate_monologue_character(
        _game_id, _character_id, _user_id, _location_id, _state_game_id
):
    # game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_other_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    character_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id}
    )
    try:
        # if not character_other_db.get("prompt_user_dialog"):
        #     character_other_db["prompt_user_dialog"] = game_db["history"]

        language_detection = await generate_language_detection(
            character_state_db["data"]['prompt_user_dialog'], _user_id
        )

        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f" Correct spelling on the text of dialogue in the {language_detection} language. ",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"character dialog: {character_state_db['data']['prompt_user_dialog']}"
                                    f"id: {str(character_other_db['_id'])}",
                        },
                    ],
                },
            ],
            model="gpt-4o-mini-2024-07-18",
            max_tokens=4096,
            response_format=SchemaCharacterConversations,
            user_id=_user_id,
            type_generation="create_monologue_character",
        )

        conversation_ = [
            {"id_character": str(character_other_db["_id"]), "dialog": dialog.dialog, "audio": None,
             "audio_mp3": None, }
            for dialog in response.conversation
        ]

        interaction_exists = False

        if "interaction" not in character_state_db["data"]:
            character_state_db["data"]["interaction"] = []

        for interaction in character_state_db["data"]["interaction"]:
            if (
                    interaction["location_id"] == _location_id
                    and interaction["state_game"] == _state_game_id
            ):
                interaction["conversation"] = conversation_
                interaction["prompt_user_dialog"] = character_state_db["data"]["prompt_user_dialog"]
                interaction["type_conversation"] = "one_way"
                interaction_exists = True
                break

        if not interaction_exists:
            character_state_db["data"]["interaction"].append(
                {
                    "location_id": _location_id,
                    "state_game": _state_game_id,
                    "type_conversation": "one_way",
                    "prompt_user_dialog": character_state_db["data"]["prompt_user_dialog"],
                    "conversation": conversation_,
                }
            )

        await db["state_glic"].update_one(
            {"_id": character_state_db["_id"]},
            {
                "$set": {
                    "data": character_state_db["data"],
                }
            },
        )

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating character monologue: {str(e)}")
        return False


class SchemaLanguageDetection(BaseModel):
    response: str = Field(..., example="response", description="response of the language detection")


async def generate_language_detection(_text, _user_id):
    try:
        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Detecta el idioma del texto",
                },
                {
                    "role": "user",
                    "content": f"Texto: {str(_text)}",
                },
            ],
            model="gpt-4o-mini-2024-07-18",
            max_tokens=4096,
            response_format=SchemaLanguageDetection,
            user_id=_user_id,
            type_generation="detect_language",
        )

        return response.response
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating language detection: {str(e)}")
        return "english"


async def async_generate_character_task(
        _character_id,
        _user_id,
        _task_id,
        _location_id,
        _state_game_id,
        _game_id,
        _type_game="2d",
        _is_image=False,
):
    if _task_id and _task_id != "" and _task_id is not None:
        await update_task_service(_id=_task_id, _status="pending")

    character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})

    if not character_db:
        if _task_id and _task_id != "" and _task_id is not None:
            await update_task_service(
                _id=_task_id,
                _status="failed",
                _message=f"Error can't find character with id {_character_id}",
            )
        return f"Error can't find character with id {_character_id}"

    response_description = await generate_character_description(
        _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
    )
    if not response_description:
        if _task_id and _task_id != "" and _task_id is not None:
            await update_task_service(
                _id=_task_id, _status="failed", _message="Error in generate character description"
            )
        return "Error in generate character description"

    if _type_game == "3d":
        response_body_type = await generate_character_body_type(
            _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
        )
        if not response_body_type:
            if _task_id and _task_id != "" and _task_id is not None:
                await update_task_service(
                    _id=_task_id, _status="failed", _message="Error in generate character body type"
                )
            return "Error in generate character body type"
    if _is_image:
        response_image, message = await generate_image_character_face(
            _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
        )
        if not response_image:
            if _task_id and _task_id != "" and _task_id is not None:
                await update_task_service(
                    _id=_task_id,
                    _status="failed",
                    _message=message,
                    _status_updated=1,
                )
            return message

    element_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id}
    )

    if _type_game == "3d":
        detection_personalization = await generate_character_personalization(
            _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
        )

        if not detection_personalization:
            if _task_id and _task_id != "" and _task_id is not None:
                await update_task_service(
                    _id=_task_id, _status="failed", _message="Error in generate character personalization"
                )
            return "Error in generate character personalization"

    # voice_generated = await generate_voice_character(
    #     game_id=_game_id,
    #     character_id=_character_id,
    #     user_id=_user_id,
    #     state_game=_state_game_id,
    #     location_id=_location_id,
    #     type_conversation=element_state_db["data"]["conversation_type"],
    #     prompt_user_dialog=element_state_db["data"]["prompt_user_dialog"],
    #     options_dialog=element_state_db["data"]["options_dialog"],
    # )
    #
    # if not voice_generated:
    #     if _task_id and _task_id != "" and _task_id is not None:
    #         await update_task_service(
    #             _id=_task_id, _status="failed", _message="Error voice not generated"
    #         )
    #     return "Error voice not generated"

    if _task_id and _task_id != "" and _task_id is not None:
        await update_task_service(
            _id=_task_id, _status="completed", _message="Character generate successfully"
        )
    return "Character generate successfully"


async def async_update_character_task(
        _character_id,
        _user_id,
        _task_id,
        _game_id,
        _updated_data,
        _updated_voice,
        _state_game_id,
        _location_id,
        _type_game="2d",
):
    if _task_id and _task_id != "" and _task_id is not None:
        await update_task_service(_id=_task_id, _status="pending")

    if _updated_data:
        character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
        if not character_db:
            if _task_id and _task_id != "" and _task_id is not None:
                await update_task_service(
                    _id=_task_id,
                    _status="failed",
                    _message=f"Error can't find character with id {_character_id}",
                )
            return f"Error can't find character with id {_character_id}"

        response_description = await generate_character_description(
            _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
        )
        if not response_description:
            if _task_id and _task_id != "" and _task_id is not None:
                await update_task_service(
                    _id=_task_id, _status="failed", _message="Error in generate character description"
                )
            return "Error in generate character description"

        if _type_game == "3d":
            response_body_type = await generate_character_body_type(
                _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
            )
            if not response_body_type:
                if _task_id and _task_id != "" and _task_id is not None:
                    await update_task_service(
                        _id=_task_id, _status="failed", _message="Error in generate character body type"
                    )
                return "Error in generate character body type"

        response_image, message = await generate_image_character_face(
            _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
        )
        if not response_image:
            if _task_id and _task_id != "" and _task_id is not None:
                await update_task_service(
                    _id=_task_id,
                    _status="failed",
                    _message=message,
                    _status_updated=1,
                )
            return message

        if _type_game == "3d":
            detection_personalization = await generate_character_personalization(
                _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
            )
            if not detection_personalization:
                if _task_id and _task_id != "" and _task_id is not None:
                    await update_task_service(
                        _id=_task_id, _status="failed", _message="Error in generate character personalization"
                    )
                return "Error in generate character personalization"

    if _updated_voice:
        element_state_db = await db["state_glic"].find_one(
            {"element_id": _character_id, "state": _state_game_id}
        )

        voice_generated = await generate_voice_character(
            game_id=_game_id,
            character_id=_character_id,
            user_id=_user_id,
            state_game=_state_game_id,
            options_dialog=element_state_db["data"]["options_dialog"],
            location_id=_location_id,
            type_conversation=element_state_db["data"]["conversation_type"],
            prompt_user_dialog=element_state_db["data"]["prompt_user_dialog"],
        )
        if not voice_generated:
            if _task_id and _task_id != "" and _task_id is not None:
                await update_task_service(
                    _id=_task_id,
                    _status="failed",
                    _message="Error voice not generated",
                    _status_updated=1,
                )
            return "Error voice not generated"

    if _task_id and _task_id != "" and _task_id is not None:
        await update_task_service(
            _id=_task_id,
            _status="completed",
            _message="Character updated successfully",
        )

    return "Character updated successfully"


async def async_generate_image_character_task(_character_id, _user_id, _task_id):
    await update_task_service(_id=_task_id, _status="pending")

    character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    if not character_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message=f"Error can't find character with id {_character_id}",
        )
        return f"Error can't find character with id {_character_id}"
    response_image = await generate_image_character_face(
        _character_db=character_db, _user_id=_user_id
    )
    if not response_image:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Error in generate image character face service",
        )
        return "Error in generate image character face service "
    await update_task_service(
        _id=_task_id, _status="completed", _message="Character image generate successfully"
    )
    return "Character image generate successfully"


async def _generate_image_character(_user_id,
                                    _prompt_user,
                                    _gender,
                                    _id_character,
                                    _game_provisional,
                                    _url_image_reference=None):
    try:
        # Construir el prompt base
        prompt_base = (
            f"Genera una imagen en vista frontal cuadrada de 1024x1024 de un personaje de fondo transparente,"
            f" ({_prompt_user}) en estilo 3D low poly, de la cintura para arriba, sin objetos adicionales, "
            f"mirando al frente con los brazos hacia abajo."
            f"genero: {_gender},"
        )

        # Si existe referencia de imagen, usar generate_image(), sino usar generate_gpt()
        image_face = None
        if _url_image_reference:
            # Usar generate_image con la referencia en el prompt
            prompt_with_reference = (
                prompt_base +
                f" Basándote en el estilo visual de esta referencia ({_url_image_reference}), "
                f"mantén coherencia visual con esa imagen de referencia."
            )
            try:
                image_face = await openai_generator.generate_image(
                    prompt=prompt_with_reference,
                    size="1024x1024",
                    user_id=_user_id,
                    model="gpt-image-1",
                    style=None,
                    type_generation="character_face",
                    background="transparent"
                )
            except Exception as e:
                logger.warning(f"Error generando imagen de personaje con referencia: {str(e)}, usando fallback generate_gpt")
                image_face = None

        # Si no hay respuesta, usar método original con generate_gpt como fallback
        if not image_face:
            content_prompt = [
                {"role": "user", "content": [
                    {"type": "input_text", "text": prompt_base}
                ]}
            ]
            image_face = await openai_generator.generate_gpt(
                content_prompt=content_prompt,
                model="gpt-4.1",
                type_generation="character_face",
                tools=[{"type": "image_generation", "size": "1024x1024"}],
                image=True,
                user_id=_user_id,
            )

        image_bytes = base64.b64decode(image_face)
        image_generated = upload_image(
            img_byte_arr=image_bytes,
            file_name=f"characters/{uuid4()}.png",
            size=(512, 512),
        )

        game_db = await db["game_provisional"].find_one({"_id": ObjectId(_game_provisional)})
        if not game_db:
            return "Error game provisional not found"

        characters = game_db.get("characters", [])
        index_found = next((i for i, c in enumerate(characters) if c.get("id") == _id_character), None)
        if index_found is None:
            return "Error character not found in game provisional"

        # Actualiza la llave image usando el índice
        await db["game_provisional"].update_one(
            {"_id": ObjectId(_game_provisional)},
            {f"$set": {f"characters.{index_found}.image": image_generated}}
        )

        return "Image generated and saved successfully"
    except Exception as e:
        logger.error(f"Error in get images character service: {str(e)}")
        return f"Error in get images character service: {str(e)}"


async def get_voice_for_character(_prompt_user, _gender, _id_character, _game_provisional, _user_id):
    try:
        variants_voices = await get_variants_service()
        response_generated = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Utilizando la siguiente descripción, identificar la voz que mejor se ajuste a la descripción. "
                               f"Respondiendo con la edad y género de la voz,",
                },
                {
                    "role": "assistant",
                    "content": f"Variantes de voces a identificar: {variants_voices}",
                },
                {
                    "role": "user",
                    "content": f"Descripción del personaje: {_prompt_user}"
                               f"Genero del personaje: {_gender}",
                },
            ],
            response_format=SchemaVoiceIdentification,
            type_generation="Voice Identification",
            max_tokens=2000,
            model="gpt-4o-mini",
            user_id=_user_id,
        )

        voice_by_gender = await db["voice"].find({"gender": response_generated.genre}).to_list(None)
        voice_by_age = [voice for voice in voice_by_gender if voice["age"] == response_generated.age]
        voice_by_accent = [voice for voice in voice_by_age if voice["accent"] == "North American"]

        if voice_by_accent:
            voice = voice_by_accent[0]
        elif voice_by_age:
            voice = voice_by_age[0]
        else:
            voice_by_gender_accent = [voice for voice in voice_by_gender if voice["accent"] == "North American"]
            if voice_by_gender_accent:
                voice = voice_by_gender_accent[0]
            elif voice_by_gender:
                voice = voice_by_gender[0]
            else:
                voice = await db["voice"].find_one()
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(_game_provisional)})
        if not game_provisional_db:
            return "Error game provisional not found"
        characters = game_provisional_db.get("characters", [])
        index_found = next((i for i, c in enumerate(characters) if c.get
        ("id") == _id_character), None)
        if index_found is None:
            return "Error character not found in game provisional"
        # Actualiza la llave voice usando el índice
        await db["game_provisional"].update_one(
            {"_id": ObjectId(_game_provisional)},
            {f"$set": {f"characters.{index_found}.voice_id": voice["voice_id"]}}
        )
        return "Voice assigned to character successfully"
    except Exception as e:
        logger.error(f"Error in get voice for character service: {str(e)}")
        return f"Error in get voice for character service: {str(e)}"
