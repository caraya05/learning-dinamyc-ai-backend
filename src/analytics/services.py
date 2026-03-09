"""
Servicios (capa de negocio) para operaciones de analíticas.

Este módulo contiene la lógica de negocio para CRUD y consultas
de registros de analítica en la base de datos.
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Optional
from datetime import datetime, timezone
from bson import ObjectId

from core.database import db
from analytics.exceptions import (
    AnalyticNotFoundError,
    InvalidProgressError,
    DatabaseError,
)
from analytics.schemas import ProgressEnum

logger = logging.getLogger(__name__)


async def create_analytic_service(analytic_data: dict) -> dict:
    """
    Inserta un nuevo registro de analítica en la colección `analytics`.

    Args:
        analytic_data: Diccionario con los datos de la analítica.
                      Debe contener: game_id, session_id, start_time, progress, user_id

    Returns:
        dict: El documento creado con su ID convertido a string

    Raises:
        DatabaseError: Si falla la operación de insert
        InvalidProgressError: Si el progreso está fuera de rango

    Example:
        >>> data = {
        ...     "game_id": "123",
        ...     "session_id": "sess_123",
        ...     "start_time": datetime.now(),
        ...     "progress": 1,
        ...     "user_id": "user_123"
        ... }
        >>> analytic = await create_analytic_service(data)
    """
    try:
        # Validaciones
        if "progress" in analytic_data and analytic_data["progress"]:
            try:
                progress_val = int(analytic_data["progress"])
                if progress_val < 1 or progress_val > 3:
                    raise InvalidProgressError(progress_val)
            except (ValueError, TypeError) as e:
                raise InvalidProgressError(-1) from e

        # Agregar timestamp de creación
        analytic_data["created_at"] = datetime.now(timezone.utc)

        logger.info(
            f"Creando analítica para usuario {analytic_data.get('user_id')} "
            f"y sesión {analytic_data.get('session_id')}"
        )

        result = await db["analytics"].insert_one(analytic_data)
        analytic = await db["analytics"].find_one({"_id": result.inserted_id})

        if not analytic:
            raise DatabaseError("insert_one", "No se pudo recuperar el documento insertado")

        # Normalizar _id a string
        analytic["_id"] = str(analytic["_id"])

        logger.info(f"Analítica creada exitosamente con ID: {analytic['_id']}")
        return analytic

    except (InvalidProgressError, DatabaseError):
        raise
    except Exception as e:
        logger.error(f"Error creando analítica: {str(e)}", exc_info=True)
        raise DatabaseError("create_analytic", str(e)) from e


async def get_analytics_by_user_service(
    user_id: str,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[dict], int]:
    """
    Obtiene todos los registros de analítica de un usuario específico.

    Args:
        user_id: ID del usuario propietario de las analíticas
        skip: Cantidad de registros a saltar (offset)
        limit: Cantidad máxima de registros a retornar

    Returns:
        Tuple[List[dict], int]: Lista de documentos y cantidad total de registros

    Raises:
        DatabaseError: Si falla la operación de lectura

    Example:
        >>> results, count = await get_analytics_by_user_service("user_123", skip=0, limit=10)
        >>> print(f"Total: {count}, Retornados: {len(results)}")
    """
    try:
        query = {"user_id": str(user_id)}

        logger.debug(f"Consultando analíticas para usuario: {user_id}")

        cursor = (
            db["analytics"]
            .find(query)
            .skip(skip)
            .limit(limit)
            .sort("created_at", -1)
        )

        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)

        count = await db["analytics"].count_documents(query)

        logger.info(
            f"Se obtuvieron {len(results)} analíticas "
            f"(total disponibles: {count}) del usuario {user_id}"
        )
        return results, count

    except Exception as e:
        logger.error(
            f"Error obteniendo analíticas del usuario {user_id}: {str(e)}",
            exc_info=True
        )
        raise DatabaseError("get_by_user", str(e)) from e


async def get_analytics_by_game_service(
    game_id: str,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[dict], int]:
    """
    Obtiene todos los registros de analítica de un juego específico.

    Args:
        game_id: ID del juego
        skip: Cantidad de registros a saltar (offset)
        limit: Cantidad máxima de registros a retornar

    Returns:
        Tuple[List[dict], int]: Lista de documentos y cantidad total de registros

    Raises:
        DatabaseError: Si falla la operación de lectura

    Example:
        >>> results, count = await get_analytics_by_game_service("game_123", skip=0, limit=50)
    """
    try:
        query = {"game_id": str(game_id)}

        logger.debug(f"Consultando analíticas para juego: {game_id}")

        cursor = (
            db["analytics"]
            .find(query)
            .skip(skip)
            .limit(limit)
            .sort("created_at", -1)
        )

        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)

        count = await db["analytics"].count_documents(query)

        logger.info(
            f"Se obtuvieron {len(results)} analíticas "
            f"(total disponibles: {count}) del juego {game_id}"
        )
        return results, count

    except Exception as e:
        logger.error(
            f"Error obteniendo analíticas del juego {game_id}: {str(e)}",
            exc_info=True
        )
        raise DatabaseError("get_by_game", str(e)) from e


async def query_analytics_service(
    user_id: Optional[str] = None,
    game_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    progress: Optional[int] = None,
    completed: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[dict], int]:
    """
    Consulta avanzada de analíticas con múltiples filtros opcionales.

    Args:
        user_id: ID del usuario (opcional)
        game_id: ID del juego (opcional)
        date_from: Fecha inicial (inclusive)
        date_to: Fecha final (inclusive)
        progress: Nivel de progreso (1, 2 o 3)
        completed: Filtrar por estado de completitud
        skip: Offset de paginación
        limit: Límite de registros

    Returns:
        Tuple[List[dict], int]: Lista de documentos y cantidad total

    Raises:
        InvalidProgressError: Si el progreso está fuera de rango
        DatabaseError: Si falla la operación de lectura

    Example:
        >>> results, count = await query_analytics_service(
        ...     user_id="user_123",
        ...     game_id="game_456",
        ...     completed=True,
        ...     skip=0,
        ...     limit=20
        ... )
    """
    try:
        query = {}

        # Validar y construir filtros
        if user_id:
            query["user_id"] = str(user_id)

        if game_id:
            query["game_id"] = str(game_id)

        if date_from or date_to:
            query["created_at"] = {}
            if date_from:
                query["created_at"]["$gte"] = date_from
            if date_to:
                query["created_at"]["$lte"] = date_to

        if progress is not None:
            try:
                progress_val = int(progress)
                if progress_val < 1 or progress_val > 3:
                    raise InvalidProgressError(progress_val)
                query["progress"] = progress_val
            except ValueError as e:
                raise InvalidProgressError(-1) from e

        if completed is not None:
            query["completed"] = bool(completed)

        logger.debug(f"Ejecutando consulta con filtros: {query}")

        cursor = (
            db["analytics"]
            .find(query)
            .skip(skip)
            .limit(limit)
            .sort("created_at", -1)
        )

        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)

        count = await db["analytics"].count_documents(query)

        logger.info(
            f"Consulta completada: {len(results)} resultados "
            f"(total disponibles: {count})"
        )
        return results, count

    except InvalidProgressError:
        raise
    except Exception as e:
        logger.error(f"Error en consulta de analíticas: {str(e)}", exc_info=True)
        raise DatabaseError("query_analytics", str(e)) from e


__all__ = [
    "create_analytic_service",
    "get_analytics_by_user_service",
    "get_analytics_by_game_service",
    "query_analytics_service",
]

