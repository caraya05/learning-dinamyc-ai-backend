from datetime import datetime
from typing import Optional, Dict

from bson import ObjectId
from pydantic import BaseModel
from pydantic import Field

from character.enums import TypeCharacter
from character.enums import GenderCharacter
from core import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")


class SchemaCreateCharacter(BaseModel):
    name: str = Field(..., max_length=100, example="Jhon Doe")
    prompt_user: str = Field(..., example="prompt_user")
    prompt_user_dialog: str = Field(None, example="prompt_user_dialog")
    type: str = Field(..., example="role")
    conversation_type: str = Field(..., example="conversation_type")


class SchemaRetrieveCharacter(ResponseModel):
    name: str = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    type: Optional[str] = Field(None, example=TypeCharacter.LEADING_ROLE)
    image: Optional[str] = Field(..., example="image", default_factory=None)
    description: Optional[str] = Field(..., min_length=8, example="this is a description")
    genre: Optional[str] = Field(None, example=GenderCharacter.MAN)
    extra_data: Optional[dict] = Field(None, example={"key": "value"})
    text_idle: Optional[dict] = Field(None, example={"key": "value"})
    game_id: Optional[str] = Field(..., example="game_id")
    body_type: Optional[str] = Field(None, example="body_type")
    prompt_user: Optional[str] = Field(None, example="prompt_user")
    prompt_user_dialog: Optional[str] = Field(None, example="prompt_user_dialog")
    conversation_type: Optional[str] = Field(None, example="conversation_type")
    conversation: Optional[list[dict]] = Field([], example=[{"key": "value"}])
    characteristics: Optional[dict] = Field(None, example={"key": "value"})
    audio: Optional[str] = Field(None, example="audio")
    presentation: Optional[str] = Field(None, example="presentation")
    task_id: Optional[str] = Field(None, example="task_db")
    status: Optional[str] = Field(1, example="status")
    character_type: Optional[str] = Field(None, example="character_type")


class SchemaRetrieveCharacterStr(ResponseModelStr):
    name: str = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    type: str = Field(None, example=TypeCharacter.LEADING_ROLE)
    image: Optional[str] = Field(..., example="image", default_factory=None)
    description: Optional[str] = Field(..., min_length=8, example="this is a description")
    genre: str = Field(None, example=GenderCharacter.MAN)
    extra_data: Optional[dict] = Field(None, example={"key": "value"})
    text_idle: Optional[dict] = Field(None, example={"key": "value"})
    body_type: Optional[str] = Field(None, example="body_type")
    prompt_user: Optional[str] = Field(None, example="prompt_user")
    prompt_user_dialog: Optional[str] = Field(None, example="prompt_user_dialog")
    conversation_type: Optional[str] = Field(None, example="conversation_type")
    conversation: Optional[list[dict]] = Field([], example=[{"key": "value"}])
    audio: Optional[str] = Field(None, example="audio")
    status: Optional[str] = Field(1, example="status")
    presentation: Optional[str] = Field(None, example="presentation")
    characteristics: Optional[dict] = Field(None, example={"key": "value"})
    character_type: Optional[str] = Field(None, example="character_type")

    # weapon: Optional[SchemaRetrieveWeapon] = Field(None, example="weapon")


class SchemaCreateCharacterCollection(BaseModel):
    prompt_user: str = Field(..., example="prompt_user")
    name: str = Field(..., example="name")


class SchemaUpdateCharacterCollection(BaseModel):
    name: Optional[str] = Field(None, max_length=100, example="Jhon Doe")
    prompt_user: Optional[str] = Field(None, example="prompt_user")


class SchemaPartialUpdateCharacter(BaseModel):
    image: Optional[str] = Field(None, example="image")


class SchemaListCharacter(BaseModel):
    results: list[SchemaRetrieveCharacterStr]
    count: int

    class Config:
        orm_mode = True


class SchemaUpdatePhotoCharacter(BaseModel):
    image: str = Field(..., example="image")


class SchemaAddCharacterLocation(BaseModel):
    location_id: str = Field(..., example="location_id")
    character_id: str = Field(..., example="character_id")


class CharacterLocationModel(BaseModel):
    character_id: str = Field(...)
    location_id: str = Field(...)
    characteristics: Dict[str, str] = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(...)
    updated_by: str = Field(...)

    class Config:
        json_encoders = {ObjectId: str}


class SchemaUpdatedCharacterLocation(BaseModel):
    character_id: str = Field(...)
    location_id: str = Field(...)
    characteristics: Dict[str, str] = Field(...)
