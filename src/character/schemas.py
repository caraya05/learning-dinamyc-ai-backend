from typing import Optional

from fastapi import Query
from pydantic import BaseModel
from pydantic import Field

from character.models import TypeCharacterEnum

from weapon.schemas import SchemaRetrieveWeapon


class SchemaCreateCharacter(BaseModel):
    name: str = Field(..., max_length=100,
                      example="Jhon Doe")
    genre: str = Field(...,  max_length=100,
                       example="male")
    type: str = Field(...,max_length=100,
                      example="leading role")
    description: str = Field(..., example="this is a description")

    game_id: str = Field(..., max_length=100, example="game_id")

    attempts: int = Field(..., example=0)

    extra_data: Optional[dict] = Field(None, example={"key": "value"})

    text_idle: Optional[dict] = Field(None, example={"key": "value"})


class SchemaRetrieveCharacter(BaseModel):
    id: str
    name: str = Field(..., min_length=3, max_length=100,
                      example="Jhon Doe")
    type: TypeCharacterEnum = Query(..., example="leading role")
    image: Optional[str] = Field(..., example="image", default_factory=None)
    description: str = Field(..., min_length=8, example="this is a description")
    genre: str = Field(...)
    extra_data: Optional[dict] = Field(None, example={"key": "value"})
    text_idle: Optional[dict] = Field(None, example={"key": "value"})
    # weapon: Optional[SchemaRetrieveWeapon] = Field(None, example="weapon")

    class Config:
        orm_mode = True


class SchemaPartialUpdateCharacter(BaseModel):
    image: Optional[str] = Field(None, example="image")


class SchemaListCharacter(BaseModel):
    results: list[SchemaRetrieveCharacter]
    count: int

    class Config:
        orm_mode = True


class SchemaUpdatePhotoCharacter(BaseModel):
    image: str = Field(..., example="image")
