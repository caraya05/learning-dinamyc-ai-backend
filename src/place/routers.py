from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from place.services import create_place_service, delete_place_service
from place.services import get_place_service
from place.services import get_places_service
from place.services import generate_image_place_service
from place.services import update_place_service

from place.schemas import SchemaCreatePlace
from place.schemas import SchemaRetrievePlace
from place.schemas import SchemaPartialUpdatePlace
from place.schemas import SchemeListPlace
from user.services import disable_user_service, validate_star_user_service

router = APIRouter(prefix="/place", tags=["Place"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemeListPlace)
async def get_places(
        skip: int = 1,
        limit: int = 10,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all places.

    It returns a list of places.
    """

    try:
        places_db, places_count = await get_places_service(skip=skip - 1, limit=limit, user_id=str(user_db["_id"]))
        for place in places_db:
            place["_id"] = str(place["_id"])
            place["location_count"] = len(place["locations_id"]) if place["locations_id"] else 0
            # if not place["locations_id"]:
            #     place["locations_id"] = None

        return SchemeListPlace(results=places_db, count=places_count, page=skip, total_pages=places_count // limit + 1)

    except Exception as e:
        print(f"Error in get places: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Places not found",
        )


@router.get("/{place_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrievePlace)
async def get_place(
        place_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a place.

    It returns a place.
    """

    try:
        place_db = await get_place_service(place_id=place_id)
        place_db["location_count"] = len(place_db["locations_id"]) if place_db["locations_id"] else 0
        return place_db

    except Exception as e:
        print(f"Error in get place: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@router.get("/{place_id}/generate-image", status_code=status.HTTP_200_OK)
async def generate_image_place(
        place_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint generates an image for a place.

    It returns a generated image.
    """

    try:
        image = await generate_image_place_service(place_id=place_id)

        await disable_user_service(user_id=str(user_db["_id"]), section="place")

        return image

    except Exception as e:
        print(f"Error in generate image place: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image not generated")


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrievePlace)
async def create_place(
        schema: SchemaCreatePlace,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a place.

    It expects the place's information in the request body.
    If the place is successfully created, it returns the place's information.
    """
    await validate_star_user_service(user_id=str(user_db.get("_id")))

    try:
        place_db = await create_place_service(schema=schema, user_id=str(user_db["_id"]))

        return place_db

    except Exception as e:
        print(f"Error in create place: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Place not created")


@router.put("/{place_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrievePlace)
async def update_place(
        place_id: str,
        schema: SchemaPartialUpdatePlace,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint updates a place.

    It expects the place's information in the request body.
    If the place is successfully updated, it returns the place's information.
    """

    try:
        place_db = await update_place_service(place_id=place_id, schema=schema, user_id=str(user_db["_id"]))

        return place_db

    except Exception as e:
        print(f"Error in update place: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Place not updated")


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place(
        place_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint deletes a place.

    If the place is successfully deleted, it returns True.
    """

    try:
        await delete_place_service(place_id=place_id)
        return True

    except Exception as e:
        print(f"Error in delete place: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Place not deleted")
