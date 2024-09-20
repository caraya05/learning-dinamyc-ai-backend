from uuid import uuid4

from bson import ObjectId

from pydantic import BaseModel
from pydantic import Field

from core.database import db

from gpt_ai.utils import openai_generator

from task.services import update_task_service

from utils import upload_image


async def generate_image_character_face(_character_db,
                                        _user_id):
    try:
        image_face = await  openai_generator.generate_image(
            prompt=f"Genera una imagen cuadrada en vista frontal de {_character_db['description_shoulder_up']},"
                   " de ojos vivos, rasgos faciales exagerados y expresivos, de la "
                   "cintura para arriba, en estilo 3D Cel-shaded que Imita el aspecto "
                   "de los dibujos animados 2D, utilizando colores planos pero vivos y "
                   f"contornos marcados. Con fondo Blanco. el sexo del personaje es {_character_db['body_type']}",
            quality="hd",
            size="1024x1024",
            user_id=_user_id,
            type_generation="character_face"
        )
        # if character_db['image']:
        #     delete_image(character_db['image'])
        image_generated = upload_image(
            url_image=image_face,
            file_name=f"characters/{uuid4()}.jpg",
            size=(512, 512),
        )
        await db["character"].update_one({"_id": ObjectId(_character_db["_id"])},
                                         {"$set": {"image": image_generated}})
        return True
    except Exception as e:
        print(f"Error in get images character service: {str(e)}")
        return False


class SchemaSelectBodyType(BaseModel):
    body_type: str = Field(..., example="body_type",
                           description="body type of the character according to the description")
    genre: str = Field(..., example="genre",
                       description="genre of the character according to the description")


class SchemaCharacterCreate(BaseModel):
    description: str = Field(..., example="description",
                             description="description to identify the colors that the character has, it is necessary "
                                         "to know the colors of clothes, shoes, hair, skin, eyes and lips")
    description_shoulder_up: str = Field(..., example="description_shoulder_up",
                                         description="string (15-word description cut from the head to the waist of"
                                                     " the character, to generate an image of the character")

    description_game: str = Field(..., example="description_game",
                                  description="description of the character for the game")


class SchemaSelectCharacterType(BaseModel):
    type_body: str = Field(..., example="type_body",
                           description="type of body of the character according to the description")
    genre: str = Field(..., example="genre",
                       description="genre of the character according to the description")


async def generate_character_body_type(_character_db, _user_id):
    try:
        response_type_genre = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Eres un identificador de genero y tipo de cuerpo de un personaje, "
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
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format=SchemaSelectBodyType,
            type_generation="detect_body_type__genre",
            user_id=_user_id
        )
        character_type_db = await db["character_type"].find(
            {"body_type": response_type_genre["body_type"], "genre": response_type_genre["genre"]}).to_list(None)

        response_character_type = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Eres un identificador de tipo de personaje"
                },
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
                        }
                    ],
                },
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format=SchemaSelectCharacterType,
            type_generation="detect_character_type",
            user_id=_user_id
        )

        await db["character"].update_one({"_id": ObjectId(_character_db["_id"])},
                                         {"$set": {"body_type": response_type_genre["type_body"],
                                                   "genre": response_type_genre["genre"],
                                                   "character_type": response_character_type["character_type"]}})

        return True
    except Exception as e:
        print(f"Error in get character body type service: {str(e)}")
        return False


async def generate_character_description(_character_db,
                                         _user_id):
    try:
        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "create 3 descriptions for the character, one for the character description, one for the "
                               "game description and one for the description for the generation of a picture of the character."
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": f"Description by user: {_character_db['prompt_user']}"}]
                },
            ],
            model="gpt-4o",
            max_tokens=4096,
            response_format=SchemaCharacterCreate,
            user_id=_user_id,
            type_generation="create_description_character"
        )

        await db["character"].update_one({"_id": ObjectId(_character_db["_id"])},
                                         {"$set": {"description": response["description"],
                                                   "description_game": response["description_game"],
                                                   "description_shoulder_up": response["description_shoulder_up"]}})

        return True
    except Exception as e:
        print(f"Error in get character description service: {str(e)}")
        return False


async def async_generate_character_task(_character_id,
                                        _user_id,
                                        _task_id):
    await update_task_service(
        _id=_task_id,
        _status="pending"
    )

    character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})

    if not character_db:
        await db["task"].update_one({"_id": _task_id},
                                    {"$set": {"status": "error",
                                              "message": f"Can't find character with id {_character_id}"}})
        return f"Can't find character with id {_character_id}"
    message_response = ""
    response_description = await generate_character_description(_character_db=character_db,
                                                                _user_id=_user_id)
    if not response_description:
        message_response += " Error in get character description service "
    response_body_type = await generate_character_body_type(_character_db=character_db,
                                                            _user_id=_user_id)
    if not response_body_type:
        message_response += " Error in get character body type service "
    response_image = await generate_image_character_face(_character_db=character_db,
                                                         _user_id=_user_id)
    if not response_image:
        message_response += " Error in generate image character face service "
    if message_response != "":
        await db["task"].update_one({"_id": _task_id},
                                    {"$set": {"status": "error",
                                              "message": message_response}})
        return message_response

    await db["task"].update_one({"_id": _task_id},
                                {"$set": {"status": "completed",
                                          "message": "Character created successfully"}})

    return "Character generate successfully"


async def async_generate_image_character_task(_character_id,
                                              _user_id,
                                              _task_id):
    await update_task_service(
        _id=_task_id,
        _status="pending"
    )
    character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    if not character_db:
        await db["task"].update_one({"task_id": _task_id},
                                    {"$set": {"status": "error",
                                              "message": f"Can't find character with id {_character_id}"}})
        return f"Can't find character with id {_character_id}"
    message_response = ""
    response_image = await generate_image_character_face(_character_db=character_db,
                                                         _user_id=_user_id)
    if not response_image:
        message_response += " Error in generate image character face service "
    if message_response != "":
        await db["task"].update_one({"task_id": _task_id},
                                    {"$set": {"status": "error",
                                              "message": message_response}})
        return message_response
    await db["task"].update_one({"task_id": _task_id},
                                {"$set": {"status": "completed",
                                          "message": "Character created successfully"}})
    return "Character image generate successfully"
