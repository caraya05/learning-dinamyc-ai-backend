from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Analytic(BaseModel):
    gameId: str
    startTime: datetime
    endTime: datetime
    progress: int
    completed: bool
    duration: int
    user_id: Optional[str]
    created_at: Optional[datetime]

    class Config:
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "gameId": "68fb8fa10a03fc50ec57a672",
                "startTime": "2025-11-10T14:12:00Z",
                "endTime": "2025-11-10T14:22:20Z",
                "progress": 2,
                "completed": True,
                "duration": 620,
            }
        }

