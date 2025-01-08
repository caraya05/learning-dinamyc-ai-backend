import random
import traceback
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


class SchemaVoiceIdentification(BaseModel):
    age: str = Field(..., description="Age of the voice according to the description")
    genre: str = Field(..., description="Genre of the voice according to the description")


async def generate_voice_character(game_id, character_id: str, user_id: str, location_id: str, state_game: str,
                                   type_conversation: str, prompt_user_dialog: str, options_dialog: dict = None):
    try:
        voice = {}
        character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
        character_state_db = await db["state_glic"].find_one(
            {"element_id": character_id, "state": state_game})
        if not character_db.get("voice_id") or not character_state_db["data"].get("voice_id"):
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

            voice_by_gender = (
                await db["voice"].find({"gender": response_generated.genre}).to_list(None)
            )
            voice_by_age = [
                voice for voice in voice_by_gender if voice["age"] == response_generated.age
            ]
            if voice_by_age:
                voice = voice_by_age[0]
            else:
                voice = random.choice(voice_by_gender)
            await db["character"].update_one(
                {"_id": ObjectId(character_id)}, {"$set": {"voice_id": str(voice["voice_id"])}}
            )
        else:
            voice["voice_id"] = character_db["voice_id"]
        character_state_db["data"]["voice_id"] = str(voice["voice_id"])
        character_state_db["data"]["prompt_user_dialog"] = prompt_user_dialog
        character_state_db["data"]["conversation_type"] = type_conversation
        character_state_db["data"]["options_dialog"] = options_dialog
        if character_state_db["data"].get("locations_id"):
            locations_array = character_state_db["data"]["locations_id"]
            locations_array.append(location_id)
            character_state_db["data"]["locations_id"] = locations_array
        else:
            character_state_db["data"]["locations_id"] = [location_id]
        await db["state_glic"].update_one(
            {"_id": character_state_db["_id"]},
            {"$set": {
                "data": character_state_db["data"],
            }},
        )

        if type_conversation == "one_way":
            await generate_monologue_character(_game_id=game_id,
                                               _character_id=character_id,
                                               _user_id=user_id,
                                               _location_id=location_id,
                                               _state_game_id=state_game)
        if type_conversation == "two_way":
            await generate_conversation_character(_game_id=game_id,
                                                  _character_id=character_id,
                                                  _user_id=user_id,
                                                  _location_id=location_id,
                                                  _state_game_id=state_game)
        if type_conversation == "option_multiple":
            await generate_option_character(_game_id=game_id,
                                            _character_id=character_id,
                                            _user_id=user_id,
                                            _location_id=location_id,
                                            _state_game_id=state_game)

        if type_conversation == "open_question":
            await generate_open_question_character(_game_id=game_id,
                                                   _character_id=character_id,
                                                   _user_id=user_id,
                                                   _location_id=location_id,
                                                   _state_game_id=state_game)
        if type_conversation != "none" and type_conversation != "option_multiple" and type_conversation != "open_question":
            character_state_db = await db["state_glic"].find_one({"_id": character_state_db["_id"]})
            if character_state_db["data"]["interaction"]:
                for i in range(len(character_state_db["data"]["interaction"])):
                    if character_state_db["data"]["interaction"][i]["location_id"] == location_id and \
                            character_state_db["data"]["interaction"][i]["state_game"] == state_game:
                        for j in range(len(character_state_db["data"]["interaction"][i]["conversation"])):
                            character_state_db_ = await db["state_glic"].find_one({"element_id":
                                                                                       character_state_db["data"][
                                                                                           "interaction"][i][
                                                                                           "conversation"][j][
                                                                                           'id_character'],
                                                                                   "state": state_game})

                            try:
                                audio = await generate_audio(
                                    text=character_state_db["data"]["interaction"][i]["conversation"][j]["dialog"],
                                    voice_id=character_state_db_["data"]["voice_id"],
                                    user_id=user_id,
                                )

                                character_state_db["data"]["interaction"][i]["conversation"][j]["audio"] = audio
                            except Exception as e:
                                print(f"Error in generate voice service: {str(e)}")
                                pass

                await db["state_glic"].update_one(
                    {"_id": character_state_db["_id"]},
                    {"$set": {
                        "data": character_state_db["data"],
                    }}
                )
            return True

        if type_conversation == "option_multiple":

            character_state_db = await db["state_glic"].find_one({"_id": ObjectId(character_state_db["_id"])})
            if character_state_db["data"]["interaction"]:
                for i in range(len(character_state_db["data"]["interaction"])):
                    if character_state_db["data"]["interaction"][i]["location_id"] == location_id and \
                            character_state_db["data"]["interaction"][i]["state_game"] == state_game:
                        for j in range(len(
                                character_state_db["data"]["interaction"][i]["options_dialog"][
                                    "prompt_user_question"])):
                            character_state_db_ = await db["state_glic"].find_one(
                                {"element_id": character_state_db["data"]["interaction"][i]["options_dialog"][
                                    "prompt_user_question"][j]['id_character'], "state": state_game}
                            )
                            audio = await generate_audio(
                                text=
                                character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][
                                    j]["dialog"],
                                voice_id=character_state_db_["data"]["voice_id"],
                                user_id=user_id,
                            )
                            character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][j][
                                "audio"] = audio
                        for j in range(len(character_state_db["data"]["interaction"][i]["options_dialog"]["options"])):
                            character_state_db_ = await db["state_glic"].find_one(
                                {"element_id":
                                     character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j][
                                         'prompt_user_option'][
                                         'id_character'], "state": state_game}
                            )
                            audio = await generate_audio(
                                text=character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j][
                                    "prompt_user_option"]["dialog"],
                                voice_id=character_state_db_["data"]["voice_id"],
                                user_id=user_id,
                            )
                            character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j][
                                'prompt_user_option']["audio"] = audio

                            audio = await generate_audio(
                                text=character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j][
                                    "prompt_user_answer"]["dialog"],
                                voice_id=character_state_db["data"]["voice_id"],
                                user_id=user_id,
                            )
                            character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j][
                                'prompt_user_answer']["audio"] = audio

                await db["state_glic"].update_one(
                    {"_id": character_state_db["_id"]},
                    {"$set": {
                        "data": character_state_db["data"],
                    }}
                )
            return True
        if type_conversation == "open_question":

            character_state_db = await db["state_glic"].find_one({"_id": ObjectId(character_state_db["_id"])})
            if character_state_db["data"]["interaction"]:
                for i in range(len(character_state_db["data"]["interaction"])):
                    if character_state_db["data"]["interaction"][i]["location_id"] == location_id and \
                            character_state_db["data"]["interaction"][i]["state_game"] == state_game:
                        for j in range(len(character_state_db["data"]["interaction"][i]["options_dialog"][
                                               "prompt_user_question"])):
                            character_state_db_ = await db["state_glic"].find_one(
                                {"element_id": character_state_db["data"]["interaction"][i]["options_dialog"][
                                    "prompt_user_question"][j]['id_character'], "state": state_game}
                            )
                            audio = await generate_audio(
                                text=
                                character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][
                                    j]["dialog"],
                                voice_id=character_state_db_["data"]["voice_id"],
                                user_id=user_id,
                            )
                            character_state_db["data"]["interaction"][i]["options_dialog"]["prompt_user_question"][j][
                                "audio"] = audio

                        for j in range(len(character_state_db["data"]["interaction"][i]["options_dialog"]["options"])):
                            character_state_db_ = await db["state_glic"].find_one(
                                {"element_id":
                                     character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j][
                                         "prompt_user_answer"]['id_character'], "state": state_game}
                            )
                            audio = await generate_audio(
                                text=character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j][
                                    "prompt_user_answer"]["dialog"],
                                voice_id=character_state_db_["data"]["voice_id"],
                                user_id=user_id,
                            )
                            character_state_db["data"]["interaction"][i]["options_dialog"]["options"][j][
                                'prompt_user_answer']["audio"] = audio

                await db["state_glic"].update_one(
                    {"_id": character_state_db["_id"]},
                    {"$set": {
                        "data": character_state_db["data"],
                    }}
                )
        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generate voice service: {str(e)}")
        return False


