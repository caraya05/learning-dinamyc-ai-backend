from uuid import uuid4

from bson import ObjectId

from pydantic import BaseModel
from pydantic import Field

from core.database import db

from gpt_ai.utils import openai_generator

from prompt.services import get_prompt_by_category_service
from sound.services import get_sounds_service

from task.services import update_task_service
from user.services import disable_user_service

from utils import upload_image


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


async def async_generate_location_task(_location_id: str, _user_id: str):
    """
    Generate a description and identify the sound for a location.
    """
    try:
        response_description = await generate_location_description(_location_id, _user_id)
        if not response_description:
            return False

        response_sound = await identify_location_sound(_location_id, _user_id)
        if not response_sound:
            return False

        response_image = await generate_location_image(_location_id, _user_id)
        if not response_image:
            return False

        await db['location'].update_one({"_id": ObjectId(_location_id)},
                                        {"$set": {
                                            "description": response_description['description'],
                                            "description_floor": response_description['description_floor'],
                                            "sound_id": response_sound["id"],
                                        }})
        return True
    except Exception as e:
        print(f"Error in generate description location service: {e}")
        return False
