from uuid import uuid4

from bson import ObjectId
from pydantic import BaseModel, Field

from character.schemas import SchemaCreateCharacter
from character.utils import get_extra_data_character_ai

from core.database import db

from gpt_ai.utils import openai_generator
from task.services import update_task_service

from utils import upload_image


async def generate_image_character_face(_character_db,
                                        _user_id):
    try:

        if _character_db["description_shoulder_up"]:
            description_character = _character_db['description_shoulder_up']
        else:
            description_character = _character_db['prompt_user']

        image_face = await  openai_generator.generate_image(
            prompt=f"Genera una imagen cuadrada en vista frontal de {description_character},"
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

        # customizes_db = []
        # if character_db['body_type'] in ["woman", "man", "MAN", "WOMAN"]:
        #     customizes_db, count_customize = await get_customize_by_type_character_service(character_db['body_type'],
        #                                                                                    "hair")
        #
        # prompt_content_extra_data = [
        #     {
        #         "role": "system",
        #         "content": "Describe a detalle el personaje con la siquiente imagen y la descrpccion del personaje,"
        #                    " extrae los colores de la piel, cabello, ojos, labios, zapatos, pantalones y camisa."
        #                    "en dado caso que una prenda no este visible colocar un color adorde a los demas colores,"
        #                    "en dado caso de que la imagen no tenga colores colocar colores que se asemejen a la imagen."
        #                    "en dado caso no se puedan de terminar los colores colocar colores asocidos a la descripcion.",
        #     },
        #     {
        #         "role": "assistant",
        #         "content": [
        #             {
        #                 "type": "text",
        #                 "text": f"tipos de peinados: {customizes_db}",
        #             },
        #         ],
        #     },
        #     {
        #         "role": "user",
        #         "content": [
        #             {
        #                 "type": "text",
        #                 "text": f"Descripcion del personaje: {character_db['description']}",
        #             },
        #             {"type": "image_url", "image_url": {"url": character_db["image"]}},
        #         ],
        #     }
        # ]
        #
        # extra_data = get_extra_data_character_ai(prompt_content_extra_data)
        #
        # character_db['extra_data'] = extra_data["extra_data"]
        #
        # if character_db['body_type'] in ["woman", "man", "MAN", "WOMAN"]:
        #     customize_character = get_customize_by_character(
        #         customizes_db, character_db['description']
        #     )
        #
        #     character_db['extra_data']["type_combing"] = customize_character["reference_ui"]
        #
        # await db["character"].update_one({"_id": ObjectId(character_id)}, {"$set": character_db})

        return True
    except Exception as e:
        print(f"Error in get images character service: {str(e)}")
        return False


class SchemaSelectBodyType(BaseModel):
    body_type: str = Field(..., example="body_type",
                           description="body type of the character according to the description")


class SchemaCharacterCreate(BaseModel):
    description: str = Field(..., example="description",
                             description="description to identify the colors that the character has, it is necessary to know the"
                                         " colors of clothes, shoes, hair, skin, eyes and lips")
    description_shoulder_up: str = Field(..., example="description_shoulder_up",
                                         description="string (15-word description cut from the head to the waist of the character, to generate an image of the character")

    description_game: str = Field(..., example="description_game",
                                  description="description of the character for the game")


async def get_character_body_type(_character_db, _body_type, _user_id):
    try:
        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Selecciona el tipo de cuerpo del personaje entre hombre o mujer"
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": f"description: {_character_db['description']}"},
                                {"type": "text", "text": f"Name: {_character_db['name']}"},
                                {"type": "text", "text": f"Body type: {_body_type}"}]
                },
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format=SchemaSelectBodyType,
            type_generation="create_description_character",
            user_id=_user_id
        )

        await db["character"].update_one({"_id": ObjectId(_character_db["_id"])},
                                         {"$set": {"body_type": response["body_type"]}})

        return True
    except Exception as e:
        print(f"Error in get character body type service: {str(e)}")
        return False


async def get_character_description(_character_db,
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


async def async_create_character_task(_character_id,
                                      _body_type,
                                      _user_id,
                                      _task_id):
    character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})

    if not character_db:
        await db["task"].update_one({"task_id": _task_id},
                                    {"$set": {"status": "error",
                                              "message": f"Can't find character with id {_character_id}"}})
        return f"Can't find character with id {_character_id}"
    message_response = ""
    response_description = await get_character_description(character_db,
                                                           _user_id=_user_id)
    if not response_description:
        message_response += " Error in get character description service "
    response_body_type = await get_character_body_type(character_db, _body_type,
                                                       _user_id=_user_id)
    if not response_body_type:
        message_response += " Error in get character body type service "
    response_image = await generate_image_character_face(_character_db=character_db,
                                                         _user_id=_user_id)
    if not response_image:
        message_response += " Error in generate image character face service "

    # if response_body_type["body_type"] in ["woman", "man", "MAN", "WOMAN"]:
    #     customizes_db, count_customize = await get_customize_by_type_character_service(response_body_type["body_type"],
    #                                                                                    "hair")
    if message_response != "":
        await db["task"].update_one({"task_id": _task_id},
                                    {"$set": {"status": "error",
                                              "message": message_response}})
        return message_response

    await db["task"].update_one({"task_id": _task_id},
                                {"$set": {"status": "completed",
                                          "message": "Character created successfully"}})

    return "Character created successfully"


async def async_update_character_task(_character_id,
                                      _body_type,
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
    response_body_type = await get_character_body_type(character_db, _body_type,
                                                       _user_id=_user_id)
    if not response_body_type:
        message_response += " Error in get character body type service "
    response_description = await get_character_description(character_db,
                                                           _user_id=_user_id)
    if not response_description:
        message_response += " Error in get character description service "
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
                                          "message": "Character updated successfully"}})

    return "Character updated successfully"