async def generate_image_character_face(_character_id, _user_id, _state_game_id):
    try:
        _character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})

        character_state_db = await db["state_glic"].find_one(
            {"element_id": _character_id, "state": _state_game_id})

        image_face = await openai_generator.generate_image(
            prompt=f"Genera una imagen cuadrada en vista frontal de {character_state_db['data']['prompt_user']},"
                   " de ojos vivos, rasgos faciales exagerados y expresivos, de la "
                   "cintura para arriba, en estilo 3D Cel-shaded que Imita el aspecto "
                   "de los dibujos animados 2D, utilizando colores planos pero vivos y "
                   f"contornos marcados. Con fondo Blanco.",
            quality="hd",
            size="1024x1024",
            user_id=_user_id,
            type_generation="character_face",
        )
        # if character_db['image']:
        #     delete_image(character_db['image'])
        image_generated = upload_image(
            url_image=image_face,
            file_name=f"characters/{uuid4()}.jpg",
            size=(512, 512),
        )

        character_state_db["data"]["image"] = image_generated

        await db["state_glic"].update_one({"_id": character_state_db["_id"]},
                                          {"$set":
                                              {
                                                  "data": character_state_db["data"],
                                              }
                                          })

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in get images character service: {str(e)}")
        return False


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
            {"element_id": _character_id, "state": _state_game_id})

        response_type_genre = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Eres un identificador de genero y tipo de cuerpo de un personaje, "
                               "los generos son: man, woman o null, los tipos de cuerpo son: "
                               " adult, child o animal",
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
                {"role": "system", "content": "Eres un identificador de tipo de personaje"},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"nombre del personaje: {character_state_db['data']['name']} y descripción del personaje por "
                                    f"parte del usuario: {character_state_db['data']['prompt_user']}",
                        },
                        {
                            "type": "text",
                            "text": f"escoge uno de los siquientes tipos de personajes: {character_type_db}",
                        },
                    ],
                },
            ],
            model="gpt-4o-mini-2024-07-18",
            max_tokens=4096,
            response_format=SchemaSelectCharacterType,
            type_generation="detect_character_type",
            user_id=_user_id,
        )

        character_state_db["data"]["body_type"] = response_type_genre.body_type
        character_state_db["data"]["genre"] = response_type_genre.genre
        character_state_db["data"]["character_type"] = response_character_type.character_type

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


