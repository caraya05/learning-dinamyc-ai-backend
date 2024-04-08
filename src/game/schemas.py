from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


class SchemaCreateGame(BaseModel):
    story_line: Optional[str] = Field(..., example="story_line")


class SchemaRetrieveGame(BaseModel):
    id: UUID
    title: str = Field(..., min_length=3, max_length=100,
                       example="Call of suty")
    history: str = Field(..., example="history of the game")
    category: str | None = Field(None, example="category of the game")
    synopsis: str = Field(..., example="synopsis og the game")
    image: Optional[str] = Field(..., example="photo", decimal_places=None)
    image_background: Optional[str] = Field(..., example="photo background", decimal_places=None)
    story_line: Optional[str] = Field(..., example="story_line")
    attempts: Optional[int] = Field(..., example=3)
    summary: Optional[str] = Field(..., example="summary of the game")
    created_at: date
    created_by: str

    class Config:
        orm_mode = True


class SchemaListGame(BaseModel):
    count: int
    results: list[SchemaRetrieveGame]
    page: int
    total_pages: int

    class Config:
        orm_mode = True


class SchemaPartialUpdateGame(BaseModel):
    # synopsis: Optional[str] = Field(..., min_length=10, example="this is a description")
    image: Optional[str] = Field(..., example="photo")
