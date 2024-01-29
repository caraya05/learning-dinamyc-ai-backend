from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


class SchemaCreateCharacter(BaseModel):
    name: str = Field(..., min_length=3, max_length=100,
                      example="Jhon Doe")
    type: str = Field(..., min_length=3, max_length=100,
                      example="leading role")
    description: str = Field(..., min_length=8, example="this is a description")
    image: Optional[str] = Field(None, example="image")


class SchemaRetrieveCharacter(BaseModel):
    id: UUID
    name: str = Field(..., min_length=3, max_length=100,
                      example="Jhon Doe")
    type: str = Field(..., min_length=3, max_length=100,
                      example="leading role")
    description: str = Field(..., min_length=8, example="this is a description")


    class Config:
        orm_mode = True


class SchemaPartialUpdateCharacter(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100,
                                example="Jhon Doe")
    type: Optional[str] = Field(None, min_length=3, max_length=100,
                                example="leading role")
    description: Optional[str] = Field(None, min_length=8, example="this is a description")
    image: Optional[str] = Field(None, example="image")


class SchemaListCharacter(BaseModel):
    results: list[SchemaRetrieveCharacter]
    count: int

    class Config:
        orm_mode = True