async def generate_character_description(_character_id, _user_id, _state_game_id):
    try:

        character_state_db = await db["state_glic"].find_one(
            {"element_id": _character_id, "state": _state_game_id})

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
    dialog: str = Field(..., example="dialog", description="dialog of the character and be a maximum of 15-30 words.")


class SchemaCharacterConversations(BaseModel):
    conversation: list[SchemaCharacterConversation] = Field(
        ..., example=[{"key": "value"}], description="conversation of the character"
    )


async def generate_conversation_character(_game_id, _character_id, _user_id, _location_id, _state_game_id):
    game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_principal_db = await db["character"].find_one(
        {"_id": ObjectId(game_db["character_principal"])}
    )
    character_other_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    element_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id}
    )
    language_detection = await generate_language_detection(element_state_db['data']['prompt_user_dialog'], _user_id)
    try:

        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f" You are a character dialogue extractor, according to a text where there is a conversation between two characters as follows. " +
                               "1. hello. how are you?" +
                               "2. hello, well how are you?" +
                               "where 1 is the main character and 2 is the other character, transform it to a"
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
                            "text": f"Conversation of the character: {element_state_db['data']['prompt_user_dialog']}",
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
        conversation_ = [{"id_character": dialog.id_character, "dialog": dialog.dialog, "audio": None} for dialog
                         in response.conversation]

        # await db["character"].update_one(
        #     {"_id": ObjectId(str(_character_db["_id"]))},
        #     {
        #         "$set": {
        #             "conversation": conversation_,
        #         }
        #     },
        # )

        interaction_exists = False

        if "interaction" not in element_state_db["data"]:
            element_state_db["data"]["interaction"] = []

        for interaction in element_state_db["data"]["interaction"]:
            if interaction["location_id"] == _location_id and interaction["state_game"] == _state_game_id:
                interaction["conversation"] = conversation_
                interaction["prompt_user_dialog"] = element_state_db["data"]["prompt_user_dialog"]
                interaction["type_conversation"] = "two_way"
                interaction_exists = True
                break

        if not interaction_exists:
            element_state_db["data"]["interaction"].append({
                "location_id": _location_id,
                "state_game": _state_game_id,
                "type_conversation": "two_way",
                "prompt_user_dialog": element_state_db["data"]["prompt_user_dialog"],
                "conversation": conversation_,
            })

        element_state_db["data"]["conversation"] = conversation_

        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {
                "$set": {
                    "data": element_state_db["data"],
                }
            })

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
                               "para saber si es una conversación o no, si tiene la siquiente estructura: "
                               "1. hello. how are you?" +
                               "2. hello, well how are you?" +
                               "es una conversación.",
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
            model="gpt-4o-mini-2024-07-18",
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


