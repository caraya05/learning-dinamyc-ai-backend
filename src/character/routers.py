from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi import Request

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from character.schemas import SchemaUpdateCharacterCollection
from character.schemas import SchemaAddCharacterLocation
from character.schemas import SchemaUpdatedCharacterLocation
from character.schemas import SchemaCreateCharacter
from character.schemas import SchemaRetrieveCharacter
from character.schemas import SchemaListCharacter

from character.services import get_character_service
from character.services import create_character_service
from character.services import delete_character_service
from character.services import add_character_to_location_service
from character.services import get_characters_by_location_service
from character.services import add_or_edit_character_location
from character.services import get_all_character_service
from character.services import update_character_service
from character.services import get_characters_service

from game.services import get_game_v2_service
from game.services import get_characters_game_publish_service
from game.services import get_character_game_publish_service
from game.services import get_location_game_publish_service

from prompt.services import get_prompt_by_category_service

from user.services import disable_user_service
from user.services import validate_star_user_service

router = APIRouter(prefix='/characters', tags=['Characters'])


@router.get("/{character_id}", response_model=SchemaRetrieveCharacter)
async def get_character(
        character_id: str,
        publish: bool = False,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a character.

    It expects the character's id in the request path.
    If the character is successfully retrieved, it returns the character's information.
    """

    if publish:
        game_id = character_id.split('_')[1]
        character_id = character_id.split('_')[0]
        try:
            character_db = await get_character_game_publish_service(character_id=character_id, game_id=game_id)

            return character_db

        except Exception as e:
            print(f"error in get character: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Character not found",
            )
    else:
        try:
            character_db = await get_character_service(character_id=character_id)

            return character_db

        except Exception as e:
            print(f"error in get character: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Character not found",
            )


@router.get("/", response_model=SchemaListCharacter)
async def get_characters(
        location_id: str,
        publish: bool = False,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all characters.

    It returns a list of characters.
    """

    if publish:
        try:
            game_id = location_id.split("_")[-1]
            location_id = location_id.split("_")[0]
            locations_db = await get_location_game_publish_service(game_id=game_id, location_id=location_id)
            return SchemaListCharacter(results=locations_db["characters"], count=len(locations_db["characters"]))
        except Exception as e:
            print(f"error in get characters: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Characters publish not found",
            )

    else:
        try:
            characters_db = await get_characters_by_location_service(skip=1, limit=100, location_id=location_id)

            for i in characters_db:
                i["_id"] = str(i["_id"])

            return SchemaListCharacter(results=characters_db, count=len(characters_db))

        except Exception as e:
            print(f"error in get characters: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Characters not found",
            )


@router.get("/me/", response_model=SchemaListCharacter)
async def get_all_characters(
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        count: int = 10,
):
    """
    This endpoint retrieves all characters.

    It returns a list of characters.
    """

    try:
        characters_db = await get_all_character_service(user_id=str(user_db.get("_id")), skip=page, limit=count)

        for i in characters_db:
            i["_id"] = str(i["_id"])

        return SchemaListCharacter(results=characters_db, count=len(characters_db))

    except Exception as e:
        print(f"error in get characters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Characters not found",
        )


@router2.get("/{character_id}/generate-face/", response_model=SchemaRetrieveCharacter)
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

        await disable_user_service(user_id=str(user_db.get("_id")), section="character")

        return character_db

    except Exception as e:
        print(f"error in get characters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Characters not found",
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


@router.post("/add-character-location/")
async def add_character_location(
        character_location: SchemaAddCharacterLocation,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a character.

    It expects the character's information in the request body.
    If the character is successfully created, it returns the character's information.
    """

    try:

        if character_db := await add_character_to_location_service(character_id=character_location.character_id,
                                                                   location_id=character_location.location_id):
            return character_db

    except HTTPException as e:
        print(f"error in create character: {str(e)}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
        )


@router.post("/add-edit-characteristic/")
async def add_edit_characteristic(
        character: SchemaUpdatedCharacterLocation,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a character.

    It expects the character's information in the request body.
    If the character is successfully created, it returns the character's information.
    """

    try:

        if character_db := await add_or_edit_character_location(character_id=character.character_id,
                                                                location_id=character.location_id,
                                                                characteristics=character.characteristics,
                                                                user_id=str(user_db.get("_id"))):
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
        character_update: SchemaUpdateCharacterCollection,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint partially updates a character.

    It expects the character's id in the request path and the character's information in the request body.
    If the character is successfully updated, it returns the character's information.
    """

    try:
        character_db = await update_character_service(character_id=character_id,
                                                      name=character_update.name,
                                                      prompt_user=character_update.prompt_user)
        return character_db

    except Exception as e:
        print(f"error in partial update character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not updated",

        )


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
        character_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint deletes a character.

    It expects the character's id in the request path.
    If the character is successfully deleted, it returns status code 204.
    """

    await delete_character_service(character_id=character_id)
    return status.HTTP_204_NO_CONTENT
