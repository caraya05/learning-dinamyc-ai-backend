"""
Modelos Pydantic para la capa de datos de analíticas.

Este módulo define el modelo de dominio utilizado en la aplicación.
Los nombres aquí siguen la convención snake_case para consistencia.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from analytics.schemas import ProgressEnum, UserResponseSchema


class Analytic(BaseModel):
    """
    Modelo de analítica que representa una sesión de juego.

    Attributes:
        game_id: ID del juego jugado
        session_id: ID único de la sesión
        start_time: Hora de inicio de la sesión
        end_time: Hora de finalización de la sesión (opcional)
        progress: Nivel de progreso alcanzado (1-3)
        completed: Booleano indicando si la sesión fue completada
        duration: Duración total en segundos
        score: Puntuación obtenida
        user_id: ID del usuario que jugó (opcional)
        created_at: Fecha de creación del registro (opcional)
        responses: Lista de respuestas del usuario (opcional)
        views: Cantidad de vistas (opcional)
        likes: Cantidad de likes (opcional)
        plays: Cantidad de reproducciones (opcional)
    """
    game_id: str = Field(..., description="ID del juego")
    session_id: Optional[str] = Field(default=None, description="ID de la sesión")
    start_time: datetime = Field(..., description="Hora de inicio")
    end_time: Optional[datetime] = Field(default=None, description="Hora de finalización")
    progress: ProgressEnum = Field(..., description="Progreso (1-3)")
    completed: bool = Field(default=False, description="Completado")
    duration: int = Field(default=0, ge=0, description="Duración en segundos")
    score: int = Field(default=0, ge=0, description="Puntuación")
    user_id: Optional[str] = Field(default=None, description="ID del usuario")
    created_at: Optional[datetime] = Field(default=None, description="Fecha de creación")
    responses: Optional[List[UserResponseSchema]] = Field(default=None, description="Respuestas")
    views: Optional[int] = Field(default=0, ge=0, description="Vistas")
    likes: Optional[int] = Field(default=0, ge=0, description="Likes")
    plays: Optional[int] = Field(default=0, ge=0, description="Reproducciones")

    class Config:
        """Configuración del modelo."""
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "game_id": "68fb8fa10a03fc50ec57a672",
                "session_id": "sess_123456",
                "start_time": "2026-02-25T14:12:00Z",
                "end_time": "2026-02-25T14:22:20Z",
                "progress": 2,
                "completed": True,
                "duration": 620,
                "score": 150,
                "user_id": "664cc1d9f4fcb10d908de3a6",
                "created_at": "2026-02-25T14:12:00Z"
            }
        }