async def generate_option_character(_game_id, _character_id, _user_id, _location_id, _state_game_id):
    game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_principal_db = await db["character"].find_one(
        {"_id": ObjectId(game_db["character_principal"])}
    )
    character_other_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    element_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id}
    )
    language_detection = await generate_language_detection(element_state_db['data']['options_dialog'], _user_id)

    try:

        question_ic = await identify_prompt_conversation(
            element_state_db['data']['options_dialog']["prompt_user_question"], _user_id)

        if question_ic.is_conversation:
            response = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": f" You are a character dialogue extractor, according to a text where there is a conversation between two characters as follows. " +
                                   "1. hello. how are you?" +
                                   "2. hello, well how are you?" +
                                   "where 1 is the main character and 2 is the other character, transform it to a"
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
            conversation_ = [{"id_character": dialog.id_character, "dialog": dialog.dialog, "audio": None} for dialog
                             in response.conversation]
            element_state_db["data"]['options_dialog']['prompt_user_question'] = conversation_
        else:
            response = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": f" Correct spelling on the text of dialogue in the {language_detection} language. "
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
                {"id_character": str(character_other_db["_id"]), "dialog": dialog.dialog, "audio": None} for
                dialog
                in response.conversation]

            element_state_db["data"]['options_dialog']['prompt_user_question'] = conversation_

    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating character option (question): {str(e)}")
        return False

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

            conversation_ = {"id_character": str(character_principal_db["_id"]),
                             "dialog": element_state_db['data']['options_dialog']['options'][option][
                                 'prompt_user_option'], "audio": None}

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

            conversation_ = {"id_character": str(character_other_db["_id"]),
                             "dialog": element_state_db['data']['options_dialog']['options'][option][
                                 'prompt_user_answer'], "audio": None}

            element_state_db["data"]['options_dialog']['options'][option]['prompt_user_answer'] = conversation_


        except Exception as e:
            print(f"Error in generating character option (answer): {str(e)}")
            return False

    interaction_exists = False

    if "interaction" not in element_state_db["data"]:
        element_state_db["data"]["interaction"] = []

    for interaction in element_state_db["data"]["interaction"]:
        if interaction["location_id"] == _location_id and interaction["state_game"] == _state_game_id:
            interaction["options_dialog"] = element_state_db["data"]["options_dialog"]
            interaction["prompt_user_dialog"] = None
            interaction["type_conversation"] = "option_multiple"
            interaction_exists = True
            break

    if not interaction_exists:
        element_state_db["data"]["interaction"].append({
            "location_id": _location_id,
            "state_game": _state_game_id,
            "type_conversation": "option_multiple",
            "prompt_user_dialog": None,
            "options_dialog": element_state_db["data"]["options_dialog"],
        })

    try:

        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {
                "$set": {
                    "data": element_state_db["data"],
                }
            })

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating character conversation: {str(e)}")
        return False


