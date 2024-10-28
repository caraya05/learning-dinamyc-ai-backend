from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel
from pydantic import Field

from character.enums import TypeCharacter
from character.enums import GenderCharacter
from core.database import PyObjectId


class SchemaAdminCreateCharacter(BaseModel):
    name: str = Field(..., max_length=100, example="Jhon Doe")
    prompt_user: str = Field(..., example="prompt_user")
    prompt_user_dialog: str = Field(None, example="prompt_user_dialog")
    type: str = Field(..., example="role")
    conversation_type: str = Field(..., example="conversation_type")


class SchemaAdminUpdateCharacter(BaseModel):
    name: Optional[str] = Field(None, max_length=100, example="Jhon Doe")
    prompt_user: Optional[str] = Field(None, example="prompt_user")
    type: Optional[str] = Field(None, example="role")
    image: Optional[str] = Field(None, example="image")
    audio: Optional[str] = Field(None, example="sound")
    presentation: Optional[str] = Field(None, example="presentation")
    description: Optional[str] = Field(None, example="this is a description")
    genre: Optional[str] = Field(None, example=GenderCharacter.MAN)
    body_type: Optional[str] = Field(None, example="body_type")
    character_type: Optional[str] = Field(None, example="character_type")


