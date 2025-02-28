from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from object.schemas import SchemaListObject, SchemaNewInteractionItem, SchemaDeactivateItem
from object.schemas import SchemaCreateItem
from object.schemas import SchemaUpdatedObjectLocation
from object.schemas import SchemaAddItemLocation
from object.schemas import SchemaRetrieveObject
from object.schemas import SchemaCreateObject

from object.services import (
    get_objects_service,
    new_interaction_item_service,
    deactivate_item_service,
)
from object.services import create_item_service
from object.services import update_item_service
from object.services import add_item_location_service
from object.services import add_or_edit_item_characteristic_service
from object.services import retrieve_object_service

from user.services import disable_user_service, validate_star_user_service

router = APIRouter(prefix="/item", tags=["Items"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListObject)
async def get_objects(
    game_id: str = None,
    location_id: str = None,
    user_db: dict = Depends(auth),
    page: int = 1,
    limit: int = 100,
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all objects.

    It returns a list of objects.
    """

    objects_db, counts_objects = await get_objects_service(
        game=game_id, location=location_id, user=str(user_db.get("_id")), skip=page, limit=limit
    )

    return SchemaListObject(results=objects_db, count=counts_objects)


@router.get("/{item_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveObject)
async def retrieve_object(
    item_id: str,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a object.

    It returns a object.
    """

    object_db = await retrieve_object_service(object_id=item_id)

    return object_db


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveObject)
async def create_object(
    object_: SchemaCreateObject,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a new object.

    It returns the created object.
    """

    try:
        object_db = await create_item_service(object_, str(user_db.get("_id")))
        return object_db

    except Exception as e:
        print(f"Error in create object: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )


@router.patch("/{item_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveObject)
async def update_item(
    item_id: str,
    object_: SchemaCreateItem,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint updates a object.

    It returns the updated object.
    """

    try:
        object_db = await update_item_service(item_id, object_)
        return object_db

    except Exception as e:
        print(f"Error in create object: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )


# @router.post("/add-item-location/", status_code=status.HTTP_200_OK)
# async def add_item_location(
#         item: SchemaAddItemLocation,
#         user_db: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     """
#     This endpoint adds a object to a location.
#
#     It returns the added object.
#     """
#
#     object_db = await add_item_location_service(item.item_id, item.location_id)
#     return object_db


@router.post("/add-edit-characteristic/")
async def add_edit_characteristic(
    item: SchemaUpdatedObjectLocation,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint adds or edits a characteristic to a object in a location.

    It returns the added or edited object.
    """

    try:
        object_db = await add_or_edit_item_characteristic_service(
            item.item_id,
            item.location_id,
            item.characteristics,
            str(user_db.get("_id")),
            item.game_id,
            item.state_game,
        )
        return object_db

    except Exception as e:
        print(f"Error in create object: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )


@router.post("/{item_id}/generate-interaction/", status_code=status.HTTP_200_OK)
async def generate_interaction_item(
    item_id: str,
    new_interaction: SchemaNewInteractionItem,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint generates a interaction for a object.

    It returns the generated interaction.
    """

    object_db = await new_interaction_item_service(
        location_id=new_interaction.location_id,
        game_id=new_interaction.game_id,
        item_id=item_id,
        prompt_user_dialog=new_interaction.prompt_user_dialog,
        user_id=str(user_db.get("_id")),
        state_game=new_interaction.state_game,
    )
    return object_db


@router.post("/disable/{item_id}/")
async def disable_character(
    item_id: str,
    item: SchemaDeactivateItem,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        character_db = await deactivate_item_service(
            item_id=item_id, state_game=item.state_game, active=item.is_active
        )
        return {"message": "Location disabled or enabled"}
    except Exception as e:
        print(f"error in get character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not found",
        )
