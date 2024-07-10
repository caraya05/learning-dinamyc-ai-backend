from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from uuid import uuid4

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from object.schemas import SchemaListObject, SchemaCreateItem, SchemaUpdatedObjectLocation, SchemaAddItemLocation
from object.schemas import SchemaRetrieveObject
from object.schemas import SchemaCreateObject

from object.services import get_objects_service, update_image_object_service, create_item_service, update_item_service, \
    delete_object_service, add_item_location_service, add_or_edit_item_characteristic_service, \
    get_item_by_location_service, get_all_object_service
from object.services import retrieve_object_service
from object.services import create_object_service
# from object.services import partial_update_object_service

from prompt.services import get_prompt_by_category_service

from gpt_ai.utils import generate_image_dalle
from user.services import disable_user_service
from utils import upload_image

router = APIRouter(prefix="/object", tags=["Object"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListObject)
async def get_objects(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all objects.

    It returns a list of objects.
    """

    objects_db, counts_objects = await get_objects_service(game_id, skip=0, limit=100)

    return SchemaListObject(results=objects_db, count=counts_objects)


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
        object_db = await create_object_service(object_, str(user_db.get("_id")))
        return object_db

    except Exception as e:
        print(f"Error in create object: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )


@router.get("/{object_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveObject)
def retrieve_object(
        object_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a object.

    It returns a object.
    """

    object_db = retrieve_object_service(object_id=object_id)

    return object_db


# @router.patch("/{object_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveObject)
# def partial_update_object(
#         object_id: str,
#         object_: SchemaCreateObject,
#         db: Session = Depends(get_db),
#         Authorize: AuthJWT = Depends(),
#         Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
# ):
#     """
#     This endpoint updates a object.
#
#     It returns the updated object.
#     """
#
#     try:
#         Authorize.jwt_required()
#         current_user = Authorize.get_jwt_subject()
#
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid token",
#         )
#
#     object_db = partial_update_object_service(db, object_id, object_)
#
#     return SchemaRetrieveObject(**object_db.dict())


@router.get("/generate-image/{object_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveObject)
async def generate_image(
        object_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint generates a image for a object.

    It returns the image.
    """

    try:

        object_db = await retrieve_object_service(object_id=object_id)
        prompt_db_image_object = await get_prompt_by_category_service('image_object')
        prompt_object = prompt_db_image_object.get("description").replace("x_object", object_db.get("description"))
        image_generated = generate_image_dalle(prompt_object, quality="hd", size="1024x1024")

        image_object = upload_image(
            url_image=image_generated,
            file_name=f"object/{uuid4()}.jpg",
            size=(512, 512),
        )

        object_db = await update_image_object_service(object_id, image_object)
        return object_db

    except Exception as e:
        print(f"Error in generate image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image not generated",
        )


router2 = APIRouter(prefix="/item", tags=["Item"])


@router2.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveObject)
async def create_object(
        object_: SchemaCreateItem,
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


@router2.get("/{item_id}/generate-image/", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveObject)
async def generate_image(
        item_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint generates a image for a object.

    It returns the image.
    """

    try:

        object_db = await retrieve_object_service(object_id=item_id)
        prompt_db_image_object = await get_prompt_by_category_service('image_object')
        prompt_object = prompt_db_image_object.get("description").replace("x_object", object_db.get("prompt_user"))
        image_generated = generate_image_dalle(prompt_object, quality="hd", size="1024x1024")

        image_object = upload_image(
            url_image=image_generated,
            file_name=f"object/{uuid4()}.jpg",
            size=(512, 512),
        )

        await disable_user_service(user_id=str(user_db["_id"]), section="item")

        object_db = await update_image_object_service(item_id, image_object)
        return object_db

    except Exception as e:
        print(f"Error in generate image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image not generated",
        )


@router2.patch("/{item_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveObject)
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


@router2.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
        item_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint deletes a object.

    It returns the deleted object.
    """

    try:
        object_db = await delete_object_service(item_id)
        return object_db

    except Exception as e:
        print(f"Error in create object: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )


@router2.post("/add-item-location/", status_code=status.HTTP_200_OK)
async def add_item_location(
        item: SchemaAddItemLocation,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint adds a object to a location.

    It returns the added object.
    """

    object_db = await add_item_location_service(item.item_id, item.location_id)
    return object_db


@router2.post("/add-edit-characteristic/")
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
        object_db = await add_or_edit_item_characteristic_service(item.item_id, item.location_id,
                                                                  item.characteristics, str(user_db.get("_id")))
        return object_db

    except Exception as e:
        print(f"Error in create object: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )


@router2.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListObject)
async def get_objects(
        location_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all objects.

    It returns a list of objects.
    """

    objects_db = await get_item_by_location_service(location_id)
    print(objects_db)

    return SchemaListObject(results=objects_db, count=len(objects_db))


@router2.get("/all/", status_code=status.HTTP_200_OK, response_model=SchemaListObject)
async def get_all_objects(
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        count: int = 10,
):
    """
    This endpoint retrieves all objects.

    It returns a list of objects.
    """

    objects_db = await get_all_object_service(user_id=str(user_db.get("_id")), skip=page, limit=count)
    for object_db in objects_db:
        object_db["_id"] = str(object_db["_id"])

    return SchemaListObject(results=objects_db, count=len(objects_db))
