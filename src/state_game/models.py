from datetime import datetime

from pydantic import BaseModel


class StateGame(BaseModel):
    game_id: str
    order: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str