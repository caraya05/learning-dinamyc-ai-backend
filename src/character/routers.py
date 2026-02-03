from typing import Optional, Union
import json
from fastapi import APIRouter
from fastapi import File
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi import UploadFile
from fastapi import Request
from fastapi import Form
from fastapi import Body

from fastapi.security import HTTPAuthorizationCredentials

import traceback

from auth.auth import auth
from auth.utils import auth_schema


from character.schemas import (
    SchemaUpdateCharacterCollection,
    SchemaNewInteraction,
    SchemaDeactivateCharacter,
    SchemaResponseQuestionOpen, SchemaResponseTalkOpen, SchemaOpenTalk, SchemaOpenAnswer, SchemaOptionMultiple,
)
from character.schemas import SchemaUpdatedCharacterLocation
from character.schemas import SchemaCreateCharacter
from character.schemas import SchemaRetrieveCharacter
from character.schemas import SchemaListCharacter

from game.text_update_schemas import (
    SchemaUpdateCharacterData,
    SchemaCharacterStateDataResponse,
    SchemaUpdateDialog,
    SchemaDialogResponse,
    SchemaUpdateOptionQuestion,
    SchemaOptionQuestionResponse,
    SchemaUpdateOptionAnswer,
    SchemaOptionAnswerResponse,
    SchemaUpdateOptionGuideline,
    SchemaOptionGuidelineResponse,
    SchemaUpdateOpenQuestionDialog,
    SchemaOpenQuestionDialogResponse,
)

from character.services import (
    get_character_service,
    get_characters_service,
    new_interaction_character_service,
    answer_open_question_service,
    deactivate_character_service, answer_open_talk_service,
)
from character.services import create_character_service
from character.services import delete_character_service
from character.services import get_characters_by_location_service
from character.services import add_or_edit_character_location
from character.services import get_all_character_service
from character.services import update_character_service

from character.text_update_services import CharacterTextUpdateService
from character.image_update_services import CharacterImageUpdateService
from character.audio_update_services import CharacterAudioUpdateService

from game.services import GameService

router = APIRouter(prefix='/characters', tags=['Characters'])


