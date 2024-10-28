from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class SchemaUpdateGame(BaseModel):
    title: str = Field(..., max_length=100, example="Game Title")
    history: str = Field(..., example="Game History")
    summary: str = Field(..., example="Game Summary")
    category_id: str = Field(..., example="category_id")
    image: str = Field(..., example="image")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
