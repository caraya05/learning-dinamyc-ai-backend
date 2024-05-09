from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core.database import db
from place.schemas import SchemaCreatePlace, SchemaPartialUpdatePlace
from place.models import Place

from prompt.services import get_prompt_by_category_service

from gpt_ai.utils import generate_image_dalle
from utils import upload_image


async def create_place_service(*, schema: SchemaCreatePlace, user_id):
    """
    Create a place.
    """
    try:
        place = Place(**schema.dict(),
                      created_by=user_id,
                      updated_by=user_id)

        location_created = await db['place'].insert_one(place.dict())
        return await db['place'].find_one({"_id": location_created.inserted_id})
    except Exception as e:
        print(f"Error in create place service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Place not created")


async def get_place_service(place_id: str):
    """
    Get a place.
    """
    try:
        if place_db := await db['place'].find_one({"_id": ObjectId(place_id)}):
            return place_db
    except Exception as e:
        print(f"Error in get place service: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")


async def get_places_service(*, skip: int = 0, limit: int = 10, user_id: str = None):
    """
    Get all places.
    """
    try:
        if user_id:
            places_db = await db['place'].find({"created_by": user_id}).skip(skip).limit(limit).to_list(None)
            places_count = await db['place'].count_documents({"created_by": user_id})
        else:
            places_db = await db['place'].find().skip(skip).limit(limit).to_list(None)
            places_count = await db['place'].count_documents({})
        return places_db, places_count
    except Exception as e:
        print(f"Error in get places service: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Places not found")


async def generate_image_place_service(place_id: str):
    """
    Generate an image for a place.
    """
    try:
        if place_db := await db['place'].find_one({"_id": ObjectId(place_id)}):
            prompt_db_image_place = await get_prompt_by_category_service("place_image")
            prompt_db_image_place["description"] = prompt_db_image_place["description"].replace("{{place}}",
                                                                                                place_db["prompt_user"])
            print(prompt_db_image_place["description"])
            image = generate_image_dalle(prompt=prompt_db_image_place["description"],
                                         size="1792x1024",
                                         quality="hd")
            return image
    except Exception as e:
        print(f"Error in generate image place service: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Image not generated")


async def update_attempts_place_service(place_id: str):
    """
    Update the attempts of a place.
    """
    try:
        if place_db := await db['place'].find_one({"_id": ObjectId(place_id)}):
            await db['place'].update_one({"_id": ObjectId(place_id)},
                                         {"$inc": {"attempts": -1}})
    except Exception as e:
        print(f"Error in update attempts place service: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Attempts not updated")


async def update_place_service(*, place_id: str, schema: SchemaPartialUpdatePlace, user_id: str):
    """
    Update a place.
    """
    try:
        if place_db := await db['place'].find_one({"_id": ObjectId(place_id)}):
            place_db["updated_by"] = user_id
            if schema.title:
                place_db["title"] = schema.title
            if schema.image:
                place_db["image"] = upload_image(
                    url_image=schema.image,
                    file_name=f"location/{uuid4()}.jpg",
                    size=(1218, 686),
                )

            await db['place'].update_one({"_id": ObjectId(place_id)}, {"$set": place_db})
            return await db['place'].find_one({"_id": ObjectId(place_id)})
    except Exception as e:
        print(f"Error in update place service: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Place not updated")
