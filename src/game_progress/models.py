from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class GameProgress(BaseModel):
    user_id: str = Field(..., example="123")
    scene_id: str = Field(..., example="123")
    game_id: str = Field(..., example="123")
    object: str = Field(..., example="Object")
    life: int = Field(..., example=1)
    location_id: str = Field(..., example="123")
    is_complete: bool = Field(..., example=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
