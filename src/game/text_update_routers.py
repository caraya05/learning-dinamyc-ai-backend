"""
Routers para los endpoints de actualización de textos en juegos, personajes, locaciones y eventos.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

# Importar servicios de cada carpeta
from character.text_update_services import CharacterTextUpdateService
from location.text_update_services import LocationTextUpdateService
from game.text_update_services_game import GameTextUpdateService
from event.text_update_services import EventTextUpdateService

from game.text_update_schemas import (
    SchemaUpdateGameTitle,
    SchemaGameTitleResponse,
    SchemaUpdateCharacterData,
    SchemaCharacterStateDataResponse,
    SchemaUpdateLocationData,
    SchemaLocationStateDataResponse,
    SchemaUpdateDialog,
    SchemaDialogResponse,
    SchemaUpdateOptionQuestion,
    SchemaOptionQuestionResponse,
    SchemaUpdateOptionAnswer,
    SchemaOptionAnswerResponse,
    SchemaUpdateOptionGuideline,
    SchemaOptionGuidelineResponse,
    SchemaUpdateEvent,
    SchemaEventResponse,
    SchemaUpdateOpenQuestionDialog,
    SchemaOpenQuestionDialogResponse,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/api", tags=["Text Updates"])


def get_game_text_service():
    """Inyección de dependencias para el servicio de juegos"""
    return GameTextUpdateService()

def get_character_text_service():
    """Inyección de dependencias para el servicio de personajes"""
    return CharacterTextUpdateService()

def get_location_text_service():
    """Inyección de dependencias para el servicio de locaciones"""
    return LocationTextUpdateService()

def get_event_text_service():
    """Inyección de dependencias para el servicio de eventos"""
    return EventTextUpdateService()


# ============ 1. Update Game Title ============
@router.patch(
    "/game/{game_id}/title",
    status_code=status.HTTP_200_OK,
    response_model=SchemaGameTitleResponse,
    responses={
        404: {"description": "Game not found"},
        400: {"description": "Validation error"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
)
async def update_game_title(
    game_id: str,
    request: SchemaUpdateGameTitle,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: GameTextUpdateService = Depends(get_game_text_service)
):
    """
    Actualiza el título del juego/episodio.

    - **game_id**: ID del juego
    - **title**: Nuevo título del episodio
    """
    try:
        if not request.title or not request.title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": "Title cannot be empty",
                    "code": "VALIDATION_ERROR"
                }
            )

        user_id = str(user.get("_id"))
        result = await service.update_game_title(game_id, request.title, user_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)

        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": error_msg,
                    "code": "RESOURCE_NOT_FOUND"
                }
            )
        elif "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "You don't have permission to edit this game",
                    "code": "PERMISSION_DENIED"
                }
            )
        else:
            logger.error(f"Error updating game title: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An error occurred while updating the data",
                    "code": "INTERNAL_ERROR"
                }
            )
    """
    Actualiza el título del juego.

    - **game_id**: ID del juego
    - **title**: Nuevo título del episodio
    """
    try:
        # Validar que el título no esté vacío
        if not request.title or not request.title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": "Title cannot be empty",
                    "code": "VALIDATION_ERROR"
                }
            )

        user_id = str(user.get("_id"))
        result = await service.update_game_title(game_id, request.title, user_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)

        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": error_msg,
                    "code": "RESOURCE_NOT_FOUND"
                }
            )
        elif "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "You don't have permission to edit this game",
                    "code": "PERMISSION_DENIED"
                }
            )
        else:
            logger.error(f"Error updating game title: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An error occurred while updating the data",
                    "code": "INTERNAL_ERROR"
                }
            )


# ============ 2. Update Character Data ============
@router.patch(
    "/character/{character_id}/state/{state_id}",
    status_code=status.HTTP_200_OK,
    response_model=SchemaCharacterStateDataResponse,
    responses={
        404: {"description": "Character or state not found"},
        400: {"description": "Validation error"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
)
async def update_character_data(
    character_id: str,
    state_id: str,
    request: SchemaUpdateCharacterData,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: CharacterTextUpdateService = Depends(get_character_text_service)
):
    """
    Actualiza los datos de un personaje (nombre y/o descripción).

    - **character_id**: ID del personaje
    - **state_id**: ID del estado en state_glic
    - **name**: Nuevo nombre del personaje (opcional)
    - **description**: Nueva descripción del personaje (opcional)
    """
    try:
        # Validar que al menos un campo sea proporcionado
        if not request.name and not request.description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": "At least one field (name or description) must be provided",
                    "code": "VALIDATION_ERROR"
                }
            )

        user_id = str(user.get("_id"))
        data = {}
        if request.name:
            data['name'] = request.name
        if request.description:
            data['description'] = request.description

        result = await service.update_character_data(character_id, state_id, data, user_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)

        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": error_msg,
                    "code": "RESOURCE_NOT_FOUND"
                }
            )
        elif "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "You don't have permission to edit this game",
                    "code": "PERMISSION_DENIED"
                }
            )
        else:
            logger.error(f"Error updating character data: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An error occurred while updating the data",
                    "code": "INTERNAL_ERROR"
                }
            )


# ============ 3. Update Location Data ============
@router.patch(
    "/location/{location_id}/state/{state_id}",
    status_code=status.HTTP_200_OK,
    response_model=SchemaLocationStateDataResponse,
    responses={
        404: {"description": "Location or state not found"},
        400: {"description": "Validation error"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
)
async def update_location_data(
    location_id: str,
    state_id: str,
    request: SchemaUpdateLocationData,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: LocationTextUpdateService = Depends(get_location_text_service)
):
    """
    Actualiza los datos de una locación (título y/o descripción).

    - **location_id**: ID de la locación
    - **state_id**: ID del estado en state_glic
    - **title**: Nuevo nombre de la locación (opcional)
    - **description**: Nueva descripción de la locación (opcional)
    """
    try:
        # Validar que al menos un campo sea proporcionado
        if not request.title and not request.description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": "At least one field (title or description) must be provided",
                    "code": "VALIDATION_ERROR"
                }
            )

        user_id = str(user.get("_id"))
        data = {}
        if request.title:
            data['title'] = request.title
        if request.description:
            data['description'] = request.description

        result = await service.update_location_data(location_id, state_id, data, user_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)

        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": error_msg,
                    "code": "RESOURCE_NOT_FOUND"
                }
            )
        elif "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "You don't have permission to edit this game",
                    "code": "PERMISSION_DENIED"
                }
            )
        else:
            logger.error(f"Error updating location data: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An error occurred while updating the data",
                    "code": "INTERNAL_ERROR"
                }
            )


# ============ 4. Update Interaction Dialog ============
@router.patch(
    "/character/{character_id}/state/{state_id}/interaction/{interaction_index}/dialog/{dialog_index}",
    status_code=status.HTTP_200_OK,
    response_model=SchemaDialogResponse,
    responses={
        404: {"description": "Character or state not found"},
        400: {"description": "Validation error or invalid index"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
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
    """
    Actualiza el diálogo de una interacción de personaje.

    - **character_id**: ID del personaje
    - **state_id**: ID del estado en state_glic
    - **interaction_index**: Índice de la interacción
    - **dialog_index**: Índice del diálogo en la conversación
    - **dialog**: Nuevo texto del diálogo
    """
    try:
        # Validar que el diálogo no esté vacío
        if not request.dialog or not request.dialog.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": "Dialog text cannot be empty",
                    "code": "VALIDATION_ERROR"
                }
            )

        user_id = str(user.get("_id"))
        result = await service.update_interaction_dialog(
            character_id, state_id, interaction_index, dialog_index, request.dialog, user_id
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)

        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": error_msg,
                    "code": "RESOURCE_NOT_FOUND"
                }
            )
        elif "invalid" in error_msg.lower() or "index" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": error_msg,
                    "code": "VALIDATION_ERROR"
                }
            )
        elif "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "You don't have permission to edit this game",
                    "code": "PERMISSION_DENIED"
                }
            )
        else:
            logger.error(f"Error updating interaction dialog: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An error occurred while updating the data",
                    "code": "INTERNAL_ERROR"
                }
            )


# ============ 5. Update Option Question ============
@router.patch(
    "/character/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/question",
    status_code=status.HTTP_200_OK,
    response_model=SchemaOptionQuestionResponse,
    responses={
        404: {"description": "Character or state not found"},
        400: {"description": "Validation error or invalid index"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
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
    """
    Actualiza la pregunta de una opción múltiple.

    - **character_id**: ID del personaje
    - **state_id**: ID del estado en state_glic
    - **interaction_index**: Índice de la interacción
    - **option_index**: Índice de la opción
    - **dialog**: Nueva pregunta de opción
    """
    try:
        # Validar que el diálogo no esté vacío
        if not request.dialog or not request.dialog.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": "Dialog text cannot be empty",
                    "code": "VALIDATION_ERROR"
                }
            )

        user_id = str(user.get("_id"))
        result = await service.update_option_question(
            character_id, state_id, interaction_index, option_index, request.dialog, user_id
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)

        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": error_msg,
                    "code": "RESOURCE_NOT_FOUND"
                }
            )
        elif "invalid" in error_msg.lower() or "index" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": error_msg,
                    "code": "VALIDATION_ERROR"
                }
            )
        elif "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "You don't have permission to edit this game",
                    "code": "PERMISSION_DENIED"
                }
            )
        else:
            logger.error(f"Error updating option question: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An error occurred while updating the data",
                    "code": "INTERNAL_ERROR"
                }
            )


# ============ 6. Update Option Answer ============
@router.patch(
    "/character/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/answer",
    status_code=status.HTTP_200_OK,
    response_model=SchemaOptionAnswerResponse,
    responses={
        404: {"description": "Character or state not found"},
        400: {"description": "Validation error or invalid index"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
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
    """
    Actualiza la respuesta de una opción múltiple.

    - **character_id**: ID del personaje
    - **state_id**: ID del estado en state_glic
    - **interaction_index**: Índice de la interacción
    - **option_index**: Índice de la opción
    - **dialog**: Nueva respuesta de opción
    """
    try:
        # Validar que el diálogo no esté vacío
        if not request.dialog or not request.dialog.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": "Dialog text cannot be empty",
                    "code": "VALIDATION_ERROR"
                }
            )

        user_id = str(user.get("_id"))
        result = await service.update_option_answer(
            character_id, state_id, interaction_index, option_index, request.dialog, user_id
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)

        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": error_msg,
                    "code": "RESOURCE_NOT_FOUND"
                }
            )
        elif "invalid" in error_msg.lower() or "index" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": error_msg,
                    "code": "VALIDATION_ERROR"
                }
            )
        elif "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "You don't have permission to edit this game",
                    "code": "PERMISSION_DENIED"
                }
            )
        else:
            logger.error(f"Error updating option answer: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An error occurred while updating the data",
                    "code": "INTERNAL_ERROR"
                }
            )


# ============ 7. Update Option Guideline ============
@router.patch(
    "/character/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/guideline",
    status_code=status.HTTP_200_OK,
    response_model=SchemaOptionGuidelineResponse,
    responses={
        404: {"description": "Character or state not found"},
        400: {"description": "Validation error or invalid index"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
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
    """
    Actualiza la guía de una opción (para preguntas abiertas).

    - **character_id**: ID del personaje
    - **state_id**: ID del estado en state_glic
    - **interaction_index**: Índice de la interacción
    - **option_index**: Índice de la opción
    - **guideline**: Nueva guía para la respuesta abierta
    """
    try:
        # Validar que la guía no esté vacía
        if not request.guideline or not request.guideline.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": "Guideline text cannot be empty",
                    "code": "VALIDATION_ERROR"
                }
            )

        user_id = str(user.get("_id"))
        result = await service.update_option_guideline(
            character_id, state_id, interaction_index, option_index, request.guideline, user_id
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)

        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": error_msg,
                    "code": "RESOURCE_NOT_FOUND"
                }
            )
        elif "invalid" in error_msg.lower() or "index" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": error_msg,
                    "code": "VALIDATION_ERROR"
                }
            )
        elif "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "You don't have permission to edit this game",
                    "code": "PERMISSION_DENIED"
                }
            )
        else:
            logger.error(f"Error updating option guideline: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An error occurred while updating the data",
                    "code": "INTERNAL_ERROR"
                }
            )


# ============ 8. Update Event ============
@router.patch(
    "/event/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=SchemaEventResponse,
    responses={
        404: {"description": "Event not found"},
        400: {"description": "Validation error"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
)
async def update_event(
    event_id: str,
    request: SchemaUpdateEvent,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: EventTextUpdateService = Depends(get_event_text_service)
):
    """
    Actualiza los datos de un evento.

    - **event_id**: ID del evento
    - **text_image**: Texto que aparece en la imagen del evento (opcional)
    - **description**: Descripción del evento (opcional)
    - **prompt_user_text**: Texto adicional para el usuario (opcional)
    """
    try:
        # Validar que al menos un campo sea proporcionado
        if not request.text_image and not request.description and not request.prompt_user_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": "At least one field must be provided",
                    "code": "VALIDATION_ERROR"
                }
            )

        user_id = str(user.get("_id"))
        data = {}
        if request.text_image:
            data['text_image'] = request.text_image
        if request.description:
            data['description'] = request.description
        if request.prompt_user_text:
            data['prompt_user_text'] = request.prompt_user_text

        result = await service.update_event(event_id, data, user_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)

        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": error_msg,
                    "code": "RESOURCE_NOT_FOUND"
                }
            )
        elif "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "You don't have permission to edit this game",
                    "code": "PERMISSION_DENIED"
                }
            )
        else:
            logger.error(f"Error updating event: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An error occurred while updating the data",
                    "code": "INTERNAL_ERROR"
                }
            )


# ============ 9. Update Open Question Dialog ============
@router.patch(
    "/character/{character_id}/state/{state_id}/interaction/{interaction_index}/question/{question_index}",
    status_code=status.HTTP_200_OK,
    response_model=SchemaOpenQuestionDialogResponse,
    responses={
        404: {"description": "Character or state not found"},
        400: {"description": "Validation error or invalid index"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
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
    """
    Actualiza el diálogo de una pregunta abierta.

    - **character_id**: ID del personaje
    - **state_id**: ID del estado en state_glic
    - **interaction_index**: Índice de la interacción
    - **question_index**: Índice de la pregunta en prompt_user_question
    - **dialog**: Nuevo texto de la pregunta
    """
    try:
        # Validar que el diálogo no esté vacío
        if not request.dialog or not request.dialog.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": "Dialog text cannot be empty",
                    "code": "VALIDATION_ERROR"
                }
            )

        user_id = str(user.get("_id"))
        result = await service.update_open_question_dialog(
            character_id, state_id, interaction_index, question_index, request.dialog, user_id
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)

        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": error_msg,
                    "code": "RESOURCE_NOT_FOUND"
                }
            )
        elif "invalid" in error_msg.lower() or "index" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": error_msg,
                    "code": "VALIDATION_ERROR"
                }
            )
        elif "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "You don't have permission to edit this game",
                    "code": "PERMISSION_DENIED"
                }
            )
        else:
            logger.error(f"Error updating open question dialog: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal Server Error",
                    "message": "An error occurred while updating the data",
                    "code": "INTERNAL_ERROR"
                }
            )
