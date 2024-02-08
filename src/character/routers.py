from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi import Request

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from character.schemas import SchemaUpdatePhotoCharacter
from character.schemas import SchemaRetrieveCharacter
from character.schemas import SchemaListCharacter

from character.services import get_character_service, update_attempts_character_service
from character.services import get_characters_service
from character.services import update_partial_character_service
from config import auth_scheme
from gpt_ai.utils import generate_image_dalle
from prompt.services import get_prompt_by_field

router = APIRouter(prefix='/characters', tags=['Characters'])


def get_db(request: Request):
    return request.state.db


@router.get("/", response_model=SchemaListCharacter)
def get_characters(game_id: str,
                   db: Session = Depends(get_db),
                   Authorize: AuthJWT = Depends(),
                   Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                   ):
    """
    This endpoint retrieves all characters.

    It returns a list of characters.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    characters_db = get_characters_service(db, skip=0, limit=100, game_id=game_id)
    # print(characters_db[0].__dict__)

    # return SchemaListCharacter(results=characters_db, count=len(characters_db))
    return SchemaListCharacter(results=characters_db, count=len(characters_db))


@router.get("/{character_id}", response_model=SchemaRetrieveCharacter)
def get_character(character_id: str,
                  db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint retrieves a character.

    It expects the character's id in the request path.
    If the character is successfully retrieved, it returns the character's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    character_db = get_character_service(db, character_id=character_id)

    return SchemaRetrieveCharacter.from_orm(character_db)


# @router.post("/", response_model=SchemaRetrieveCharacter)
# def create_character(character: SchemaCreateCharacter,
#                      db: Session = Depends(get_db),
#                      Authorize: AuthJWT = Depends(),
#                      Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
#                      ):
#     """
#     This endpoint creates a character.
#
#     It expects the character's information in the request body.
#     If the character is successfully created, it returns the character's information.
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
#     character_db = create_character_service(db, character=character)
#
#     return SchemaRetrieveCharacter.from_orm(character_db)


@router.patch("/{character_id}", response_model=SchemaRetrieveCharacter)
def partial_update_character(character_id: str,
                             character_update: SchemaUpdatePhotoCharacter,
                             db: Session = Depends(get_db),
                             Authorize: AuthJWT = Depends(),
                             Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                             ):
    """
    This endpoint partially updates a character.

    It expects the character's id in the request path and the character's information in the request body.
    If the character is successfully updated, it returns the character's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    character_db = update_partial_character_service(db, character_id=character_id, character_update=character_update)

    return SchemaRetrieveCharacter.from_orm(character_db)


@router.get("/generate_image/{character_id}")
def generate_image(character_id: str,
                   db: Session = Depends(get_db),
                   Authorize: AuthJWT = Depends(),
                   Token: HTTPAuthorizationCredentials = Depends(auth_scheme), ):
    """
    This endpoint generates an image for a character.

    It expects the character's information in the request body.
    If the image is successfully generated, it returns the image.
    """

    character_db = get_character_service(db, character_id=character_id)

    if character_db.attempts == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character attempts exhausted",
        )

    prompt_db_image_character = get_prompt_by_field(db, 'category', 'character_image')

    content_prompt = f"{prompt_db_image_character.description} genero :{character_db.genre} descripcion: {character_db.description}"

    # prompt_content = prompt_db_image_character.description.replace('x_personaje',
    #                                                                f"{character_db.genre} {character_db.description}")

    image_generated = generate_image_dalle(prompt=content_prompt,
                                           size="1024x1024")

    update_attempts_character_service(db, character_id=character_id)

    return image_generated
