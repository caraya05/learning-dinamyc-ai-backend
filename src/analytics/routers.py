"""
Endpoints (routers) de la API para operaciones de analítica.

Este módulo define los endpoints REST para CRUD de analíticas,
con autenticación, validaciones y manejo de errores granular.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime

from analytics.services_responses import update_session_complete
from analytics.schemas import (
    AnalyticCreate,
    AnalyticDB,
    AnalyticListResponse,
    AnalyticUpdate,
)
from analytics.services import (
    create_analytic_service,
    get_analytics_by_user_service,
    get_analytics_by_game_service,
    query_analytics_service,
)
from analytics.exceptions import (
    AnalyticsException,
    AnalyticNotFoundError,
    InvalidAnalyticDataError,
    UnauthorizedAnalyticAccessError,
    DatabaseError,
)
from auth.auth import auth
from auth.utils import auth_schema

router = APIRouter(prefix="/analytics", tags=["Analytics"])
logger = logging.getLogger(__name__)


def _normalize_response(data: dict) -> dict:
    """
    Normaliza un documento de BD para la respuesta API.

    Convierte _id a id (si es necesario) y normaliza campos.

    Args:
        data: Documento de BD

    Returns:
        dict: Documento normalizado
    """
    if "_id" in data and "id" not in data:
        data["id"] = data.pop("_id")
    return data


def _check_analytic_ownership(analytic: dict, user_db: dict) -> None:
    """
    Verifica que el usuario sea propietario de la analítica.

    Args:
        analytic: Documento de analítica
        user_db: Información del usuario autenticado

    Raises:
        UnauthorizedAnalyticAccessError: Si el usuario no es propietario
    """
    user_id = str(user_db.get("_id"))
    analytic_user_id = str(analytic.get("user_id", ""))

    if analytic_user_id and analytic_user_id != user_id:
        logger.warning(
            f"Intento de acceso no autorizado: usuario {user_id} "
            f"intentó acceder a analítica de usuario {analytic_user_id}"
        )
        raise UnauthorizedAnalyticAccessError(user_id, analytic.get("id", "unknown"))


def _handle_analytics_error(
        error: Exception,
        operation: str,
        context: Optional[dict] = None
) -> HTTPException:
    """
    Mapea excepciones de analytics a respuestas HTTP apropiadas.

    Args:
        error: La excepción lanzada
        operation: Nombre de la operación que falló
        context: Contexto adicional para logging

    Returns:
        HTTPException: Excepción HTTP apropiada para el cliente
    """
    context = context or {}

    if isinstance(error, AnalyticNotFoundError):
        logger.warning(f"{operation} falló: analítica no encontrada")
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error)
        )

    elif isinstance(error, UnauthorizedAnalyticAccessError):
        logger.warning(f"{operation} falló: acceso no autorizado")
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error)
        )

    elif isinstance(error, InvalidAnalyticDataError):
        logger.warning(f"{operation} falló: datos inválidos - {str(error)}")
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error)
        )

    elif isinstance(error, DatabaseError):
        logger.error(f"{operation} falló: error de BD - {str(error)}")
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar la solicitud"
        )

    else:
        logger.error(
            f"{operation} falló: error inesperado - {str(error)}",
            exc_info=True
        )
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "/",
    response_model=AnalyticDB,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo registro de analítica",
    description="Crea un nuevo registro de sesión de juego con los datos proporcionados."
)
async def create_analytic(
        payload: AnalyticCreate,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Crea un nuevo registro de analítica.

    Requiere autenticación. El usuario_id se asigna automáticamente
    del token de autenticación.

    Todos los campos en el request body son OPCIONALES.

    Ejemplo de request body (todos estos son válidos):

    Ejemplo 1 (completo):
    {
        "game_id": "string",
        "session_id": "string",
        "start_time": "2026-02-25T16:18:59.524000",
        "progress": 1,
        "completed": false,
        "duration": 0,
        "score": 0,
        "responses": []
    }

    Ejemplo 2 (mínimo):
    {}

    Ejemplo 3 (parcial):
    {
        "game_id": "game_123",
        "score": 100
    }
    """
    try:
        logger.info(f"Creando analítica para usuario {user_db.get('_id')}")

        analytic = payload.dict()
        analytic["user_id"] = str(user_db.get("_id"))

        created = await create_analytic_service(analytic)

        # Normalizar respuesta
        created = _normalize_response(created)
        # Filtrar solo campos válidos del schema AnalyticDB
        valid_fields = AnalyticDB.__fields__
        return AnalyticDB(**{k: v for k, v in created.items() if k in valid_fields})

    except AnalyticsException as e:
        raise _handle_analytics_error(e, "create_analytic")
    except Exception as e:
        raise _handle_analytics_error(e, "create_analytic")


