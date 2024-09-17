from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from game.services import get_locations_game_publish_service
from game.services import get_location_game_publish_service

from location.schemas import SchemaListLocation
from location.schemas import SchemaRetrieveLocation
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation

from location.services import get_locations_v2_service
from location.services import generate_image_location_service
from location.services import get_location_service
from location.services import create_location_service
from location.services import partial_update_location_service
from sound.services import get_sound_service
# TODO: falta implemntar el desconteo de estrellas
from user.services import disable_user_service
from user.services import validate_star_user_service

router = APIRouter(prefix="/location", tags=["Location"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListLocation)
async def get_locations(
        game_id: str = None,
        publish: bool = False,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all locations.

    It returns a list of locations.
    """
    if publish:
        try:
            locations_db = await get_locations_game_publish_service(game_id=game_id)

            for location in locations_db:
                location["_id"] = f'{location["_id"]}_{game_id}'

            return SchemaListLocation(results=locations_db, count=len(locations_db))
        except Exception as e:
            print(f"Error in get locations: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Locations not found",
            )
    else:
        try:
            locations_db, count_locations = await get_locations_v2_service(skip=0,
                                                                           limit=100,
                                                                           game_id=game_id)

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
        publish: bool = False,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a location.

    It expects the location's id in the request path.
    If the location is successfully retrieved, it returns the location's information.
    """

    if publish:
        game_id = location_id.split("_")[-1]
        location_id = location_id.split("_")[0]
        try:
            locations_db = await get_location_game_publish_service(game_id=game_id,
                                                                   location_id=location_id)
            sound_db = await get_sound_service(locations_db["sound_id"])
            locations_db["sound_id"] = sound_db["file"]
            return locations_db
        except Exception as e:
            print(f"Error in get locations: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Locations not found",
            )
    else:
        try:
            location_db = await get_location_service(location_id=location_id,
                                                     user_id=str(user_db['_id']))
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
    await validate_star_user_service(user_id=str(user_db.get("_id")))

    try:
        location_db = await create_location_service(location=schema,
                                                    user_id=str(user_db['_id']))
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
        location_db = await partial_update_location_service(location_id=location_id,
                                                            location=schema,
                                                            user_id=str(user_db['_id']))
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
    try:
        location_db = await generate_image_location_service(location_id=location_id,
                                                            user_id=str(user_db['_id']))
        return location_db

    except Exception as e:
        print(f"Error in generate image location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location not updated",
        )
        