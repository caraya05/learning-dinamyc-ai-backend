from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List


class AnalyticBase(BaseModel):
    gameId: str
    startTime: datetime
    endTime: datetime
    progress: int = Field(..., ge=1, le=3)
    completed: bool
    duration: int


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

