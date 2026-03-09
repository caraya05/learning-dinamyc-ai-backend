"""
Servicio para gestionar actualizaciones de sesiones en analítica.

Este módulo proporciona funcionalidades para actualizar campos
de registros de analítica existentes con validaciones.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

from core.database import db
from analytics.exceptions import (
    AnalyticNotFoundError,
    InvalidScoreError,
    InvalidViewsError,
    InvalidLikesError,
    InvalidPlaysError,
    InvalidProgressError,
    InvalidDurationError,
    DatabaseError,
)

logger = logging.getLogger(__name__)


def _validate_update_fields(update_data: Dict[str, Any]) -> None:
    """
    Valida que todos los campos de actualización cumplan con las restricciones.

    Args:
        update_data: Diccionario con datos a actualizar

    Raises:
        InvalidScoreError: Si score es negativo
        InvalidViewsError: Si views es negativo
        InvalidLikesError: Si likes es negativo
        InvalidPlaysError: Si plays es negativo
        InvalidProgressError: Si progress no está en rango [1, 3]
        InvalidDurationError: Si duration es negativo
    """
    validations = {
        "score": (InvalidScoreError, "score debe ser >= 0"),
        "views": (InvalidViewsError, "views debe ser >= 0"),
        "likes": (InvalidLikesError, "likes debe ser >= 0"),
        "plays": (InvalidPlaysError, "plays debe ser >= 0"),
        "duration": (InvalidDurationError, "duration debe ser >= 0"),
    }

    for field, (exception_class, _) in validations.items():
        if field in update_data and update_data[field] is not None:
            if update_data[field] < 0:
                raise exception_class(update_data[field])

    # Validación especial para progress
    if "progress" in update_data and update_data["progress"] is not None:
        progress = update_data["progress"]
        if progress < 1 or progress > 3:
            raise InvalidProgressError(progress)


async def update_session_complete(
    session_id: str,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Actualiza todos los campos de una sesión de analítica.

    Valida que no se actualicen campos protegidos (_id, id) y
    que todos los valores cumplan con las restricciones de negocio.

    Args:
        session_id: ID de la sesión del juego
        update_data: Diccionario con los campos a actualizar

    Returns:
        dict: Documento de analítica actualizado

    Raises:
        AnalyticNotFoundError: Si no se encuentra la sesión
        InvalidScoreError: Si score es negativo
        InvalidViewsError: Si views es negativo
        InvalidLikesError: Si likes es negativo
        InvalidPlaysError: Si plays es negativo
        InvalidProgressError: Si progress está fuera de [1, 3]
        InvalidDurationError: Si duration es negativo
        DatabaseError: Si hay error en la operación de BD

    Example:
        >>> updated = await update_session_complete(
        ...     "sess_123",
        ...     {"score": 200, "completed": True}
        ... )
    """
    try:
        logger.info(f"Iniciando actualización de sesión: {session_id}")

        # Campos que no deben ser actualizados directamente (protegidos)
        protected_fields = {"_id", "id"}

        # Validar todos los campos
        _validate_update_fields(update_data)

        # Limpiar campos vacíos, None o protegidos
        cleaned_data = {
            k: v for k, v in update_data.items()
            if v is not None and k not in protected_fields
        }

        if not cleaned_data:
            logger.warning(
                f"Sin cambios para sesión {session_id}: "
                f"todos los campos eran None o protegidos"
            )
            # Si no hay datos para actualizar, retornar el documento actual
            analytic = await db["analytics"].find_one({"session_id": session_id})
            if not analytic:
                raise AnalyticNotFoundError(session_id, "session_id")
            analytic["_id"] = str(analytic["_id"])
            return analytic

        logger.debug(f"Campos a actualizar en sesión {session_id}: {list(cleaned_data.keys())}")

        result = await db["analytics"].update_one(
            {"session_id": session_id},
            {"$set": cleaned_data}
        )

        if result.matched_count == 0:
            logger.error(f"Sesión no encontrada: {session_id}")
            raise AnalyticNotFoundError(session_id, "session_id")

        logger.info(
            f"Sesión {session_id} actualizada: "
            f"{result.modified_count} documento(s) modificado(s)"
        )

        # Retornar el documento actualizado
        analytic = await db["analytics"].find_one({"session_id": session_id})
        if analytic:
            analytic["_id"] = str(analytic["_id"])

        return analytic

    except (
        AnalyticNotFoundError,
        InvalidScoreError,
        InvalidViewsError,
        InvalidLikesError,
        InvalidPlaysError,
        InvalidProgressError,
        InvalidDurationError,
    ):
        # Re-lanzar excepciones conocidas sin wrappear
        raise
    except Exception as e:
        logger.error(
            f"Error inesperado actualizando sesión {session_id}: {str(e)}",
            exc_info=True
        )
        raise DatabaseError("update_session_complete", str(e)) from e


__all__ = [
    "update_session_complete",
]

