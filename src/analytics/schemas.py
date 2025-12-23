

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List


class UserResponse(BaseModel):
    """Modelo para una respuesta del usuario a una pregunta."""
    questionId: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    timestamp: Optional[datetime] = None
    isCorrect: Optional[bool] = None


class AnalyticBase(BaseModel):
    gameId: Optional[str] = None
    sessionId: Optional[str] = None
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    progress: Optional[int] = Field(default=None, ge=1, le=3)
    completed: Optional[bool] = None
    duration: Optional[int] = None
    responses: Optional[List[UserResponse]] = None
    score: Optional[int] = Field(default=None, ge=0)


class AnalyticCreate(AnalyticBase):
    """Schema para creación de un registro de analítica."""


class AnalyticDB(AnalyticBase):
    """Schema que representa el documento guardado en DB (respuesta)."""
    id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None

class AnalyticList(BaseModel):
    results: List[AnalyticDB]
    count: int

