from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class SchemaUpdateGame(BaseModel):
    title: str = Field(None, max_length=100, example="Game Title")
    history: str = Field(None, example="Game History")
    summary: str = Field(None, example="Game Summary")
    category_id: str = Field(None, example="category_id")
    is_active: bool = Field(default=None, example=True)
    image: str = Field(None, example="image")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default=None, example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default=None, example="system")
