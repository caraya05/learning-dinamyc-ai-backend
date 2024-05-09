from pydantic import BaseModel
from pydantic import Field
from datetime import datetime
from typing import Optional


class Chapter(BaseModel):
    title: str = Field(..., example="Script Title")
    description: str = Field(None, example="This is a script description")
    game_id: str = Field(..., example="123")
    order: Optional[int] = Field(None, example=1)
    status: Optional[int] = Field(None, example=1)
    status_character: Optional[int] = Field(None, example=1)
    status_location: Optional[int] = Field(None, example=1)
    status_scene: Optional[int] = Field(None, example=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