@router.get("/{character_id}", response_model=SchemaRetrieveCharacter)
async def get_character(
        character_id: str,
        publish: bool = False,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        game_service = Depends(GameService)
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
            character_db = await game_service.get_character_game_publish_service(
                character_id=character_id, game_id=game_id
            )

            print(character_db)
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
        game_service = Depends(GameService)
):
    if publish:
        try:
            game_id = location_id.split("_")[-1]
            location_id = location_id.split("_")[0]
            locations_db = await game_service.get_location_game_publish_service(
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
                characters_db = await get_characters_service(game_id=game_id, skip=1, limit=200)
            elif location_id:
                characters_db = await get_characters_by_location_service(
                    skip=1, limit=200, location_id=location_id
                )
            else:
                characters_db = await get_characters_service(
                    skip=1, limit=200, user_id=str(user_db.get("_id"))
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
        request: Request,
        name: Optional[str] = Form(None, max_length=100, example="Jhon Doe"),
        prompt_user: Optional[str] = Form(None, example="prompt_user"),
        prompt_user_dialog: Optional[str] = Form(None),
        conversation_type: Optional[str] = Form(None),
        options_dialog: Optional[str] = Form(None),
        game_id: Optional[str] = Form(None, example="location_id"),
        location_id: Optional[str] = Form(None, example="location_id"),
        state_game: Optional[str] = Form(None, example="state_game"),
        file: Optional[UploadFile] = File(None),
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        # Intenta procesar el cuerpo como JSON
        try:
            json_body = await request.json()
            name = json_body.get("name")
            prompt_user = json_body.get("prompt_user")
            prompt_user_dialog = json_body.get("prompt_user_dialog")
            conversation_type = json_body.get("conversation_type")
            options_dialog = json_body.get("options_dialog")
            game_id = json_body.get("game_id")
            location_id = json_body.get("location_id")
            state_game = json_body.get("state_game")
        except Exception:
            # Si no es JSON, los datos se procesan como form-data
            pass

        # print(f"Creating character with name: {name}, "
        #       f"game_id: {game_id},"
        #       f" location_id: {location_id}, "
        #       f"state_game: {state_game}, prompt_user: {prompt_user},"
        #       f" prompt_user_dialog: {prompt_user_dialog},"
        #       f" conversation_type: {conversation_type}, "
        #       f"options_dialog: {options_dialog},"
        #       f" file: {file}")

        if options_dialog:
            options_dialog = json.loads(options_dialog)

            if isinstance(options_dialog, (SchemaOpenTalk, SchemaOptionMultiple, SchemaOpenAnswer)):
                options_dialog = options_dialog.dict()
            elif isinstance(options_dialog, dict):
                pass  # El valor ya es un diccionario válido
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="options_dialog debe ser un diccionario válido."
                )

        character_db = await create_character_service(
            character=SchemaCreateCharacter(
                name=name,
                prompt_user=prompt_user,
                prompt_user_dialog=prompt_user_dialog,
                conversation_type=conversation_type,
                options_dialog=options_dialog,
                game_id=game_id,
                location_id=location_id,
                state_game=state_game
            ),
            user_id=str(user_db.get("_id")),
            game_id=game_id,
            file=file
        )
        return character_db
    except Exception as e:
        print(traceback.print_exc())
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
    character_db = await update_character_service(
        character_id=character_id,
        name=character_update.name,
        options_dialog=(
            character_update.options_dialog.dict() if character_update.options_dialog else None
        ),
        prompt_user=character_update.prompt_user,
        user_id=str(user_db.get("_id")),
        type_dialog=character_update.conversation_type,
        dialog=character_update.prompt_user_dialog,
        game_id=character_update.game_id,
        location_id=character_update.location_id,
        state_game=character_update.state_game,
    )
    return character_db


@router.post("/{character_id}/generate-interaction/", response_model=SchemaRetrieveCharacter)
async def generate_interaction_character(
        character_id: str,
        new_interaction: SchemaNewInteraction,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        character_db = await new_interaction_character_service(
            location_id=new_interaction.location_id,
            game_id=new_interaction.game_id,
            conversation_type=new_interaction.conversation_type,
            conversation=new_interaction.conversation,
            options_dialog=new_interaction.options_dialog,
            user_id=str(user_db.get("_id")),
            state_game=new_interaction.state_game,
            character_id=character_id,
        )
        return character_db
    except Exception as e:
        print(traceback.format_exc())
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
        answer: SchemaResponseQuestionOpen,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    character_db = await answer_open_question_service(
        character_id=character_id,
        location_id=location_id,
        prompt_user_answer=answer.prompt_user_answer,
        user_id=str(user_db.get("_id")),
        state_game=answer.state_game,
    )

    return character_db


@router.post("/answer/open-talk/{character_id}/{location_id}/")
async def answer_open_talk(
        character_id: str,
        location_id: str,
        answer: SchemaResponseTalkOpen,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    character_db = await answer_open_talk_service(
        character_id=character_id,
        location_id=location_id,
        prompt_user_answer=answer.prompt_user_answer,
        user_id=str(user_db.get("_id")),
        state_game=answer.state_game,
        id_conversation=answer.id_conversation,
    )

    return character_db


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
        return {"message": character_db}
    except Exception as e:
        print(f"error in get character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not found",
        )

# class SchemaResponsePromptOpen(BaseModel):
#     response: str
# @router.post("/test-prompt/")
# async def test_prompt(
#         prompt: str,
# ):
#     try:
#
#         # response = await openai_generator.moderation_text(text=prompt)
#         # if response:
#         #     return {"response": "Prompt is not allowed"}
#         try:
#             # response = await openai_generator.generate_gpt(content_prompt=[
#             #     {
#             #         "role": "user",
#             #         "content": [
#             #             {
#             #                 "type": "text",
#             #                 "text": f"Prompt: {prompt}",
#             #             },
#             #         ],
#             #     },
#             # ],
#             # response_format=SchemaResponsePromptOpen)
#             response = await openai_generator.generate_image(prompt=prompt)
#             return {"response": response}
#
#         except Exception as e:
#             print(f"error in get character: {e}")
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=e,
#             )
#     except Exception as e:
#         print(f"error in get character 2: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Character not found",
#         )


# ============ CHARACTER TEXT UPDATE ENDPOINTS ============

def get_character_text_service():
    """Inyección de dependencias para el servicio de personalización de textos"""
    return CharacterTextUpdateService()


@router.patch(
    "/{character_id}/state/{state_id}/",
    status_code=status.HTTP_200_OK,
    response_model=SchemaCharacterStateDataResponse,
    tags=["Characters"]
)
async def update_character_data(
    character_id: str,
    state_id: str,
    request: SchemaUpdateCharacterData,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterTextUpdateService = Depends(get_character_text_service)
):
    """Actualiza datos de un personaje (nombre y/o descripción)"""
    try:
        if not request.name and not request.description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Validation Error", "message": "At least one field is required", "code": "VALIDATION_ERROR"}
            )

        user_id = str(user.get("_id"))
        result = await service.update_character_data(character_id, state_id, request.dict(exclude_unset=True), user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/dialog/{dialog_index}/",
    status_code=status.HTTP_200_OK,
    response_model=SchemaDialogResponse,
    tags=["Characters"]
)
async def update_interaction_dialog(
    character_id: str,
    state_id: str,
    interaction_index: int,
    dialog_index: int,
    request: SchemaUpdateDialog,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterTextUpdateService = Depends(get_character_text_service)
):
    """Actualiza el diálogo de una interacción"""
    try:
        if not request.dialog or not request.dialog.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "Validation Error", "code": "VALIDATION_ERROR"})

        user_id = str(user.get("_id"))
        result = await service.update_interaction_dialog(character_id, state_id, interaction_index, dialog_index, request.dialog, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/question/",
    status_code=status.HTTP_200_OK,
    response_model=SchemaOptionQuestionResponse,
    tags=["Characters"]
)
async def update_option_question(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    request: SchemaUpdateOptionQuestion,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterTextUpdateService = Depends(get_character_text_service)
):
    """Actualiza la pregunta de una opción"""
    try:
        if not request.dialog or not request.dialog.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "Validation Error", "code": "VALIDATION_ERROR"})

        user_id = str(user.get("_id"))
        result = await service.update_option_question(character_id, state_id, interaction_index, option_index, request.dialog, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/answer/",
    status_code=status.HTTP_200_OK,
    response_model=SchemaOptionAnswerResponse,
    tags=["Characters"]
)
async def update_option_answer(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    request: SchemaUpdateOptionAnswer,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterTextUpdateService = Depends(get_character_text_service)
):
    """Actualiza la respuesta de una opción"""
    try:
        if not request.dialog or not request.dialog.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "Validation Error", "code": "VALIDATION_ERROR"})

        user_id = str(user.get("_id"))
        result = await service.update_option_answer(character_id, state_id, interaction_index, option_index, request.dialog, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/guideline/",
    status_code=status.HTTP_200_OK,
    response_model=SchemaOptionGuidelineResponse,
    tags=["Characters"]
)
async def update_option_guideline(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    request: SchemaUpdateOptionGuideline,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterTextUpdateService = Depends(get_character_text_service)
):
    """Actualiza la guía de una opción"""
    try:
        if not request.guideline or not request.guideline.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "Validation Error", "code": "VALIDATION_ERROR"})

        user_id = str(user.get("_id"))
        result = await service.update_option_guideline(character_id, state_id, interaction_index, option_index, request.guideline, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/question/{question_index}/",
    status_code=status.HTTP_200_OK,
    response_model=SchemaOpenQuestionDialogResponse,
    tags=["Characters"]
)
async def update_open_question_dialog(
    character_id: str,
    state_id: str,
    interaction_index: int,
    question_index: int,
    request: SchemaUpdateOpenQuestionDialog,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterTextUpdateService = Depends(get_character_text_service)
):
    """Actualiza el diálogo de una pregunta abierta"""
    try:
        if not request.dialog or not request.dialog.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "Validation Error", "code": "VALIDATION_ERROR"})

        user_id = str(user.get("_id"))
        result = await service.update_open_question_dialog(character_id, state_id, interaction_index, question_index, request.dialog, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


# ============ CHARACTER IMAGE UPDATE ENDPOINTS ============

def get_character_image_service():
    """Inyección de dependencias para el servicio de imágenes de personajes"""
    return CharacterImageUpdateService()


@router.patch(
    "/{character_id}/state/{state_id}/full-image/",
    status_code=status.HTTP_200_OK,
    tags=["Characters"]
)
async def update_character_full_image(
    character_id: str,
    state_id: str,
    image: UploadFile = File(..., description="Full body image (1024x1024px, max 4MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterImageUpdateService = Depends(get_character_image_service)
):
    """Actualiza la imagen completa (full body) de un personaje"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_character_full_image(character_id, state_id, image, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/description-image/",
    status_code=status.HTTP_200_OK,
    tags=["Characters"]
)
async def update_character_description_image(
    character_id: str,
    state_id: str,
    image: UploadFile = File(..., description="Description image (1024x576px, max 3MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterImageUpdateService = Depends(get_character_image_service)
):
    """Actualiza la imagen de descripción de un personaje"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_character_description_image(character_id, state_id, image, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/image/",
    status_code=status.HTTP_200_OK,
    tags=["Characters"]
)
async def update_character_image(
    character_id: str,
    state_id: str,
    image: UploadFile = File(..., description="Character avatar image (512x512px, max 3MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterImageUpdateService = Depends(get_character_image_service)
):
    """Actualiza la foto/avatar de un personaje"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_character_image(character_id, state_id, image, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


# ============ CHARACTER OPTION TEXT UPDATE ENDPOINTS ============

@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/question/",
    status_code=status.HTTP_200_OK,
    tags=["Characters"]
)
async def update_option_question_text(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    dialog: str = Body(..., embed=True),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterTextUpdateService = Depends(get_character_text_service)
):
    """Actualiza el texto de la pregunta de una opción"""
    try:
        if not dialog or not dialog.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "Validation Error", "code": "VALIDATION_ERROR"})

        user_id = str(user.get("_id"))
        result = await service.update_option_question(character_id, state_id, interaction_index, option_index, dialog, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/answer/",
    status_code=status.HTTP_200_OK,
    tags=["Characters"]
)
async def update_option_answer_text(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    dialog: str = Body(..., embed=True),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterTextUpdateService = Depends(get_character_text_service)
):
    """Actualiza el texto de la respuesta de una opción"""
    try:
        if not dialog or not dialog.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "Validation Error", "code": "VALIDATION_ERROR"})

        user_id = str(user.get("_id"))
        result = await service.update_option_answer(character_id, state_id, interaction_index, option_index, dialog, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/guideline/",
    status_code=status.HTTP_200_OK,
    tags=["Characters"]
)
async def update_option_guideline_text(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    guideline: str = Body(..., embed=True),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterTextUpdateService = Depends(get_character_text_service)
):
    """Actualiza la guía de una opción"""
    try:
        if not guideline or not guideline.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "Validation Error", "code": "VALIDATION_ERROR"})

        user_id = str(user.get("_id"))
        result = await service.update_option_guideline(character_id, state_id, interaction_index, option_index, guideline, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


# ============ CHARACTER AUDIO UPDATE ENDPOINTS ============

from character.audio_update_services import CharacterAudioUpdateService


def get_character_audio_service():
    """Inyección de dependencias para el servicio de audios de personajes"""
    return CharacterAudioUpdateService()


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/dialog/{dialog_index}/audio/",
    status_code=status.HTTP_200_OK,
    tags=["Characters"]
)
async def update_dialog_audio(
    character_id: str,
    state_id: str,
    interaction_index: int,
    dialog_index: int,
    audio: UploadFile = File(..., description="Dialog audio (MP3/WAV/OGG/M4A, max 10MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterAudioUpdateService = Depends(get_character_audio_service)
):
    """Actualiza el audio de un diálogo de personaje"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_dialog_audio(character_id, state_id, interaction_index, dialog_index, audio, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/question/audio/",
    status_code=status.HTTP_200_OK,
    tags=["Characters"]
)
async def update_option_question_audio(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    audio: UploadFile = File(..., description="Option question audio (MP3/WAV/OGG/M4A, max 5MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterAudioUpdateService = Depends(get_character_audio_service)
):
    """Actualiza el audio de una pregunta de opción"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_option_question_audio(character_id, state_id, interaction_index, option_index, audio, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/answer/audio/",
    status_code=status.HTTP_200_OK,
    tags=["Characters"]
)
async def update_option_answer_audio(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    audio: UploadFile = File(..., description="Option answer audio (MP3/WAV/OGG/M4A, max 5MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterAudioUpdateService = Depends(get_character_audio_service)
):
    """Actualiza el audio de una respuesta de opción"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_option_answer_audio(character_id, state_id, interaction_index, option_index, audio, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/question/{question_index}/audio/",
    status_code=status.HTTP_200_OK,
    tags=["Characters"]
)
async def update_open_question_audio(
    character_id: str,
    state_id: str,
    interaction_index: int,
    question_index: int,
    audio: UploadFile = File(..., description="Open question audio (MP3/WAV/OGG/M4A, max 5MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterAudioUpdateService = Depends(get_character_audio_service)
):
    """Actualiza el audio de una pregunta abierta"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_open_question_audio(character_id, state_id, interaction_index, question_index, audio, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


# ============ CHARACTER VIDEO DELETE ENDPOINTS ============

from character.video_delete_services import CharacterInteractionVideoDeleteService


def get_character_video_delete_service():
    """Inyección de dependencias para el servicio de eliminación de videos de interacciones"""
    return CharacterInteractionVideoDeleteService()


@router.delete(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/video/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Characters"]
)
async def delete_interaction_video(
    character_id: str,
    state_id: str,
    interaction_index: int,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterInteractionVideoDeleteService = Depends(get_character_video_delete_service)
):
    """Elimina el video de una interacción"""
    try:
        user_id = str(user.get("_id"))
        await service.delete_interaction_video(character_id, state_id, interaction_index, user_id)
        return status.HTTP_204_NO_CONTENT

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


# ============ CHARACTER OPTION AUDIO ENDPOINTS ============

def get_character_audio_service():
    """Inyección de dependencias para el servicio de audio de personajes"""
    return CharacterAudioUpdateService()


@router.post(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/question/audio/",
    status_code=status.HTTP_200_OK,
    tags=["Characters - Option Audio"]
)
async def upload_option_question_audio(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    audio: UploadFile = File(...),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterAudioUpdateService = Depends(get_character_audio_service)
):
    """
    Sube un archivo de audio para la pregunta de una opción.

    - **character_id**: ID del personaje (ObjectId)
    - **state_id**: ID del estado del juego
    - **interaction_index**: Índice de la interacción (0, 1, 2...)
    - **option_index**: Índice de la opción (0, 1, 2...)
    - **audio**: Archivo de audio (MP3, WAV, OGG - Max 10MB)
    """
    try:
        user_id = str(user.get("_id"))
        result = await service.update_option_question_audio(
            character_id,
            state_id,
            interaction_index,
            option_index,
            audio,
            user_id
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.post(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/answer/audio/",
    status_code=status.HTTP_200_OK,
    tags=["Characters - Option Audio"]
)
async def upload_option_answer_audio(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    audio: UploadFile = File(...),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterAudioUpdateService = Depends(get_character_audio_service)
):
    """
    Sube un archivo de audio para la respuesta de una opción.

    - **character_id**: ID del personaje (ObjectId)
    - **state_id**: ID del estado del juego
    - **interaction_index**: Índice de la interacción (0, 1, 2...)
    - **option_index**: Índice de la opción (0, 1, 2...)
    - **audio**: Archivo de audio (MP3, WAV, OGG - Max 10MB)
    """
    try:
        user_id = str(user.get("_id"))
        result = await service.update_option_answer_audio(
            character_id,
            state_id,
            interaction_index,
            option_index,
            audio,
            user_id
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.delete(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/question/audio/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Characters - Option Audio"]
)
async def delete_option_question_audio(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterAudioUpdateService = Depends(get_character_audio_service)
):
    """
    Elimina el audio de la pregunta de una opción.

    - **character_id**: ID del personaje (ObjectId)
    - **state_id**: ID del estado del juego
    - **interaction_index**: Índice de la interacción
    - **option_index**: Índice de la opción
    """
    try:
        user_id = str(user.get("_id"))
        await service.delete_option_question_audio(
            character_id,
            state_id,
            interaction_index,
            option_index,
            user_id
        )
        return None

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.delete(
    "/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/answer/audio/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Characters - Option Audio"]
)
async def delete_option_answer_audio(
    character_id: str,
    state_id: str,
    interaction_index: int,
    option_index: int,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterAudioUpdateService = Depends(get_character_audio_service)
):
    """
    Elimina el audio de la respuesta de una opción.

    - **character_id**: ID del personaje (ObjectId)
    - **state_id**: ID del estado del juego
    - **interaction_index**: Índice de la interacción
    - **option_index**: Índice de la opción
    """
    try:
        user_id = str(user.get("_id"))
        await service.delete_option_answer_audio(
            character_id,
            state_id,
            interaction_index,
            option_index,
            user_id
        )
        return None

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


