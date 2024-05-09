from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class Location(BaseModel):
    title: str = Field(None, example="Location Title")
    description: str = Field(None, example="This is a location description")
    prompt_user: str = Field(None, example="This is a prompt user")
    image: str = Field(None, example="image.jpg")
    config: list[dict] = Field(None, example="")
    sound_id: str = Field(None, example="123")
    game_id: str = Field(None, example="123")
    attempts: int = Field(3, example=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
