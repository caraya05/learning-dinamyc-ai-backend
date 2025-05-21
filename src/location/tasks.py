import traceback
from http.client import HTTPException
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
    rain_mode: bool = Field(
        ...,
        title="Rain Mode",
        description="Indicates whether there should be rain at the site.",
    )
    snow_model: bool = Field(
        ...,
        title="Snow Mode",
        description="Indicates whether there should be snow at the site.",
    )
    fire_mode: bool = Field(
        ...,
        title="Fire Mode",
        description="Indicates whether there should be a fire at the site.",
    )


async def generate_environment_location(_location_id: str, _user_id: str, _state_game_id: str):
    try:
        element_state_db = await db['state_glic'].find_one({"element_id": _location_id, "state": _state_game_id})
        if not element_state_db:
            return False

        response_analyze = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f"Analiza cuidadosamente la imagen proporcionada y describe detalladamente el ambiente"
                               f" que se muestra, incluyendo las condiciones climáticas, iluminación, y el estado "
                               f"general del entorno. Basado en la escena, determina si sería apropiado agregar efectos"
                               f" como humo o chispas que emergen de la lava para mejorar la atmósfera. No incluyas lluvia"
                               f" o nieve ya que se trata de una cueva de lava con un ambiente de calor extremo.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": element_state_db["data"]["image"]}
                        },
                    ],
                },
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            type_generation="generate_environment_location",
            user_id=_user_id,
            vision=True,
        )

        response_analyze_image = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f"Extrae la información del JSON proporcionado sobre la imagen de la locación y "
                               f"describe detalladamente el ambiente mostrado, incluyendo aspectos como la presencia "
                               f"de niebla, iluminación, lluvia, nieve y fuego. Indica cómo cada uno de estos elementos "
                               f"contribuye a la atmósfera general de la escena. No incluyas lluvia o nieve ya que se trata "
                               f"de una cueva de lava con un ambiente de calor extremo. Aquí tienes algunos ejemplos de ambientes:\n\n"
                               f"A continuación, se presentan ejemplos de preguntas y respuestas para guiar la generación:\n\n"
                               f"### Ejemplo de Pregunta:\n"
                               f"{{'role': 'user', 'content': 'La locación es una cueva de lava con ríos de magma y humo saliendo de las grietas. Describe el ambiente.'}}\n"
                               f"### Ejemplo de Respuesta:\n"
                               f"{{'fog_level': 'medium', 'light_mode': 'shade', 'light_intensity': 'high', 'rain_mode': False, 'snow_model': False, 'fire_mode': True}}\n\n"
                               f"### Ejemplo de Pregunta:\n"
                               f"{{'role': 'user', 'content': 'La locación es un bosque nevado con árboles cubiertos de nieve y un cielo despejado. Describe el ambiente.'}}\n"
                               f"### Ejemplo de Respuesta:\n"
                               f"{{'fog_level': 'medium', 'light_mode': 'blueSky', 'light_intensity': 'low', 'rain_mode': False, 'snow_model': True, 'fire_mode': False}}\n\n"
                               f"### Ejemplo de Pregunta:\n"
                               f"{{'role': 'user', 'content': 'La locación es un campo abierto con un cielo nublado y una ligera llovizna. Describe el ambiente.'}}\n"
                               f"### Ejemplo de Respuesta:\n"
                               f"{{'fog_level': 'low', 'light_mode': 'cloudy', 'light_intensity': 'low', 'rain_mode': True, 'snow_model': False, 'fire_mode': False}}",
                },
                {
                    "role": "user",
                    "content": f"descripcion de la imagen de la locacion : {response_analyze}",
                },
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format=SchemaLocationEnvironment,
            type_generation="generate_environment_location",
            user_id=_user_id,
        )

        location_environment = {
            "fog_level": response_analyze_image.fog_level,
            "light_mode": response_analyze_image.light_mode,
            "light_intensity": response_analyze_image.light_intensity,
            "rain_mode": response_analyze_image.rain_mode,
            "snow_model": response_analyze_image.snow_model,
            "fire_mode": response_analyze_image.fire_mode,
            "animals": []
        }

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
        description="detailed description of the apartment next to a wall",
    )


class SchemaLocationSound(BaseModel):
    sound_id: str = Field(
        ..., title="Sound ID", description="Sound ID that most closely resembles the location"
    )


async def generate_location_description(_location_id: str, _user_id: str, state_game_id):
    try:
        location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})

        element_state_db = await db["state_glic"].find_one(
            {"element_id": _location_id, "state": state_game_id}
        )

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
    element_state_db = await db["state_glic"].find_one(
        {"element_id": _location_id, "state": _state_game_id}
    )
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
                },
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

        element_state_db = await db["state_glic"].find_one(
            {"element_id": _location_id, "state": _state_game_id}
        )

        prompt_db_image_location = await get_prompt_by_category_service("location_image")
        content_prompt = (
            f'{prompt_db_image_location["description"]}, {element_state_db["data"]["description"]}'
        )
        new_prompt = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "reestructure el prompt para generar la imagen con estilo 3D volumétrico en vista"
                               " isométrica para un videojuego RPG, con fondo de color solido.",
                },
                {"role": "user", "content": content_prompt},
            ],
            model="gpt-4o-mini",
            max_tokens=4096,
            response_format=SchemaLocationImage,
            type_generation="text generation location image",
            user_id=_user_id,
        )

        validate_prompt = await openai_generator.moderation_text(
            text=new_prompt.response, user_id=_user_id
        )
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
            file_name=f"locations/{uuid4()}.jpg",
            size=(2436, 1372),
        )
        # await db['location'].update_one(
        #     {"_id": ObjectId(_location_id)}, {"$set": {"image": image_generated}}
        # )

        element_state_db["data"]["image"] = image_generated

        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]}, {"$set": {"data": element_state_db["data"]}}
        )

        return True, "Image generated successfully"
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generate location image: {e}")
        return False, "Error in generate location image"


async def async_generate_location_task(
        _location_id: str, _user_id: str, _task_id: str, _state_game_id: str
):
    await update_task_service(_id=_task_id, _status="pending")
    location_db = await db['location'].find_one({"_id": ObjectId(_location_id)})
    if not location_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message=f"Error can't find location with id {_location_id}",
        )
        return f"Error can't find location with id {_location_id}"
    response_description = await generate_location_description(
        _location_id, _user_id, _state_game_id
    )
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
    response_environment = await generate_environment_location(
        _location_id, _user_id, _state_game_id
    )
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
