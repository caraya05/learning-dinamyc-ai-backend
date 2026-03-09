"""
Esquemas Pydantic para validación y documentación de datos de analíticas.

Este módulo define los modelos de datos (schemas) utilizados en toda la API de analytics,
incluyendo creación, actualización, lectura y listado de registros de analítica.
"""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from pydantic import BaseModel, Field, validator
from typing import Optional, List


class ProgressEnum(IntEnum):
    """Enumeración de estados de progreso en sesiones de juego."""
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


class UserResponseSchema(BaseModel):
    """
    Schema que representa la respuesta de un usuario a una pregunta.

    Todos los campos son opcionales para permitir flexibilidad en el frontend.

    Attributes:
        question_id: ID único de la pregunta (opcional)
        question: Texto de la pregunta (opcional)
        answer: Respuesta del usuario (opcional)
        timestamp: Hora en que se respondió (opcional)
        is_correct: Booleano indicando si la respuesta es correcta (opcional)
    """
    question_id: Optional[str] = Field(default=None, description="ID único de la pregunta")
    question: Optional[str] = Field(default=None, description="Texto de la pregunta")
    answer: Optional[str] = Field(default=None, description="Respuesta del usuario")
    timestamp: Optional[datetime] = Field(default=None, description="Hora de la respuesta")
    is_correct: Optional[bool] = Field(default=None, description="Si la respuesta es correcta")

    class Config:
        """Configuración del schema."""
        schema_extra = {
            "example": {
                "question_id": "q123",
                "question": "¿Cuál es la capital de Colombia?",
                "answer": "Bogotá",
                "timestamp": "2026-02-25T16:18:59.524000",
                "is_correct": True
            }
        }


class AnalyticBase(BaseModel):
    """
    Schema base para registros de analítica.

    Contiene los campos comunes a creación, actualización y lectura.
    Todos los campos son opcionales para permitir actualizaciones parciales.
    """
    game_id: Optional[str] = Field(default=None, description="ID del juego")
    session_id: Optional[str] = Field(default=None, description="ID de la sesión")
    start_time: Optional[datetime] = Field(default=None, description="Hora de inicio")
    end_time: Optional[datetime] = Field(default=None, description="Hora de finalización")
    progress: Optional[ProgressEnum] = Field(default=None, description="Progreso (1-3)")
    completed: Optional[bool] = Field(default=None, description="Sesión completada")
    duration: Optional[int] = Field(default=None, ge=0, description="Duración en segundos")
    responses: Optional[List[UserResponseSchema]] = Field(default=None, description="Respuestas del usuario")
    score: Optional[int] = Field(default=None, ge=0, description="Puntuación total")
    views: Optional[int] = Field(default=None, ge=0, description="Cantidad de vistas")
    likes: Optional[int] = Field(default=None, ge=0, description="Cantidad de likes")
    plays: Optional[int] = Field(default=None, ge=0, description="Cantidad de reproducciones")


class AnalyticCreate(AnalyticBase):
    """
    Schema para creación de un nuevo registro de analítica.

    Todos los campos son opcionales. Se pueden enviar tantos o tan pocos campos
    como sea necesario desde el frontend.
    """
    game_id: Optional[str] = Field(default=None, description="ID del juego")
    session_id: Optional[str] = Field(default=None, description="ID de la sesión")
    start_time: Optional[datetime] = Field(default=None, description="Hora de inicio")
    progress: Optional[ProgressEnum] = Field(default=None, description="Progreso inicial (1-3)")

    @validator('duration')
    def validate_duration(cls, v):
        """Valida que la duración sea positiva si se proporciona."""
        if v is not None and v < 0:
            raise ValueError('La duración debe ser positiva')
        return v

    class Config:
        """Configuración del schema."""
        schema_extra = {
            "example": {
                "game_id": "68fb8fa10a03fc50ec57a672",
                "session_id": "sess_123456",
                "start_time": "2026-02-25T14:12:00Z",
                "progress": 1,
                "completed": False,
                "duration": 0,
                "score": 0
            }
        }


class AnalyticUpdate(BaseModel):
    """
    Schema para actualización de un registro de analítica.

    Todos los campos son opcionales. Solo se actualizan los campos enviados.
    Los campos 'id' y '_id' se ignoran si se envían.
    """
    game_id: Optional[str] = Field(default=None, description="ID del juego")
    session_id: Optional[str] = Field(default=None, description="ID de la sesión")
    start_time: Optional[datetime] = Field(default=None, description="Hora de inicio")
    end_time: Optional[datetime] = Field(default=None, description="Hora de finalización")
    progress: Optional[ProgressEnum] = Field(default=None, description="Progreso (1-3)")
    completed: Optional[bool] = Field(default=None, description="Sesión completada")
    duration: Optional[int] = Field(default=None, ge=0, description="Duración en segundos")
    responses: Optional[List[UserResponseSchema]] = Field(default=None, description="Respuestas del usuario")
    score: Optional[int] = Field(default=None, ge=0, description="Puntuación total")
    views: Optional[int] = Field(default=None, ge=0, description="Cantidad de vistas")
    likes: Optional[int] = Field(default=None, ge=0, description="Cantidad de likes")
    plays: Optional[int] = Field(default=None, ge=0, description="Cantidad de reproducciones")
    user_id: Optional[str] = Field(default=None, description="ID del usuario")
    created_at: Optional[datetime] = Field(default=None, description="Fecha de creación")

    class Config:
        """Configuración del schema."""
        extra = "ignore"  # Ignora campos extra como 'id' o '_id'


class AnalyticDB(AnalyticBase):
    """
    Schema que representa un documento de analítica retornado desde la BD.

    Incluye los campos de metadata como id, user_id y created_at.
    """
    id: Optional[str] = Field(default=None, alias="_id", description="ID del documento")
    user_id: Optional[str] = Field(default=None, description="ID del usuario propietario")
    created_at: Optional[datetime] = Field(default=None, description="Fecha de creación")

    class Config:
        """Configuración del schema."""
        allow_population_by_field_name = True  # Permite usar tanto 'id' como '_id'
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "game_id": "68fb8fa10a03fc50ec57a672",
                "session_id": "sess_123456",
                "start_time": "2026-02-25T14:12:00Z",
                "end_time": "2026-02-25T14:22:20Z",
                "progress": 2,
                "completed": True,
                "duration": 620,
                "score": 85,
                "user_id": "664cc1d9f4fcb10d908de3a6",
                "created_at": "2026-02-25T14:12:00Z"
            }
        }


class AnalyticListResponse(BaseModel):
    """
    Schema para la respuesta de listado de analíticas.

    Attributes:
        results: Lista de documentos de analítica
        count: Cantidad total de documentos (sin considerar paginación)
        skip: Cantidad de documentos saltados (offset)
        limit: Cantidad máxima de documentos retornados
    """
    results: List[AnalyticDB] = Field(..., description="Lista de registros de analítica")
    count: int = Field(..., ge=0, description="Total de registros disponibles")
    skip: int = Field(default=0, ge=0, description="Offset de la consulta")
    limit: int = Field(default=100, ge=1, le=1000, description="Límite de registros retornados")

    class Config:
        """Configuración del schema."""
        schema_extra = {
            "example": {
                "results": [],
                "count": 0,
                "skip": 0,
                "limit": 100
            }
        }

