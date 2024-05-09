from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class Game(BaseModel):
    title: str = Field(..., example="Game Title")
    synopsis: str = Field(..., example="This is a game synopsis")
    history: dict = Field(..., example="This is a game history")
    summary: str = Field(..., example="This is a game summary")
    image: str = Field(..., example="image.jpg")
    image_background: str = Field(..., example="background.jpg")
    prompt_image: str = Field(..., example="prompt.jpg")
    story_line: str = Field(..., example="This is a game story line")
    attempts: int = Field(..., example=1)
    characters_id: Optional[list[str]] = Field(..., example=["123", "456"])
    locations_id: Optional[list[str]] = Field(..., example=["123", "456"])
    category_id: str = Field(..., example="Category")
    response_error: str = Field(..., example="Error")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