@router.get(
    "/user/{user_id}",
    response_model=AnalyticListResponse,
    summary="Obtener analíticas de un usuario",
    description="Retorna todas las analíticas de un usuario específico con paginación."
)
async def get_by_user(
        user_id: str,
        skip: int = Query(0, ge=0, description="Offset de paginación"),
        limit: int = Query(100, ge=1, le=1000, description="Límite de registros"),
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Obtiene analíticas de un usuario.

    Nota: Solo los propietarios y administradores pueden ver sus propias analíticas.

    Query parameters:
    - skip: int >= 0 (default: 0)
    - limit: int [1-1000] (default: 100)
    """
    try:
        # Validar permiso: usuario solo puede ver sus propias analíticas
        current_user_id = str(user_db.get("_id"))
        if str(user_id) != current_user_id:
            logger.warning(
                f"Intento de acceso cruzado: usuario {current_user_id} "
                f"intentó acceder a analíticas de {user_id}"
            )
            raise UnauthorizedAnalyticAccessError(current_user_id, user_id)

        logger.info(f"Obteniendo analíticas del usuario {user_id}")
        results, count = await get_analytics_by_user_service(user_id, skip=skip, limit=limit)

        normalized = [_normalize_response(r) for r in results]
        return AnalyticListResponse(
            results=[AnalyticDB(**r) for r in normalized],
            count=count,
            skip=skip,
            limit=limit
        )

    except AnalyticsException as e:
        raise _handle_analytics_error(e, "get_by_user", {"user_id": user_id})
    except Exception as e:
        raise _handle_analytics_error(e, "get_by_user", {"user_id": user_id})


@router.get(
    "/game/{game_id}",
    response_model=AnalyticListResponse,
    summary="Obtener analíticas de un juego",
    description="Retorna todas las analíticas de un juego específico con paginación."
)
async def get_by_game(
        game_id: str,
        skip: int = Query(0, ge=0, description="Offset de paginación"),
        limit: int = Query(100, ge=1, le=1000, description="Límite de registros"),
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Obtiene analíticas de un juego específico.

    Query parameters:
    - skip: int >= 0 (default: 0)
    - limit: int [1-1000] (default: 100)
    """
    try:
        logger.info(f"Obteniendo analíticas del juego {game_id}")
        results, count = await get_analytics_by_game_service(game_id, skip=skip, limit=limit)

        normalized = [_normalize_response(r) for r in results]
        return AnalyticListResponse(
            results=[AnalyticDB(**r) for r in normalized],
            count=count,
            skip=skip,
            limit=limit
        )

    except AnalyticsException as e:
        raise _handle_analytics_error(e, "get_by_game", {"game_id": game_id})
    except Exception as e:
        raise _handle_analytics_error(e, "get_by_game", {"game_id": game_id})


@router.get(
    "/query",
    response_model=AnalyticListResponse,
    summary="Consulta avanzada de analíticas",
    description="Permite filtrar analíticas por múltiples criterios."
)
async def query_analytics(
        user_id: Optional[str] = Query(None, description="Filtrar por usuario"),
        game_id: Optional[str] = Query(None, description="Filtrar por juego"),
        date_from: Optional[datetime] = Query(None, description="Fecha mínima"),
        date_to: Optional[datetime] = Query(None, description="Fecha máxima"),
        progress: Optional[int] = Query(None, ge=1, le=3, description="Progreso (1-3)"),
        completed: Optional[bool] = Query(None, description="Solo completadas"),
        skip: int = Query(0, ge=0, description="Offset de paginación"),
        limit: int = Query(100, ge=1, le=1000, description="Límite de registros"),
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Consulta avanzada de analíticas con múltiples filtros.

    Todos los filtros son opcionales. Se pueden combinar.
    """
    try:
        logger.info("Ejecutando consulta avanzada de analíticas")
        results, count = await query_analytics_service(
            user_id=user_id,
            game_id=game_id,
            date_from=date_from,
            date_to=date_to,
            progress=progress,
            completed=completed,
            skip=skip,
            limit=limit,
        )

        normalized = [_normalize_response(r) for r in results]
        return AnalyticListResponse(
            results=[AnalyticDB(**r) for r in normalized],
            count=count,
            skip=skip,
            limit=limit
        )

    except AnalyticsException as e:
        raise _handle_analytics_error(e, "query_analytics")
    except Exception as e:
        raise _handle_analytics_error(e, "query_analytics")


@router.put(
    "/session/{session_id}",
    response_model=AnalyticDB,
    status_code=status.HTTP_200_OK,
    summary="Actualizar una sesión de analítica",
    description="Actualiza uno o varios campos de un registro de analítica."
)
async def update_analytics_complete(
        session_id: str,
        analytic_update: AnalyticUpdate,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        logger.info(f"Actualizando sesión {session_id}")

        update_dict = analytic_update.dict(exclude_unset=True)
        result = await update_session_complete(session_id, update_dict)

        # Normalizar respuesta
        result = _normalize_response(result)
        # Filtrar solo campos válidos del schema AnalyticDB
        valid_fields = AnalyticDB.__fields__
        return AnalyticDB(**{k: v for k, v in result.items() if k in valid_fields})

    except AnalyticsException as e:
        raise _handle_analytics_error(e, "update_analytics_complete", {"session_id": session_id})
    except Exception as e:
        raise _handle_analytics_error(e, "update_analytics_complete", {"session_id": session_id})
