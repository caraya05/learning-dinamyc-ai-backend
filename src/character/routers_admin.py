from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth_admin
from auth.utils import auth_schema

from character.schemas_admin import SchemaAdminUpdateCharacter
from character.schemas_admin import SchemaAdminCreateCharacter
from character.schemas_admin import SchemaAdminStateCharacters

from character.services_admin import get_character_service_admin
from character.services_admin import get_characters_service_admin
from character.services_admin import create_character_service_admin
from character.services_admin import update_character_service_admin

router = APIRouter(prefix='/character', tags=['Character'])


@router.get("/{character_id}",status_code=status.HTTP_200_OK)
async def get_character(
        character_id: str,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        character_db = await get_character_service_admin(character_id=character_id)
        return character_db
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )


@router.get("/", status_code=status.HTTP_200_OK)
async def get_characters(
        skip: int = 1,
        limit: int = 100,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        characters_db = await get_characters_service_admin(skip=skip, limit=limit)
        return characters_db
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characters not found",
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_character(
        character: SchemaAdminCreateCharacter,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        character_db = await create_character_service_admin(character=character, user_id=str(user_db["_id"]))
        return character_db
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not created",
        )


@router.put("/{character_id}", status_code=status.HTTP_200_OK)
async def update_character(
        character_id: str,
        character: SchemaAdminUpdateCharacter,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        character_db = await update_character_service_admin(character_id=character_id, character=character,
                                                            user_id=str(user_db["_id"]))
        return "Character updated"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not updated",
        )
