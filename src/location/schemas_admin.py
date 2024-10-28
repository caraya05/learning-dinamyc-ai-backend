
from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class SchemaUpdateLocation(BaseModel):
    title: str = Field(None, example="Location Title")
    description: str = Field(None, example="This is a location description")
    prompt_user: str = Field(None, example="This is a prompt user")
    image: str = Field(None, example="image.jpg")
    audio: str = Field(None, example="audio.mp3")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