#
async def generate_open_question_character(_game_id, _character_id, _user_id, _location_id, _state_game_id):
    game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_principal_db = await db["character"].find_one(
        {"_id": ObjectId(game_db["character_principal"])}
    )
    character_other_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    element_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id}
    )
    language_detection = await generate_language_detection(element_state_db['data']['options_dialog'], _user_id)

    try:

        question_ic = await identify_prompt_conversation(
            element_state_db['data']['options_dialog']["prompt_user_question"], _user_id)

        if question_ic.is_conversation:
            response = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": f" You are a character dialogue extractor, according to a text where there is a conversation between two characters as follows. " +
                                   "1. hello. how are you?" +
                                   "2. hello, well how are you?" +
                                   "where 1 is the main character and 2 is the other character, transform it to a"
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
            conversation_ = [{"id_character": dialog.id_character, "dialog": dialog.dialog, "audio": None} for dialog
                             in response.conversation]
            element_state_db["data"]['options_dialog']['prompt_user_question'] = conversation_
        else:
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

            conversation_ = [
                {"id_character": str(character_other_db["_id"]), "dialog": element_state_db['data']['options_dialog']['prompt_user_question'], "audio": None}]

            element_state_db["data"]['options_dialog']['prompt_user_question'] = conversation_

    except Exception as e:
        print(f"Error in generating character option (question): {str(e)}")
        return False

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

            conversation_ = {"id_character": str(character_other_db["_id"]),
                             "dialog": element_state_db['data']['options_dialog']['options'][option][
                                 'prompt_user_answer'], "audio": None}

            element_state_db["data"]['options_dialog']['options'][option]['prompt_user_answer'] = conversation_


        except Exception as e:
            print(f"Error in generating character option (answer): {str(e)}")
            return False

    interaction_exists = False

    if "interaction" not in element_state_db["data"]:
        element_state_db["data"]["interaction"] = []

    for interaction in element_state_db["data"]["interaction"]:
        if interaction["location_id"] == _location_id and interaction["state_game"] == _state_game_id:
            interaction["options_dialog"] = element_state_db["data"]["options_dialog"]
            interaction["prompt_user_dialog"] = None
            interaction["type_conversation"] = "open_question"
            interaction_exists = True
            break

    if not interaction_exists:
        element_state_db["data"]["interaction"].append({
            "location_id": _location_id,
            "state_game": _state_game_id,
            "type_conversation": "open_question",
            "prompt_user_dialog": None,
            "options_dialog": element_state_db["data"]["options_dialog"],
        })

    try:

        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {
                "$set": {
                    "data": element_state_db["data"],
                }
            })

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generating character conversation: {str(e)}")
        return False


async def generate_monologue_character(_game_id, _character_id, _user_id, _location_id, _state_game_id):
    # game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_other_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    character_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id})
    try:
        # if not character_other_db.get("prompt_user_dialog"):
        #     character_other_db["prompt_user_dialog"] = game_db["history"]

        language_detection = await generate_language_detection(character_state_db["data"]['prompt_user_dialog'],
                                                               _user_id)

        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f" Correct spelling on the text of dialogue in the {language_detection} language. "
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

        conversation_ = [{"id_character": str(character_other_db["_id"]), "dialog": dialog.dialog, "audio": None} for
                         dialog
                         in response.conversation]

        interaction_exists = False

        if "interaction" not in character_state_db["data"]:
            character_state_db["data"]["interaction"] = []

        for interaction in character_state_db["data"]["interaction"]:
            if interaction["location_id"] == _location_id and interaction["state_game"] == _state_game_id:
                interaction["conversation"] = conversation_
                interaction["prompt_user_dialog"] = character_state_db["data"]["prompt_user_dialog"]
                interaction["type_conversation"] = "one_way"
                interaction_exists = True
                break

        if not interaction_exists:
            character_state_db["data"]["interaction"].append({
                "location_id": _location_id,
                "state_game": _state_game_id,
                "type_conversation": "one_way",
                "prompt_user_dialog": character_state_db["data"]["prompt_user_dialog"],
                "conversation": conversation_,
            })

        await db["state_glic"].update_one(
            {"_id": character_state_db["_id"]},
            {
                "$set": {
                    "data": character_state_db["data"],
                }
            })

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


