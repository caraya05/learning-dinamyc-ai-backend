from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List


class UserResponse(BaseModel):
    """Modelo para una respuesta del usuario a una pregunta."""
    questionId: Optional[str] = None
    question: str
    answer: str
    timestamp: Optional[datetime] = None
    isCorrect: Optional[bool] = None


class AnalyticBase(BaseModel):
    gameId: str
    sessionId: str
    startTime: datetime
    endTime: datetime
    progress: int = Field(..., ge=1, le=3)
    completed: bool
    duration: int
    responses: Optional[List[UserResponse]] = []
    score: Optional[int] = Field(default=0, ge=0)


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

