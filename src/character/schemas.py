from typing import Optional

from bson import ObjectId
from pydantic import BaseModel
from pydantic import Field

from character.enums import TypeCharacter
from character.enums import GenderCharacter
from core import PyObjectId

from weapon.schemas import SchemaRetrieveWeapon


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")


class SchemaCreateCharacter(BaseModel):
    name: str = Field(..., max_length=100, example="Jhon Doe")
    gender: str = Field("man", example=GenderCharacter.MAN)
    type: str = Field("leading role", max_length=100, example="leading role")
    description: str = Field(..., example="this is a description")

    game_id: str = Field(..., max_length=100, example="game_id")

    attempts: int = Field(..., example=0)

    extra_data: Optional[dict] = Field(None, example={"key": "value"})

    text_idle: Optional[dict] = Field(None, example={"key": "value"})


class SchemaRetrieveCharacter(ResponseModel):
    name: str = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    type: str = Field(..., example=TypeCharacter.LEADING_ROLE)
    image: Optional[str] = Field(..., example="image", default_factory=None)
    description: str = Field(..., min_length=8, example="this is a description")
    gender: str = Field(..., example=GenderCharacter.MAN)
    extra_data: Optional[dict] = Field(None, example={"key": "value"})
    text_idle: Optional[dict] = Field(None, example={"key": "value"})
    game_id: str = Field(..., example="game_id")
    # weapon: Optional[SchemaRetrieveWeapon] = Field(None, example="weapon")


class SchemaRetrieveCharacterStr(ResponseModelStr):
    name: str = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    type: str = Field(..., example=TypeCharacter.LEADING_ROLE)
    image: Optional[str] = Field(..., example="image", default_factory=None)
    description: str = Field(..., min_length=8, example="this is a description")
    gender: str = Field(..., example=GenderCharacter.MAN)
    extra_data: Optional[dict] = Field(None, example={"key": "value"})
    text_idle: Optional[dict] = Field(None, example={"key": "value"})

    # weapon: Optional[SchemaRetrieveWeapon] = Field(None, example="weapon")


class SchemaPartialUpdateCharacter(BaseModel):
    image: Optional[str] = Field(None, example="image")


class SchemaListCharacter(BaseModel):
    results: list[SchemaRetrieveCharacterStr]
    count: int

    class Config:
        orm_mode = True


class SchemaUpdatePhotoCharacter(BaseModel):
    image: str = Field(..., example="image")
