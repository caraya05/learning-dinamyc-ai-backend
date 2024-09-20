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
    fog_level: str = Field(...,
                           title="Fog Level",
                           description="(none, medium, high) - The level of fog in the location",
                           max_length=50)
    light_mode: str = Field(...,
                            title="Light Mode",
                            description="(cloudy, directSun, shade, blueSky) - The light mode in the location",
                            max_length=50)
    light_intensity: str = Field(...,
                                 title="Light Intensity",
                                 description="(low, high) - The light intensity in the location",
                                 max_length=50)
    animals: list = Field(...,
                          title="Animals",
                          description="['dog','bird','squirrel','firefly'] - The animals in the location, choose "
                                      "only one or none if not necessary.",
                          )


async def generate_environment_location(_location_id: str, _user_id: str):
    try:
        location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})
        response_analyze = openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f"Analiza la imagen de la locacion y describe el ambiente en la imagen"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": location_db["image"]}},
                    ],
                }
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format=SchemaLocationEnvironment,
            type_generation="generate_environment_location",
            user_id=_user_id
        )

        await db['location'].update_one({"_id": ObjectId(_location_id)},
                                        {"$set": {"environment": response_analyze.dict()}})
        return True
    except Exception as e:
        print(f"Error in generate environment location: {e}")
        return False


class SchemaLocationDescription(BaseModel):
    description: str = Field(...,
                             title="Description",
                             description="general description of the place, theme, appearance",
                             max_length=50)
    description_floor: str = Field(...,
                                   title="Description Floor",
                                   description="detailed description of the apartment next to a wall",
                                   max_length=100,
                                   min_length=80)


class SchemaLocationSound(BaseModel):
    sound_id: str = Field(...,
                          title="Sound ID",
                          description="Sound ID that most closely resembles the location",
                          max_length=50)


async def generate_location_description(_location_id: str, _user_id: str):
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(_location_id)}):
            prompt_db_location_place = await get_prompt_by_category_service("location_place")
            prompt_db_location_place["description"] = (prompt_db_location_place["description"]
                                                       .replace("{{PromptUserLocation}}", location_db["prompt_user"]))
            response_description = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": "Eres un personaje en un videojuego de realidad virtual. Estás en un lugar nuevo"
                                   " y necesitas describirlo para que otros jugadores puedan encontrarlo."
                    },
                    {
                        "role": "user",
                        "content": f"{prompt_db_location_place['description']}"
                    },
                ],
                model="gpt-4o-mini",
                max_tokens=4096,
                response_format=SchemaLocationDescription,
                type_generation="generate_description_location",
                user_id=_user_id
            )
            return response_description
    except Exception as e:
        print(f"Error in generate location description: {e}")
        return None


async def identify_location_sound(_location_id: str, _user_id: str):
    location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})
    try:
        sounds_db = await get_sounds_service()
        response_sound = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "con la siquiente image y descripcion de una locacion, escoje uno de los "
                                    "sonidos de la lista que se escucharia en este lugar"
                        },
                        {
                            "type": "text",
                            "text": f"Listado de sonidos: {sounds_db}"
                        },
                        {
                            "type": "text",
                            "text": f"descripcion de la locacion : {location_db['description']}"
                        },
                    ],
                }
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format=SchemaLocationSound,
            type_generation="identify_sound_by_location",
            user_id=_user_id
        )
        return response_sound
    except Exception as e:
        print(f"Error in identify location sound: {e}")
        return None


async def generate_location_image(_location_id: str, _user_id: str):
    try:
        location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})
        if not location_db:
            raise Exception("Location not found")
        prompt_db_image_location = await get_prompt_by_category_service("location_image")
        content_prompt = f'{prompt_db_image_location["description"]}, {location_db["description"]}'
        new_prompt = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system",
                 "content": "reestructure el prompt para generar la imagen con estilo 3D volumétrico en vista"
                            " isométrica para un videojuego RPG, con fondo de color solido."},
                {"role": "user", "content": content_prompt},
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format="text",
            type_generation="text"
        )
        image_location = await openai_generator.generate_image(
            prompt=new_prompt,
            quality="hd",
            size="1792x1024",
            user_id=_user_id,
            type_generation="generate_image_location",
        )
        image_generated = upload_image(
            url_image=image_location,
            file_name=f"characters/{uuid4()}.jpg",
            size=(512, 512),
        )
        await db['location'].update_one({"_id": ObjectId(_location_id)},
                                        {"$set": {"image": image_generated}})
        return True
    except Exception as e:
        print(f"Error in generate location image: {e}")
        return False


async def async_generate_location_task(_location_id: str, _user_id: str, _task_id: str):
    await update_task_service(
        _id=_task_id,
        _status="pending"
    )
    message_response = ""
    response_description = await generate_location_description(_location_id, _user_id)
    if not response_description:
        message_response += " Error in generate description location service. "
    response_sound = await identify_location_sound(_location_id, _user_id)
    if not response_sound:
        message_response += " Error in identify location sound service. "
    response_image = await generate_location_image(_location_id, _user_id)
    if not response_image:
        message_response += " Error in generate location image service. "
    response_environment = await generate_environment_location(_location_id, _user_id)
    if not response_environment:
        message_response += " Error in generate environment location service. "
    if message_response != "":
        await db["task"].update_one({"_id": _task_id},
                                    {"$set": {"status": "error",
                                              "message": message_response}})
        return message_response
    else:
        await db["task"].update_one({"_id": _task_id},
                                    {"$set": {"status": "completed",
                                              "message": "Location generate successfully"}})

        return "Location generate successfully"


async def async_generate_image_location_task(_location_id: str, _user_id: str, _task_id: str):
    await update_task_service(
        _id=_task_id,
        _status="pending"
    )
    message_response = ""
    response_image = await generate_location_image(_location_id, _user_id)
    if not response_image:
        message_response += " Error in generate location image service. "
    response_environment = await generate_environment_location(_location_id, _user_id)
    if not response_environment:
        message_response += " Error in generate environment location service. "
    if message_response != "":
        await db["task"].update_one({"_id": _task_id},
                                    {"$set": {"status": "error",
                                              "message": message_response}})
        return message_response
    else:
        await db["task"].update_one({"_id": _task_id},
                                    {"$set": {"status": "completed",
                                              "message": "Location generate successfully"}})

        return "Location image generate successfully"
