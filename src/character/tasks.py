import random
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


async def generate_voice_character(game_id, character_id: str, user_id: str):
    try:
        character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
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
                    "content": f"Descripción del personaje: {character_db['description']}"
                               f"Genero del personaje: {character_db['genre']}",
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
        if character_db["conversation_type"] == "one_way":
            await generate_monologue_character(_game_id=game_id, _character_db=character_db,
                                               _user_id=user_id)
        if character_db["conversation_type"] == "two_way":
            await generate_conversation_character(_game_id=game_id, _character_db=character_db,
                                                  _user_id=user_id)
        if character_db["conversation_type"] != "none":
            character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
            if character_db["conversation"]:
                for conversation in character_db["conversation"]:
                    if conversation["dialog"]:
                        character_dialog_db = await db["character"].find_one(
                            {"_id": ObjectId(conversation['id_character'])}
                        )
                        audio = await generate_audio(
                            text=conversation["dialog"],
                            voice_id=character_dialog_db["voice_id"],
                            user_id=user_id,
                        )
                        conversation["audio"] = audio
                await db["character"].update_one(
                    {"_id": ObjectId(character_id)}, {"$set": {"conversation": character_db["conversation"]}}
                )
        return True
    except Exception as e:
        print(f"Error in generate voice service: {str(e)}")
        return False


async def generate_image_character_face(_character_db, _user_id):
    try:
        _character_db = await db["character"].find_one({"_id": _character_db["_id"]})
        image_face = await openai_generator.generate_image(
            prompt=f"Genera una imagen cuadrada en vista frontal de {_character_db['prompt_user']},"
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
        await db["character"].update_one(
            {"_id": ObjectId(_character_db["_id"])}, {"$set": {"image": image_generated}}
        )
        return True
    except Exception as e:
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


async def generate_character_body_type(_character_db, _user_id):
    try:
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
                            "text": f"nombre del personaje: {_character_db['name']} y descripción del personaje por "
                                    f"parte del usuario: {_character_db['prompt_user']}",
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
                            "text": f"nombre del personaje: {_character_db['name']} y descripción del personaje por "
                                    f"parte del usuario: {_character_db['prompt_user']}",
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

        await db["character"].update_one(
            {"_id": ObjectId(_character_db["_id"])},
            {
                "$set": {
                    "body_type": response_type_genre.body_type,
                    "genre": response_type_genre.genre,
                    "character_type": response_character_type.character_type,
                }
            },
        )

        return True
    except Exception as e:
        print(f"Error in get character body type service: {str(e)}")
        return False


async def generate_character_description(_character_db, _user_id):
    try:
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
                            "text": f"Name character: {_character_db['prompt_user_dialog']}",
                        },
                        {
                            "type": "text",
                            "text": f"Description of the role of character in history: {_character_db['prompt_user_dialog']}",
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

        await db["character"].update_one(
            {"_id": ObjectId(_character_db["_id"])},
            {
                "$set": {
                    "description": response.description,
                    "description_shoulder_up": response.description_shoulder_up,
                }
            },
        )

        return True
    except Exception as e:
        print(f"Error in get character description service: {str(e)}")
        return False


class SchemaCharacterConversation(BaseModel):
    id_character: str = Field(..., example="id_character", description="id of the character")
    dialog: str = Field(..., example="dialog", description="dialog of the character and be a maximum of 15-30 words.")


class SchemaCharacterConversations(BaseModel):
    conversation: list[SchemaCharacterConversation] = Field(
        ..., example=[{"key": "value"}], description="conversation of the character"
    )


async def generate_conversation_character(_game_id, _character_db, _user_id):
    game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_principal_db = await db["character"].find_one(
        {"_id": ObjectId(game_db["character_principal"])}
    )
    character_other_db = await db["character"].find_one({"_id": ObjectId(str(_character_db["_id"]))})
    language_detection = await generate_language_detection(character_other_db['prompt_user_dialog'], _user_id)
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
                            "text": f"Conversation of the character: {character_other_db['prompt_user_dialog']}",
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

        await db["character"].update_one(
            {"_id": ObjectId(str(_character_db["_id"]))},
            {
                "$set": {
                    "conversation": conversation_,
                }
            },
        )

        return True
    except Exception as e:
        print(f"Error in generating character conversation: {str(e)}")
        return False


async def generate_monologue_character(_game_id, _character_db, _user_id):
    # game_db = await db["game"].find_one({"_id": ObjectId(_game_id)})
    character_other_db = await db["character"].find_one({"_id": ObjectId(_character_db["_id"])})
    try:
        # if not character_other_db.get("prompt_user_dialog"):
        #     character_other_db["prompt_user_dialog"] = game_db["history"]

        language_detection = await generate_language_detection(character_other_db['prompt_user_dialog'], _user_id)

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
                            "text": f"character dialog: {character_other_db['prompt_user_dialog']}"
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

        conversation_ = [{"id_character": str(_character_db["_id"]), "dialog": dialog.dialog, "audio": None} for dialog
                         in response.conversation]

        await db["character"].update_one(
            {"_id": ObjectId(_character_db["_id"])},
            {
                "$set": {
                    "conversation": conversation_,
                }
            },
        )

        return True
    except Exception as e:
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
                    "content": f"Texto: {_text}",
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
        print(f"Error in generating language detection: {str(e)}")
        return "english"


async def async_generate_character_task(_character_id, _user_id, _task_id):
    await update_task_service(_id=_task_id, _status="pending")
    character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    if not character_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message=f"Error can't find character with id {_character_id}",
        )
        return f"Error can't find character with id {_character_id}"
    response_description = await generate_character_description(
        _character_db=character_db, _user_id=_user_id
    )
    if not response_description:
        await update_task_service(
            _id=_task_id, _status="failed", _message="Error in generate character description"
        )
        return "Error in generate character description"
    response_body_type = await generate_character_body_type(
        _character_db=character_db, _user_id=_user_id
    )
    if not response_body_type:
        await update_task_service(
            _id=_task_id, _status="failed", _message="Error in generate character body type"
        )
        return "Error in generate character body type"
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
        _id=_task_id, _status="completed", _message="Character generate successfully"
    )
    return "Character generate successfully"


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
