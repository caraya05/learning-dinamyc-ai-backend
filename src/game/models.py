from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class Game(BaseModel):
    title: Optional[str] = Field(None, example="Game Title")
    synopsis: Optional[str] = Field(None, example="This is a game synopsis")
    history: Optional[dict] = Field(None, example="This is a game history")
    summary: Optional[str] = Field(None, example="This is a game summary")
    character_principal: Optional[str] = Field(None, example="Character principal")
    image: Optional[str] = Field(None, example="image.jpg")
    image_background: Optional[str] = Field(None, example="background.jpg")
    prompt_image: Optional[str] = Field(None, example="prompt.jpg")
    story_line: Optional[str] = Field(None, example="This is a game story line")
    attempts: Optional[int] = Field(None, example=1)
    characters_id: Optional[list[str]] = Field(None, example=["123", "456"])
    locations_id: Optional[list[str]] = Field(None, example=["123", "456"])
    items_id: Optional[list[str]] = Field(None, example=["123", "456"])
    category_id: Optional[str] = Field(None, example="Category")
    response_error: Optional[str] = Field(None, example="Error")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
    likes: Optional[list[str]] = Field([], example=["123", "456"])
    version: Optional[int] = Field(2, example=1)
