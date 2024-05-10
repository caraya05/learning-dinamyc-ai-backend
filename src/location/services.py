import json
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from core.database import db
from location.models import Location

from location.schemas import SchemaRetrieveLocation
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation

from scene.services import get_scenes_service

from place.services import get_place_service

from prompt.services import get_prompt_by_category_service

from script.services import get_script_by_game_id_service
# from sound.services import get_sound_by_field

from gpt_ai.utils import generate_gpt4_

from utils import upload_image


async def get_locations_service(*, game_id: str, place_id: str = None, skip: int = 0, limit: int = 100):
    """
    Get a list of locations.
    """
    try:
        if place_id:
            place_db = await get_place_service(place_id)
            locations_db = []
            for location_id in place_db["locations_id"]:
                location_db = await db['location'].find_one({"_id": ObjectId(location_id)})
                locations_db.append(location_db)
            count_locations = len(place_db["locations_id"])
            return locations_db, count_locations
        else:
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
            print(locations_order, count_locations)
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
            # if location.sound_id:
            #     location.sound = get_sound_by_field(db, "id", location.sound_id).sound
            if location_db["config"]:
                for config in location_db["config"]:
                    if config["user"] == user_id:
                        location_db["configuration"] = config["config"]
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
            if schema.place_id:
                place_db = await db['place'].find_one({"_id": ObjectId(schema.place_id)})
                place_db["locations_id"].append(str(location_created.inserted_id))
                await db['place'].update_one({"_id": ObjectId(schema.place_id)}, {"$set": place_db})
                if not location_schema.description:
                    await generate_description_location_service(location_id=str(location_created.inserted_id))
            if location_db := await db['location'].find_one({"_id": location_created.inserted_id}):
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
                location_db["image"] = upload_image(
                    url_image=schema.image,
                    file_name=f"locations/{uuid4()}.jpg",
                    size=(1218, 686),
                )
            if schema.configuration:
                if not location_db["config"]:
                    location_db["config"] = []
                json_config = {
                    "config": schema.configuration,
                    "user": user_id,
                }
                location_db["config"].append(json_config)

            await db['location'].update_one({"_id": ObjectId(location_id)}, {"$set": location_db})
            return await db['location'].find_one({"_id": ObjectId(location_id)})
    except Exception as e:
        print(f"Error in partial update location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Location not updated.")


async def update_attempts_location_service(location_id: str):
    """
    Update the attempts of a location.
    """
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
            location_db['attempts'] -= 1
            location_updated = await db['location'].update_one({"_id": ObjectId(location_id)}, {"$set": location_db})
            if location_updated.modified_count:
                location_db = await db['location'].find_one({"_id": ObjectId(location_id)})
                return location_db
    except Exception as e:
        print(f"Error in update attempts location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Attempts not updated.")


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


async def generate_description_location_service(location_id: str):
    """
    Generate a description for a location.
    """
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
            place_db = await get_place_by_location_service(location_id)
            prompt_db_location_place = await get_prompt_by_category_service("location_place")
            prompt_db_location_place["description"] = prompt_db_location_place["description"].replace(
                "{{PromptUserLocation}}",
                location_db["prompt_user"])
            prompt_db_location_place["description"] = prompt_db_location_place["description"].replace(
                "{{PromptUserPlace}}",
                place_db["prompt_user"])
            json_description = {"description": "string (description of the location)", }
            prompt_content = [
                {"role": "system",
                 "content": f"responde el prompt con la siguiente estructura JSON: {json_description}", },
                {"role": "user", "content": f"{prompt_db_location_place['description']}"},
            ]
            prompt_description = generate_gpt4_(
                content_prompt=prompt_content, type_text="scene cero", max_tokens=4096
            )
            response_prompt = json.loads(prompt_description)
            location_db["description"] = response_prompt["description"]
            await db['location'].update_one({"_id": ObjectId(location_id)}, {"$set": location_db})
    except Exception as e:
        print(f"Error in generate description location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Description not generated.")


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
