from bson import ObjectId
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from core import db
from gpt_ai.utils import generate_image_dalle

from location.schemas import SchemaListLocation
from location.schemas import SchemaRetrieveLocation
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation

from location.services import get_locations_service
from location.services import get_place_by_location_service
from location.services import get_location_service
from location.services import create_location_service
from location.services import partial_update_location_service
from location.services import update_attempts_location_service
from prompt.services import get_prompt_by_category_service
from sound.utils import identify_by_location_service

router = APIRouter(prefix="/location", tags=["Location"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListLocation)
async def get_locations(
        game_id: str = None,
        place_id: str = None,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all locations.

    It returns a list of locations.
    """

    try:
        locations_db, count_locations = await get_locations_service(skip=0, limit=100, game_id=game_id,
                                                                    place_id=place_id)

        for location in locations_db:
            location["_id"] = str(location["_id"])

        return SchemaListLocation(results=locations_db, count=count_locations)

    except Exception as e:
        print(f"Error in get locations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Locations not found",
        )


@router.get("/{location_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveLocation)
async def get_location(
        location_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a location.

    It expects the location's id in the request path.
    If the location is successfully retrieved, it returns the location's information.
    """

    try:
        location_db = await get_location_service(location_id=location_id, user_id=str(user_db['_id']))

        return location_db

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveLocation)
async def create_location(
        schema: SchemaCreateLocation,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a location.

    It expects the location's information in the request body.
    If the location is successfully created, it returns the location's information.
    """

    try:
        location_db = await create_location_service(schema, str(user_db['_id']))
        return location_db

    except Exception as e:
        print(f"Error in create location: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location not created",
        )


@router.patch(
    "/{location_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveLocation
)
async def partial_update_location(
        location_id: str,
        schema: SchemaPartialUpdateLocation,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint partially updates a location.

    It expects the location's id in the request path.
    It expects the location's information in the request body.
    If the location is successfully updated, it returns the location's information.
    """

    try:
        location_db = await partial_update_location_service(location_id=location_id, schema=schema,
                                                            user_id=str(user_db['_id']))
        print(location_db)
        if location_db["config"]:
            for config in location_db["config"]:
                if config["user"] == str(user_db['_id']):
                    location_db["configuration"] = config["config"]
        return location_db

    except Exception as e:
        print(f"Error in partial update location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location not updated",
        )


@router.get("/generate_image/{location_id}", status_code=status.HTTP_200_OK)
async def generate_image_location(
        location_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint generates an image for a location.

    It expects the location's id in the request path.
    If the location is successfully updated, it returns the location's information.
    """
    location_db = await get_location_service(location_id=location_id, user_id=str(user_db['_id']))
    if location_db["attempts"] == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character attempts exhausted",
        )

    place_db = await get_place_by_location_service(location_id=location_id)

    if place_db:
        prompt_db_image_location = await get_prompt_by_category_service("location_place_image")
        prompt_db_image_location["description"] = prompt_db_image_location["description"].replace(
            "{{PromptUserLocation}}", location_db["prompt_user"])
        prompt_db_image_location["description"] = prompt_db_image_location["description"].replace(
            "{{PromptUserPlace}}", place_db["prompt_user"])
        prompt_db_image_location["description"] = prompt_db_image_location["description"].replace(
            "{{descriptionPlace}}", place_db["prompt_user"])
        content_prompt = prompt_db_image_location["description"]
    else:
        prompt_db_image_location = await get_prompt_by_category_service("location_image")

        content_prompt = f'{prompt_db_image_location["description"]}, {location_db["description"]}'

    image_generate = generate_image_dalle(prompt=content_prompt,
                                          quality="hd",
                                          size="1792x1024")

    sound_identification = await identify_by_location_service(description=location_db["prompt_user"],
                                                              image=image_generate)
    location_db["sound_id"] = sound_identification["id"]
    await db['location'].update_one({"_id": ObjectId(location_id)}, {"$set": location_db})

    await update_attempts_location_service(location_id=location_id)

    return image_generate
