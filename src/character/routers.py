from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi import Request

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from character.schemas import SchemaUpdatePhotoCharacter
from character.schemas import SchemaCreateCharacter
from character.schemas import SchemaRetrieveCharacter
from character.schemas import SchemaListCharacter

from character.services import (
    get_character_service,
    update_attempts_character_service,
    create_character_service,
)
from character.services import get_characters_service
from character.services import update_partial_character_service
from character.services import get_images_character_face_service
from character.services import get_images_character_body_service
from character.services import update_partial_character_service
from gpt_ai.utils import generate_image_dalle
from prompt.services import get_prompt_by_category_service

router = APIRouter(prefix='/characters', tags=['Characters'])


@router.get("/", response_model=SchemaListCharacter)
async def get_characters(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all characters.

    It returns a list of characters.
    """

    try:
        characters_db = await get_characters_service(skip=1, limit=100, game_id=game_id)

        for i in characters_db:
            i["_id"] = str(i["_id"])

        return SchemaListCharacter(results=characters_db, count=len(characters_db))

    except Exception as e:
        print(f"error in get characters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Characters not found",
        )


@router.get("/{character_id}", response_model=SchemaRetrieveCharacter)
async def get_character(
        character_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a character.

    It expects the character's id in the request path.
    If the character is successfully retrieved, it returns the character's information.
    """

    try:
        character_db = await get_character_service(character_id=character_id)

        return character_db

    except Exception as e:
        print(f"error in get character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not found",
        )


@router.post("/", response_model=SchemaRetrieveCharacter)
async def create_character(
        character: SchemaCreateCharacter,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a character.

    It expects the character's information in the request body.
    If the character is successfully created, it returns the character's information.
    """

    try:
        character_db = await create_character_service(character=character, user_id=str(user_db.get("_id")))
        return character_db

    except Exception as e:
        print(f"error in create character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not created",
        )


@router.patch("/{character_id}", response_model=SchemaRetrieveCharacter)
async def partial_update_character(
        character_id: str,
        character_update: SchemaUpdatePhotoCharacter,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint partially updates a character.

    It expects the character's id in the request path and the character's information in the request body.
    If the character is successfully updated, it returns the character's information.
    """

    try:
        character_db = await update_partial_character_service(character_id=character_id,
                                                              character_update=character_update)
        return character_db

    except Exception as e:
        print(f"error in partial update character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not updated",
        )


@router.get("/generate_image/{character_id}")
async def generate_image(
        character_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint generates an image for a character.

    It expects the character's information in the request body.
    If the image is successfully generated, it returns the image.
    """

    character_db = await get_character_service(character_id=character_id)

    if character_db['attempts'] == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character attempts exhausted",
        )

    prompt_db_image_character = await get_prompt_by_category_service('character_image')

    content_prompt = f"{prompt_db_image_character['description']} genero :{character_db['gender']} descripcion: {character_db['description']}"

    # prompt_content = prompt_db_image_character.description.replace('x_personaje',
    #                                                                f"{character_db.genre} {character_db.description}")

    image_generated = generate_image_dalle(prompt=content_prompt, quality="hd", size="1024x1024")

    await update_attempts_character_service(character_id=character_id)

    return image_generated


router2 = APIRouter(prefix='/characters', tags=['Characters'])


@router2.get("/", response_model=SchemaListCharacter)
async def get_characters(
        collection_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all characters.

    It returns a list of characters.
    """

    try:
        characters_db = await get_characters_service(skip=0, limit=100, collection_id=collection_id)

        for i in characters_db:
            i["_id"] = str(i["_id"])

        return SchemaListCharacter(results=characters_db, count=len(characters_db))

    except Exception as e:
        print(f"error in get characters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Characters not found",
        )


@router2.get("/{character_id}/generate-face/")
async def get_images_character_face(
        character_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all characters.

    It returns a list of characters.
    """

    try:
        character_db = await get_images_character_face_service(character_id=character_id)

        return character_db

    except Exception as e:
        print(f"error in get characters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Characters not found",
        )


@router2.get("/{character_id}/generate-body/")
async def get_images_character_body(
        character_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all characters.

    It returns a list of characters.
    """

    try:
        character_db = await get_images_character_body_service(character_id=character_id)

        return character_db

    except Exception as e:
        print(f"error in get characters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Characters not found",
        )
