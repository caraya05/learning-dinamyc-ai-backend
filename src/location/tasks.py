import traceback
from uuid import uuid4

from bson import ObjectId

from pydantic import BaseModel
from pydantic import Field

from core.database import db

from gpt_ai.utils import openai_generator

from prompt.services import get_prompt_by_category_service
from sound.services import get_sounds_service

from task.services import update_task_service

from utils import upload_image


class SchemaLocationEnvironment(BaseModel):
    fog_level: str = Field(
        ...,
        title="Fog Level",
        description="(none, medium, high) - The level of fog in the location",
    )
    light_mode: str = Field(
        ...,
        title="Light Mode",
        description="(cloudy, directSun, shade, blueSky) - The light mode in the location",
    )
    light_intensity: str = Field(
        ...,
        title="Light Intensity",
        description="(low, high) - The light intensity in the location",
    )


async def generate_environment_location(_location_id: str, _user_id: str, _state_game_id):
    try:
        # location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})
        # response_analyze = await openai_generator.generate_gpt(
        #     content_prompt=[
        #         {
        #             "role": "system",
        #             "content": f"Analiza la imagen de la locacion y describe el ambiente en la imagen,"
        #                        f"las opciones de animales son dog ,bird ,squirrel, firefly",
        #         },
        #         {
        #             "role": "user",
        #             "content": [
        #                 {"type": "image_url", "image_url": {"url": location_db["image"]}},
        #             ],
        #         },
        #     ],
        #     model="gpt-4o-mini",
        #     max_tokens=4096,
        #     response_format=SchemaLocationEnvironment,
        #     type_generation="generate_environment_location",
        #     user_id=_user_id,
        # )
        #
        # location_environment = response_analyze.dict()
        # location_environment["animals"] = []

        element_state_db = await db["state_glic"].find_one({"element_id": _location_id, "state": _state_game_id})

        location_environment = {
            "fog_level": "none",
            "light_mode": "directSun",
            "light_intensity": "high",
            "animals": []
        }

        # await db['location'].update_one(
        #     {"_id": ObjectId(_location_id)}, {"$set": {"environment": location_environment}}
        # )

        element_state_db["data"]["environment"] = location_environment

        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {"$set": {"data": element_state_db["data"]}},
        )

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generate environment location: {e}")
        return False


class SchemaLocationDescription(BaseModel):
    description: str = Field(
        ...,
        title="Description",
        description="general description of the place, theme, appearance",
    )
    description_floor: str = Field(
        ...,
        title="Description Floor",
        description="detailed description of the apartment next to a wall"
    )


class SchemaLocationSound(BaseModel):
    sound_id: str = Field(
        ...,
        title="Sound ID",
        description="Sound ID that most closely resembles the location"
    )


async def generate_location_description(_location_id: str, _user_id: str, state_game_id):
    try:
        location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})

        element_state_db = await db["state_glic"].find_one({"element_id": _location_id, "state": state_game_id})

        prompt_db_location_place = await get_prompt_by_category_service("location_place")
        prompt_db_location_place["description"] = prompt_db_location_place["description"].replace(
            "{{PromptUserLocation}}", element_state_db["data"]["prompt_user"]
        )
        response_description = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Eres un personaje en un videojuego de realidad virtual. Estás en un lugar nuevo"
                               " y necesitas describirlo para que otros jugadores puedan encontrarlo.",
                },
                {"role": "user", "content": f"{prompt_db_location_place['description']}"},
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format=SchemaLocationDescription,
            type_generation="generate_description_location",
            user_id=_user_id,
        )

        element_state_db["data"]["description"] = response_description.description
        element_state_db["data"]["description_floor"] = response_description.description_floor

        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]},
            {"$set": {"data": element_state_db["data"]}},
        )

        # await db['location'].update_one(
        #     {"_id": ObjectId(_location_id)},
        #     {
        #         "$set": {
        #             "description": response_description.description,
        #             "description_floor": response_description.description_floor,
        #         }
        #     },
        # )
        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generate location description: {e}")
        return False


