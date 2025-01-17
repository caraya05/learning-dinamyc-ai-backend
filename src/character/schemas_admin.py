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
    description: Optional[str] = Field(None, example="This is a character")
    description_shoulder_up: Optional[str] = Field(None, example="This is a character")
    character_type: Optional[str] = Field(None, example="role")
    image: Optional[str] = Field(None, example="image")
    genre: Optional[str] = Field(None, example=GenderCharacter.MAN)
    body_type: Optional[str] = Field(None, example="body_type")
    interaction: Optional[list[dict]] = Field([], example=[{"key": "value"}])
    state: Optional[str] = Field(None, example="state")


class SchemaAdminDataCharacter(BaseModel):
    name: str = Field(..., example="Character Name")
    description: Optional[str] = Field(None, example="This is a character")
    description_shoulder_up: Optional[str] = Field(None, example="This is a character")
    is_active: bool = Field(default=True, example=True)
    prompt_user: str = Field(None, example="prompt_user")
    body_type: Optional[str] = Field(None, example="body_type")
    genre: Optional[str] = Field(None, example=GenderCharacter.MAN)
    character_type: Optional[str] = Field(None, example="character_type")
    image: Optional[str] = Field(None, example="image.jpg")
    locations_id: Optional[list] = Field(None, example="location_id")
    extra_data: Optional[dict] = Field(None, example="Extra data")
    interaction: Optional[list[dict]] = Field([], example=[{"key": "value"}])
    type: Optional[str] = Field(None, example=TypeCharacter.NPC)
    characteristics: Optional[dict] = Field(None, example={"key": "value"})

class SchemaAdminStateCharacter(BaseModel):
    order: Optional[int] = Field(None, example=1)
    state: Optional[str] = Field(None, example="state")
    data: Optional[list[SchemaAdminDataCharacter]] = Field(None, example={})

class SchemaAdminStateCharacters(BaseModel):
    id: str = Field(alias="_id")
    data: Optional[SchemaAdminStateCharacter] = Field(None, example={})
