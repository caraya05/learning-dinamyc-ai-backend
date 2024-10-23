from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel
from pydantic import Field

from character.enums import TypeCharacter
from character.enums import GenderCharacter
from core.database import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class SchemaAdminCreateCharacter(BaseModel):
    name: str = Field(..., max_length=100, example="Jhon Doe")
    prompt_user: str = Field(..., example="prompt_user")
    prompt_user_dialog: str = Field(None, example="prompt_user_dialog")
    type: str = Field(..., example="role")
    conversation_type: str = Field(..., example="conversation_type")


class SchemaAdminRetrieveCharacter(ResponseModel):
    name: str = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    type: Optional[str] = Field(None, example=TypeCharacter.LEADING_ROLE)
    image: Optional[str] = Field(..., example="image", default_factory=None)
    description: Optional[str] = Field(..., min_length=8, example="this is a description")
    genre: Optional[str] = Field(None, example=GenderCharacter, default_factory=None)
    extra_data: Optional[dict] = Field(None, example={"key": "value"})
    game_id: Optional[str] = Field(..., example="game_id")
    is_active: Optional[bool] = Field(default=True, example=True)
    body_type: Optional[str] = Field(None, example="body_type")
    prompt_user: Optional[str] = Field(None, example="prompt_user")
    prompt_user_dialog: Optional[str] = Field(None, example="prompt_user_dialog")
    conversation_type: Optional[str] = Field(None, example="conversation_type")
    conversation: Optional[list[dict]] = Field([], example=[{"key": "value"}])
    characteristics: Optional[dict] = Field(None, example={"key": "value"})
    status: Optional[str] = Field(1, example="status")
    character_type: Optional[str] = Field(None, example="character_type")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")

    class Config:
        orm_mode = True


class SchemaAdminRetrieveListCharacter(ResponseModelStr):
    name: str = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    type: str = Field(None, example=TypeCharacter.LEADING_ROLE)
    image: Optional[str] = Field(..., example="image", default_factory=None)
    genre: str = Field(None, example=GenderCharacter.MAN)
    game_id: str = Field(..., example="game_id")
    character_type: str = Field(None, example="character_type")
    conversation_type: str = Field(None, example="conversation_type")


class SchemaAdminListCharacter(BaseModel):
    characters: list[SchemaAdminRetrieveListCharacter]
    total: int
    page: int
    count: int

    class Config:
        orm_mode = True


class SchemaAdminUpdateCharacter(BaseModel):
    name: Optional[str] = Field(None, max_length=100, example="Jhon Doe")
    prompt_user: Optional[str] = Field(None, example="prompt_user")
    type: Optional[str] = Field(None, example="role")
    image: Optional[str] = Field(None, example="image")
    audio: Optional[str] = Field(None, example="sound")
    presentation: Optional[str] = Field(None, example="presentation")
    description: Optional[str] = Field(None, example="this is a description")
    genre: Optional[str] = Field(None, example=GenderCharacter.MAN)
    extra_data: Optional[dict] = Field(None, example={"key": "value"})
    game_id: Optional[str] = Field(None, example="game_id")
    is_active: Optional[bool] = Field(None, example=True)
    body_type: Optional[str] = Field(None, example="body_type")
    characteristics: Optional[dict] = Field(None, example={"key": "value"})
    status: Optional[str] = Field(None, example="status")
    character_type: Optional[str] = Field(None, example="character_type")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