async def identify_location_sound(_location_id: str, _user_id: str, _state_game_id):
    location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})
    element_state_db = await db["state_glic"].find_one({"element_id": _location_id, "state": _state_game_id})
    try:
        sounds_db = await get_sounds_service()
        str_sounds = ""
        for sound in sounds_db:
            str_sounds += f"_id: {sound['_id']} - {sound['name']}, "
        response_sound = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "eres un identicador de sonidos para locaciones, con la siquiente image y descripcion de una locacion, escoje uno de los "
                               "sonidos de la lista que se escucharia en este lugar, no incluyas o crees sonidos que no esten en la lista.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Listado de sonidos: {str_sounds}"},
                        {
                            "type": "text",
                            "text": f"descripcion de la locacion : {element_state_db['data']['description']}",
                        },
                    ],
                }
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format=SchemaLocationSound,
            type_generation="identify_sound_by_location",
            user_id=_user_id,
        )
        # await db['location'].update_one(
        #     {"_id": ObjectId(_location_id)}, {"$set": {"sound": response_sound.sound_id}}
        # )

        element_state_db["data"]["sound"] = response_sound.sound_id

        await db["state_glic"].update_one(
            {"_id": ObjectId(element_state_db["_id"])},
            {"$set": {"data": element_state_db["data"]}},
        )

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in identify location sound: {e}")
        return False


class SchemaLocationImage(BaseModel):
    response: str = Field(
        ...,
        title="Response",
        description="Response of the image generated for the location",
    )


async def generate_location_image(_location_id: str, _user_id: str, _state_game_id: str):
    try:
        location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})

        element_state_db = await db["state_glic"].find_one({"element_id": _location_id, "state": _state_game_id})

        prompt_db_image_location = await get_prompt_by_category_service("location_image")
        content_prompt = f'{prompt_db_image_location["description"]}, {element_state_db["data"]["description"]}'
        new_prompt = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "reestructure el prompt para generar la imagen con estilo 3D volumétrico en vista"
                               " isométrica para un videojuego RPG, con fondo de color solido.",
                },
                {
                    "role": "user",
                    "content": content_prompt
                },
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format=SchemaLocationImage,
            type_generation="text generation location image",
            user_id=_user_id,
        )

        validate_prompt = await openai_generator.moderation_text(text=new_prompt.response, user_id=_user_id)
        if validate_prompt:
            return False, "Prompt not allowed"

        image_location = await openai_generator.generate_image(
            prompt=new_prompt.response,
            quality="hd",
            size="1792x1024",
            user_id=_user_id,
            type_generation="generate_image_location",
        )
        image_generated = upload_image(
            url_image=image_location,
            file_name=f"characters/{uuid4()}.jpg",
            size=(2436, 1372),
        )
        # await db['location'].update_one(
        #     {"_id": ObjectId(_location_id)}, {"$set": {"image": image_generated}}
        # )

        element_state_db["data"]["image"] = image_generated

        await db["state_glic"].update_one({
            "_id": element_state_db["_id"]
        }, {
            "$set": {
                "data": element_state_db["data"]
            }
        })

        return True, "Image generated successfully"
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generate location image: {e}")
        return False, "Error in generate location image"


async def async_generate_location_task(_location_id: str, _user_id: str, _task_id: str, _state_game_id: str):
    await update_task_service(_id=_task_id, _status="pending")
    location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})
    if not location_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message=f"Error can't find location with id {_location_id}",
        )
        return f"Error can't find location with id {_location_id}"
    response_description = await generate_location_description(_location_id, _user_id, _state_game_id)
    if not response_description:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Error in generate location description service.",
        )
        return "Error in generate location description service."
    response_sound = await identify_location_sound(_location_id, _user_id, _state_game_id)
    if not response_sound:
        await update_task_service(
            _id=_task_id, _status="failed", _message="Error in identify location sound service."
        )
        return "Error in identify location sound service."
    response_image, message = await generate_location_image(_location_id, _user_id, _state_game_id)
    if not response_image:
        await update_task_service(
            _id=_task_id, _status="failed", _message=message, _status_updated=1
        )
        return message
    response_environment = await generate_environment_location(_location_id, _user_id, _state_game_id)
    if not response_environment:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Error in generate environment location service.",
        )
        return "Error in generate environment location service."
    await update_task_service(
        _id=_task_id, _status="completed", _message="Location generate successfully"
    )
    return "Location generate successfully"


async def async_generate_image_location_task(_location_id: str, _user_id: str, _task_id: str):
    await update_task_service(_id=_task_id, _status="pending")
    location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})
    if not location_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message=f"Error can't find location with id {_location_id}",
        )
        return f"Error can't find location with id {_location_id}"
    response_image, message = await generate_location_image(_location_id, _user_id)
    if not response_image:
        await update_task_service(
            _id=_task_id, _status="failed", _message=message, _status_updated=1
        )
        return message
    response_environment = await generate_environment_location(_location_id, _user_id)
    if not response_environment:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Error in generate environment location service.",
        )
        return "Error in generate environment location service."
    await update_task_service(
        _id=_task_id, _status="completed", _message="Location image generate successfully"
    )
    return "Location image generate successfully"
