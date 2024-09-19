from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from datetime import datetime


class Location(BaseModel):
    title: str = Field(None, example="Location Title")
    description: Optional[str] = Field(None, example="This is a location description")
    prompt_user: str = Field(None, example="This is a prompt user")
    image: Optional[str] = Field(None, example="image.jpg")
    config: Optional[list[dict]] = Field(None, example="")
    connections: Optional[dict] = Field(None, example="")
    sound_id: Optional[str] = Field(None, example="123")
    game_id: Optional[str] = Field(None, example="123")
    status: Optional[int] = Field(0, example=200)
    tasks_request: Optional[list[str]] = Field([], example=["task1", "task2"])
    tasks_notified: Optional[list[str]] = Field([], example=["task1", "task2"])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
