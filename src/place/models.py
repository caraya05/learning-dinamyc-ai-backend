from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class Place(BaseModel):
    title: str = Field(None, example="Location Title")
    prompt_user: str = Field(None, example="This is a prompt user")
    image: str = Field(None, example="image.jpg")
    sound_id: str = Field(None, example="123")
    locations_id: list[str] = Field([], example="123")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
