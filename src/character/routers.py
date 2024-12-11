from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from character.schemas import SchemaUpdateCharacterCollection, SchemaNewInteraction, SchemaDeactivateCharacter
from character.schemas import SchemaAddCharacterLocation
from character.schemas import SchemaUpdatedCharacterLocation
from character.schemas import SchemaCreateCharacter
from character.schemas import SchemaRetrieveCharacter
from character.schemas import SchemaListCharacter

from character.services import get_character_service, get_characters_service, new_interaction_character_service, \
    answer_open_question_service, deactivate_character_service
from character.services import generate_image_character_service
from character.services import create_character_service
from character.services import delete_character_service
from character.services import add_character_to_location_service
from character.services import get_characters_by_location_service
from character.services import add_or_edit_character_location
from character.services import get_all_character_service
from character.services import update_character_service

from game.services import get_character_game_publish_service
from game.services import get_location_game_publish_service

from user.services import disable_user_service

router = APIRouter(prefix='/characters', tags=['Characters'])


@router.get("/{character_id}", response_model=SchemaRetrieveCharacter)
async def get_character(
        character_id: str,
        publish: bool = False,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    if publish:
        try:
            game_id = character_id.split('_')[1]
            character_id = character_id.split('_')[0]
        except Exception as e:
            print(f"error in get character: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Character not found",
            )
        try:
            character_db = await get_character_game_publish_service(
                character_id=character_id, game_id=game_id
            )
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
        location_id: str = None,
        game_id: str = None,
        publish: bool = False,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    if publish:
        try:
            game_id = location_id.split("_")[-1]
            location_id = location_id.split("_")[0]
            locations_db = await get_location_game_publish_service(
                game_id=game_id, location_id=location_id
            )
            return SchemaListCharacter(
                results=locations_db["characters"], count=len(locations_db["characters"])
            )
        except Exception as e:
            print(f"error in get characters: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Characters publish not found",
            )
    else:
        try:
            if game_id:
                characters_db = await get_characters_service(
                    game_id=game_id, skip=1, limit=200
                )
            else:
                characters_db = await get_characters_by_location_service(
                    skip=1, limit=200, location_id=location_id
                )
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
    try:
        characters_db = await get_all_character_service(
            user_id=str(user_db.get("_id")), skip=page, limit=count
        )
        # for i in characters_db:
        #     i["_id"] = str(i["_id"])
        return SchemaListCharacter(results=characters_db, count=len(characters_db))
    except Exception as e:
        print(f"error in get characters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Characters not found",
        )


# @router.get("/{character_id}/generate-face/", response_model=SchemaRetrieveCharacter)
# async def get_images_character_face(
#     character_id: str,
#     user_db: dict = Depends(auth),
#     Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     try:
#         character_db = await generate_image_character_service(character_id=character_id)
#         await disable_user_service(user_id=str(user_db.get("_id")), section="character")
#         return character_db
#     except Exception as e:
#         print(f"error in get characters: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Characters not found",
#         )


@router.post("/", response_model=SchemaRetrieveCharacter)
async def create_character(
        character: SchemaCreateCharacter,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        character_db = await create_character_service(
            character=character,
            user_id=str(user_db.get("_id")),
            game_id=character.game_id,
        )
        return character_db
    except Exception as e:
        print(f"error in create character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not created",
        )


# @router.post("/add-character-location/")
# async def add_character_location(
#         character_location: SchemaAddCharacterLocation,
#         user_db: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     try:
#         if character_db := await add_character_to_location_service(
#                 character_id=character_location.character_id, location_id=character_location.location_id
#         ):
#             return character_db
#     except HTTPException as e:
#         print(f"error in create character: {str(e)}")
#         raise HTTPException(
#             status_code=e.status_code,
#             detail=e.detail,
#         )


@router.post("/add-edit-characteristic/")
async def add_edit_characteristic(
        character: SchemaUpdatedCharacterLocation,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        if character_db := await add_or_edit_character_location(
                character_id=character.character_id,
                location_id=character.location_id,
                game_id=character.game_id,
                state_game=character.state_game,
                characteristics=character.characteristics,
                user_id=str(user_db.get("_id")),
        ):
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
    try:
        character_db = await update_character_service(
            character_id=character_id,
            name=character_update.name,
            options_dialog=character_update.options_dialog,
            prompt_user=character_update.prompt_user,
            user_id=str(user_db.get("_id")),
            type_dialog=character_update.conversation_type,
            dialog=character_update.prompt_user_dialog,
            game_id=character_update.game_id,
            location_id=character_update.location_id,
            state_game=character_update.state_game,
        )
        return character_db
    except Exception as e:
        print(f"error in partial update character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not updated",
        )


@router.post("/{character_id}/generate-interaction/", response_model=SchemaRetrieveCharacter)
async def generate_interaction_character(
        character_id: str,
        new_interaction: SchemaNewInteraction,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        character_db = await new_interaction_character_service(location_id=new_interaction.location_id,
                                                               game_id=new_interaction.game_id,
                                                               conversation_type=new_interaction.conversation_type,
                                                               prompt_user_dialog=new_interaction.prompt_user_dialog,
                                                               options_dialog=new_interaction.options_dialog,
                                                               user_id=str(user_db.get("_id")),
                                                               state_game=new_interaction.state_game,
                                                               character_id=character_id)
        return character_db
    except Exception as e:
        print(f"error in get characters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Characters not found",
        )


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
        character_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    await delete_character_service(character_id=character_id)
    return status.HTTP_204_NO_CONTENT


@router.post("/answer/open-question/{character_id}/{location_id}/")
async def answer_open_question(
        character_id: str,
        location_id: str,
        answer: dict = {"prompt_user_answer": "",
                        "state_game": ""},
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        character_db = await answer_open_question_service(character_id=character_id,
                                                          location_id=location_id,
                                                          prompt_user_answer=answer["prompt_user_answer"],
                                                          user_id=str(user_db.get("_id")),
                                                          state_game=answer["state_game"])

        return character_db
    except Exception as e:
        print(f"error in get character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not found",
        )


@router.post("/disable/{character_id}/")
async def disable_character(
        character_id: str,
        character: SchemaDeactivateCharacter,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        character_db = await deactivate_character_service(
            character_id=character_id, state_game=character.state_game, active=character.is_active
        )
        return {"message": "Location disabled or enabled"}
    except Exception as e:
        print(f"error in get character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not found",
        )