from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class Game(BaseModel):
    title: Optional[str] = Field(None, example="Game Title")
    synopsis: Optional[str] = Field(None, example="This is a game synopsis")
    description: Optional[str] = Field(None, example="This is a game description")
    summary: Optional[str] = Field(None, example="This is a game summary")
    character_principal: Optional[str] = Field(None, example="Character principal")
    image: Optional[str] = Field(None, example="image.jpg")
    image_minimalist: Optional[str] = Field(None, example="image.jpg")
    image_background: Optional[str] = Field(None, example="background.jpg")
    event_init: Optional[str] = Field(None, example="event_init")
    event_end: Optional[str] = Field(None, example="event_end")
    prompt_image: Optional[str] = Field(None, example="prompt.jpg")
    characters_id: Optional[list[str]] = Field(None, example=["123", "456"])
    locations_id: Optional[list[str]] = Field(None, example=["123", "456"])
    items_id: Optional[list[str]] = Field(None, example=["123", "456"])
    category_id: Optional[str] = Field(None, example="Category")
    likes: Optional[list[str]] = Field([], example=["123", "456"])
    version: Optional[int] = Field(2, example=1)
    status: Optional[int] = Field(0, example=200)
    code_access: Optional[str] = Field(None, example="123456")
    tasks_request: Optional[list[str]] = Field([], example=["task1", "task2"])
    tasks_notified: Optional[list[str]] = Field([], example=["task1", "task2"])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
