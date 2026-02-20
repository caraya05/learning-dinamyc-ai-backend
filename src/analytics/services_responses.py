"""
Servicio para gestionar respuestas y puntuaciones en sesiones de juego de analítica.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from core.database import db


# ============================================================================
# AGREGAR RESPUESTAS A UNA SESIÓN
# ============================================================================

async def add_response_to_session(
    session_id: str,
    question_id: str,
    question: str,
    answer: str,
    is_correct: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Agregar una respuesta a una sesión de juego existente.

    Args:
        session_id: ID de la sesión del juego (sessionId)
        question_id: ID único de la pregunta
        question: Texto de la pregunta
        answer: Respuesta proporcionada por el usuario
        is_correct: Si la respuesta es correcta (opcional)

    Returns:
        dict: Documento de analítica actualizado

    Raises:
        Exception: Si no se encuentra la sesión
    """
    new_response = {
        "questionId": question_id,
        "question": question,
        "answer": answer,
        "timestamp": datetime.now(timezone.utc),
        "isCorrect": is_correct
    }

    result = await db["analytics"].update_one(
        {"sessionId": session_id},
        {"$push": {"responses": new_response}}
    )


    if result.modified_count == 0:
        raise Exception(f"Sesión no encontrada: {session_id}")

    # Retornar el documento actualizado
    analytic = await db["analytics"].find_one({"sessionId": session_id})
    if analytic:
        analytic["_id"] = str(analytic["_id"])
    return analytic


# ============================================================================
# GESTIONAR PUNTUACIONES
# ============================================================================

async def update_session_score(
    session_id: str,
    score: int,
) -> Dict[str, Any]:
    """
    Actualizar la puntuación de una sesión de juego.

    Args:
        session_id: ID de la sesión del juego
        score: Valor numérico de puntuación

    Returns:
        dict: Documento de analítica actualizado

    Raises:
        Exception: Si no se encuentra la sesión o operación inválida
    """
    if score < 0:
        raise ValueError("La puntuación no puede ser negativa")


    result = await db["analytics"].update_one(
        {"sessionId": session_id},
        {"$set": {"score": score}}
    )

    if result.modified_count == 0:
        raise Exception(f"Sesión no encontrada: {session_id}")

    # Retornar el documento actualizado
    analytic = await db["analytics"].find_one({"sessionId": session_id})
    if analytic:
        analytic["_id"] = str(analytic["_id"])
    return analytic


__all__ = [
    "add_response_to_session",
    "update_session_score",
]

