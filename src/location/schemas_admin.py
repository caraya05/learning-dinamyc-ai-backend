from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class SchemaUpdateLocation(BaseModel):
    title: str = Field(None, example="Location Title")
    description: str = Field(None, example="This is a location description")
    prompt_user: str = Field(None, example="This is a prompt user")
    image: str = Field(None, example="image.jpg")
    audio: str = Field(None, example="audio.mp3")
    state: Optional[str] = Field(None, example="state")


class SchemaAdminDataLocation(BaseModel):
    title: str = Field(..., example="Location Title")
    description: str = Field(None, example="This is a location description")
    prompt_user: str = Field(None, example="This is a prompt user")
    image: str = Field(None, example="image.jpg")
    audio: str = Field(None, example="audio.mp3")


class SchemaAdminStateLocation(BaseModel):
    order: int = Field(..., example=1)
    state: str = Field(..., example="state")
    data: SchemaAdminDataLocation = Field(..., example={})


class SchemaAdminStateLocations(BaseModel):
    id: str = Field(alias="_id")
    data: SchemaAdminStateLocation = Field(..., example={})