async def async_generate_character_task(_character_id,
                                        _user_id,
                                        _task_id,
                                        _location_id,
                                        _state_game_id,
                                        _game_id, ):
    await update_task_service(_id=_task_id, _status="pending")
    character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    if not character_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message=f"Error can't find character with id {_character_id}",
        )
        return f"Error can't find character with id {_character_id}"
    response_description = await generate_character_description(_character_id=_character_id,
                                                                _user_id=_user_id,
                                                                _state_game_id=_state_game_id)
    if not response_description:
        await update_task_service(
            _id=_task_id, _status="failed", _message="Error in generate character description"
        )
        return "Error in generate character description"
    response_body_type = await generate_character_body_type(
        _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
    )
    if not response_body_type:
        await update_task_service(
            _id=_task_id, _status="failed", _message="Error in generate character body type"
        )
        return "Error in generate character body type"
    response_image = await generate_image_character_face(
        _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
    )
    if not response_image:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Error in generate image character face service",
        )
        return "Error in generate image character face service "

    element_state_db = await db["state_glic"].find_one(
        {"element_id": _character_id, "state": _state_game_id}
    )

    voice_generated = await generate_voice_character(game_id=_game_id,
                                                     character_id=_character_id,
                                                     user_id=_user_id,
                                                     state_game=_state_game_id,
                                                     location_id=_location_id,
                                                     type_conversation=element_state_db["data"]["conversation_type"],
                                                     prompt_user_dialog=element_state_db["data"]["prompt_user_dialog"],
                                                     options_dialog=element_state_db["data"]["options_dialog"])

    if not voice_generated:
        await update_task_service(
            _id=_task_id, _status="failed", _message="Error voice not generated"
        )
        return "Error voice not generated"

    await update_task_service(
        _id=_task_id, _status="completed", _message="Character generate successfully"
    )
    return "Character generate successfully"


async def async_update_character_task(_character_id, _user_id, _task_id, _game_id, _updated_data, _updated_voice,
                                      _state_game_id, _location_id):
    await update_task_service(_id=_task_id, _status="pending")
    if _updated_data:
        character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
        if not character_db:
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
            await update_task_service(
                _id=_task_id, _status="failed", _message="Error in generate character description"
            )
            return "Error in generate character description"
        response_body_type = await generate_character_body_type(
            _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
        )
        if not response_body_type:
            await update_task_service(
                _id=_task_id, _status="failed", _message="Error in generate character body type"
            )
            return "Error in generate character body type"
        response_image = await generate_image_character_face(
            _character_id=_character_id, _user_id=_user_id, _state_game_id=_state_game_id
        )
        if not response_image:
            await update_task_service(
                _id=_task_id,
                _status="failed",
                _message="Error in generate image character face service",
            )
            return "Error in generate image character face service "

    if _updated_voice:
        element_state_db = await db["state_glic"].find_one(
            {"element_id": _character_id, "state": _state_game_id}
        )

        voice_generated = await generate_voice_character(game_id=_game_id,
                                                         character_id=_character_id,
                                                         user_id=_user_id,
                                                         state_game=_state_game_id,
                                                         options_dialog=element_state_db["data"]["options_dialog"],
                                                         location_id=_location_id,
                                                         type_conversation=element_state_db["data"][
                                                             "conversation_type"],
                                                         prompt_user_dialog=element_state_db["data"][
                                                             "prompt_user_dialog"])
        if not voice_generated:
            await update_task_service(
                _id=_task_id, _status="failed", _message="Error voice not generated"
            )
            return "Error voice not generated"

    await update_task_service(
        _id=_task_id, _status="completed", _message="Character updated successfully"
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
