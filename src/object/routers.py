from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme

from object.schemas import SchemaListObject
from object.schemas import SchemaRetrieveObject
from object.schemas import SchemaCreateObject

from object.services import get_objects_service, get_object_by_field
from object.services import retrieve_object_service
from object.services import create_object_service
from object.services import partial_update_object_service

from prompt.services import get_prompt_by_field

from gpt_ai.utils import generate_image_dalle
from utils import upload_image

router = APIRouter(prefix="/object", tags=["Object"])


def get_db(request: Request):
    return request.state.db


@router.get("/by-field/", response_model=SchemaRetrieveObject)
def get_objects_by_field(value: str,
                         field: str,
                         db: Session = Depends(get_db),
                         Authorize: AuthJWT = Depends(),
                         Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                         ):
    """
    This endpoint retrieves a object.

    It expects the object's id in the request path.
    If the object is successfully retrieved, it returns the object's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    object_db = get_object_by_field(db, field, value)

    return object_db


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListObject)
def get_objects(game_id: str,
                db: Session = Depends(get_db),
                Authorize: AuthJWT = Depends(),
                Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                ):
    """
    This endpoint retrieves all objects.

    It returns a list of objects.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    objects_db = get_objects_service(db, game_id, skip=0, limit=100)

    return SchemaListObject(results=objects_db, count=len(objects_db))


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveObject)
def create_object(object_: SchemaCreateObject,
                  db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint creates a new object.

    It returns the created object.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    object_db = create_object_service(db, object_, current_user)

    return object_db


@router.get("/{object_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveObject)
def retrieve_object(object_id: str,
                    db: Session = Depends(get_db),
                    Authorize: AuthJWT = Depends(),
                    Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                    ):
    """
    This endpoint retrieves a object.

    It returns a object.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    object_db = retrieve_object_service(db, object_id=object_id)

    return SchemaRetrieveObject(**object_db.dict())


@router.patch("/{object_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveObject)
def partial_update_object(object_id: str,
                          object_: SchemaCreateObject,
                          db: Session = Depends(get_db),
                          Authorize: AuthJWT = Depends(),
                          Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                          ):
    """
    This endpoint updates a object.

    It returns the updated object.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    object_db = partial_update_object_service(db, object_id, object_)

    return SchemaRetrieveObject(**object_db.dict())


@router.get("/generate-image/{object_id}", status_code=status.HTTP_200_OK)
def generate_image(object_id: str,
                   db: Session = Depends(get_db),
                   Authorize: AuthJWT = Depends(),
                   Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                   ):
    """
    This endpoint generates a image for a object.

    It returns the image.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    object_db = retrieve_object_service(db, object_id=object_id)

    prompt_db_image_object = get_prompt_by_field(db, 'category', 'image_object')

    prompt_object = prompt_db_image_object.description.replace("x_object", object_db.description)

    image_generated = generate_image_dalle(prompt_object,
                                           quality="hd",
                                           size="1024x1024")

    object_db.image = upload_image(url_image=image_generated,
                                   file_name=f"{object_db.game_id}/object/{object_db.name}.jpg",
                                   size=(512, 512))
    db.commit()
    db.refresh(object_db)

    return image_generated
