from fastapi import APIRouter
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from characters_collection.services import create_character_collection_service
from characters_collection.services import get_characters_collection_service
from characters_collection.services import get_characters_collection_by_id_service
from characters_collection.schemas import SchemaListCharactersCollection
from characters_collection.schemas import SchemaRetrieveCharactersCollection

router = APIRouter(prefix="/collection-character", tags=["Collection Character"])


@router.get("/", response_model=SchemaListCharactersCollection)
async def get_characters_collection(user_db: dict = Depends(auth),
                                    Token: HTTPAuthorizationCredentials = Depends(auth_schema)):
    """
    This endpoint retrieves a list of characters collection.
    """
    return await get_characters_collection_service(user_id=str(user_db.get("_id")))


@router.get("/{collection_id}", response_model=SchemaRetrieveCharactersCollection)
async def get_characters_collection_by_id(collection_id: str,
                                          user_db: dict = Depends(auth),
                                          Token: HTTPAuthorizationCredentials = Depends(auth_schema)):
    """
    This endpoint retrieves a character collection by id.
    """

    collection_db = await get_characters_collection_by_id_service(collection_id)
    print(collection_db)
    return collection_db


@router.post("/", response_model=SchemaRetrieveCharactersCollection)
async def create_character_collection(prompt_user: str,
                                      name_character_collection: str,
                                      user_db: dict = Depends(auth),
                                      Token: HTTPAuthorizationCredentials = Depends(auth_schema)):
    """
    This endpoint creates a character collection.
    """
    collection_db = await create_character_collection_service(prompt_user=prompt_user,
                                                              name_character_collection=name_character_collection,
                                                              user_id=str(user_db.get("_id")))

    print(collection_db)
    return collection_db
