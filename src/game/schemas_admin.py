from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class SchemaUpdateGame(BaseModel):
    title: str = Field(..., max_length=100, example="Game Title")
    history: str = Field(..., example="Game History")
    summary: str = Field(..., example="Game Summary")
    image: str = Field(..., example="image")
    is_active: bool = Field(default=True, example=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
