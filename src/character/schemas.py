from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


class SchemaCreateCharacter(BaseModel):
    name: str = Field(..., min_length=3, max_length=100,
                      example="Jhon Doe")
    genre: str = Field(..., min_length=3, max_length=100,
                          example="male")
    type: str = Field(..., min_length=3, max_length=100,
                      example="leading role")
    description: str = Field(..., min_length=8, example="this is a description")


class SchemaRetrieveCharacter(BaseModel):
    id: UUID
    name: str = Field(..., min_length=3, max_length=100,
                      example="Jhon Doe")
    type: str = Field(..., min_length=3, max_length=100,
                      example="leading role")
    image: str = Field(..., example="image")
    description: str = Field(..., min_length=8, example="this is a description")

    class Config:
        orm_mode = True


class SchemaPartialUpdateCharacter(BaseModel):
    image: Optional[str] = Field(None, example="image")


class SchemaListCharacter(BaseModel):
    results: list[SchemaRetrieveCharacter]
    count: int

    class Config:
        orm_mode = True
