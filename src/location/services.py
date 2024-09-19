import json
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from core.database import db

from character.services import get_characters_by_location_service
from location.models import Location
from location.schemas import SchemaRetrieveLocation
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation
from scene.services import get_scenes_service
from prompt.services import get_prompt_by_category_service
from script.services import get_script_by_game_id_service
# from sound.services import get_sound_by_field
from gpt_ai.utils import generate_gpt4_
from gpt_ai.utils import generate_gpt4o
from sound.utils import identify_by_location_service

from utils import upload_image


async def get_locations_service(*, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of locations.
    """
    try:
        locations = await db['location'].find({"game_id": game_id}).skip(skip).limit(limit).to_list(None)
        count_locations = await db['location'].count_documents({"game_id": game_id})
        script_db = await get_script_by_game_id_service(game_id)
        scenes_db, count_scene = await get_scenes_service(script_id=script_db["_id"])
        locations_order = []
        for scene in scenes_db:
            for location in locations:
                if location.id == scene.location_id and location not in locations_order:
                    locations_order.append(location)
        for location in locations:
            if location not in locations_order:
                locations_order.append(location)
        return locations_order, count_locations
    except Exception as e:
        print(f"Error in get locations service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locations not found.")


async def get_location_service(*, location_id: str, user_id: str) -> dict:
    """
    Get a location.
    """
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
            if location_db["sound_id"]:
                location_db["sound_id"] = await db['sound'].find_one({"_id": ObjectId(location_db["sound_id"])})

            if location_db["config"]:
                user_config_found = False
                for config in location_db["config"]:
                    if config["user"] == user_id:
                        location_db["configuration"] = config["config"]
                        user_config_found = True
                        break
                if not user_config_found and location_db["config"]:
                    location_db["configuration"] = location_db["config"][0]["config"]

            if location_db.get("connect", None):
                user_connect_found = False
                for connect in location_db["connect"]:
                    if connect["user"] == user_id:
                        location_db["connections"] = connect["connect"]
                        user_connect_found = True
                        break
                if not user_connect_found and location_db["connect"]:
                    location_db["connections"] = location_db["connect"][0]["connect"]

            if characters_db := await get_characters_by_location_service(skip=1, limit=100, location_id=location_id):
                location_db["characters"] = characters_db
            return location_db
    except Exception as e:
        print(f"Error in get location service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Location not found.")


async def create_location_service(schema: SchemaCreateLocation, user_id: str):
    """
    Create a location.
    """
    try:
        location_schema = Location(title=schema.title,
                                   description=schema.description,
                                   image=schema.image,
                                   attempts=3,
                                   game_id=schema.game_id,
                                   prompt_user=schema.prompt_user,
                                   created_by=user_id,
                                   updated_by=user_id)

        if location_created := await db['location'].insert_one(location_schema.dict()):
            if not location_schema.description:
                await generate_description_location_service(location_id=str(location_created.inserted_id))
            if location_db := await get_location_service(location_id=str(location_created.inserted_id),
                                                         user_id=user_id):
                return location_db
    except Exception as e:
        print(f"Error in create location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location not created")


async def partial_update_location_service(*, location_id: str, schema: SchemaPartialUpdateLocation, user_id: str):
    """
    Partially update a location.
    """
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
            location_db["updated_by"] = user_id
            if schema.title:
                location_db["title"] = schema.title
            if schema.prompt_user:
                location_db["prompt_user"] = schema.prompt_user
                await generate_description_location_service(location_id=location_id)
            if schema.image:
                json_environment = {
                    "fog_level": "string (none, medium, high) - The level of fog in the location",
                    "light_mode": "string (cloudy, directSun, shade, blueSky) - The light mode in the location",
                    "light_intensity": "string (low, high) - The light intensity in the location",
                    "animals": "array of strings ['dog','bird','squirrel','firefly'] - The animals in the location, choose only one or none if not necessary.",
                }

                prompt_analyze = [
                    {
                        "role": "system",
                        "content": f"Analiza la imagen de la locacion y describe el ambiente en la imagen, response con el siguiente formato JSON: {json_environment}"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": schema.image}},
                        ],
                    }
                ]

                response_analyze = generate_gpt4o(content_prompt=prompt_analyze, model="gpt-4o-mini")
                response_analyze = json.loads(response_analyze)
                location_db['environment'] = response_analyze
                location_db["image"] = upload_image(
                    url_image=schema.image,
                    file_name=f"locations/{uuid4()}.jpg",
                    size=(2436, 1372),
                )
            if schema.configuration:
                if not location_db["config"]:
                    location_db["config"] = []
                    json_config = {
                        "config": schema.configuration,
                        "user": user_id,
                    }
                    location_db["config"].append(json_config)
                else:
                    for i in range(len(location_db["config"])):
                        if location_db["config"][i]["user"] == user_id:
                            location_db["config"][i]["config"] = schema.configuration
                    # location_db["config"].append(config)

            if schema.connections:
                if not location_db.get("connect", None):
                    location_db["connect"] = []
                    json_connect = {
                        "connect": schema.connections,
                        "user": user_id,
                    }
                    location_db["connect"].append(json_connect)
                else:
                    for i in range(len(location_db["connect"])):
                        if location_db["connect"][i]["user"] == user_id:
                            location_db["connect"][i]["connect"] = schema.connections
                    # location_db["connect"].append(connect)
            del location_db["sound_id"]
            await db['location'].update_one({"_id": ObjectId(location_id)}, {"$set": location_db})
            return await get_location_service(location_id=location_id, user_id=user_id)
    except Exception as e:
        print(f"Error in partial update location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Location not updated.")


async def delete_location_service(location_id: str):
    """
    Delete a location.
    """
    try:
        if location_deleted := await db['location'].delete_one({"_id": ObjectId(location_id)}):
            if location_deleted.deleted_count:
                return True
    except Exception as e:
        print(f"Error in delete location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Location not deleted.")


# async def generate_description_location_service(location_id: str):
#     """
#     Generate a description for a location.
#     """
#     try:
#         if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
#             prompt_db_location_place = await get_prompt_by_category_service("location_place")
#             prompt_db_location_place["description"] = prompt_db_location_place["description"].replace(
#                 "{{PromptUserLocation}}", location_db["prompt_user"])
#             json_description = {
#                 "description": "string (general description of the place, theme, appearance, max 50 words)",
#                 "description_floor": "string (detailed description of the apartment next to a wall, min 80 words and max 100 words)",
#             }
#             prompt_content = [
#                 {"role": "system",
#                  "content": f"responde el prompt con la siguiente estructura JSON: {json_description}", },
#                 {"role": "user", "content": f"{prompt_db_location_place['description']}"},
#             ]
#             prompt_description = generate_gpt4_(
#                 content_prompt=prompt_content, type_text="scene cero", max_tokens=4096
#             )
#             response_prompt = json.loads(prompt_description)
#             location_db["description"] = f"{response_prompt['description']} // {response_prompt['description_floor']}"
#
#             sound_identification = await identify_by_location_service(description=response_prompt["description"])
#             location_db["sound_id"] = sound_identification["id"]
#
#             await db['location'].update_one({"_id": ObjectId(location_id)}, {"$set": location_db})
#     except Exception as e:
#         print(f"Error in generate description location service: {e}")
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
#                             detail="Description not generated.")


async def get_place_by_location_service(location_id: str):
    """
    Get a place by location.
    """
    try:
        if place_db := await db['place'].find_one({"locations_id": {"$in": [location_id]}}):
            return place_db
    except Exception as e:
        print(f"Error in get place by location service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Place not found.")


async def get_locations_v2_service(*, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of locations.
    """
    try:

        game_db = await db['game'].find_one({"_id": ObjectId(game_id)})
        locations = await (db['location'].find({"_id": {"$in": [ObjectId(i) for i in game_db["locations_id"]]}})
                           .sort("created_at", -1).skip(skip).limit(limit).to_list(None))
        count_locations = await db['location'].count_documents(
            {"_id": {"$in": [ObjectId(i) for i in game_db["locations_id"]]}})

        return locations, count_locations
    except Exception as e:
        print(f"Error in get locations service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locations not found.")
