from datetime import datetime
from typing import Optional

from bson import ObjectId

from core.schemas import ResponseModel
from pydantic import BaseModel
from pydantic import Field


class SchemaCreateGame(BaseModel):
    story_line: Optional[str] = Field(..., example="story_line")


class SchemaRetrieveGame(ResponseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100, example="Call of suty")
    history: Optional[dict] = Field(None, example="history of the game")
    category_id: Optional[str] = Field(None, example="category of the game")
    synopsis: Optional[str] = Field(None, example="synopsis og the game")
    image: Optional[str] = Field(None, example="photo", decimal_places=None)
    image_background: Optional[str] = Field(None, example="photo background", decimal_places=None)
    story_line: Optional[str] = Field(None, example="story_line")
    attempts: Optional[int] = Field(None, example=3)
    summary: Optional[str] = Field(None, example="summary of the game")
    character_principal: Optional[str] = Field(None, example="Character principal")
    created_at: datetime
    created_by: str
    likes: list[str] = Field([], example=["123", "456"])


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class SchemaRetrieveGameStr(ResponseModelStr):
    title: str = Field(..., min_length=3, max_length=100, example="Call of suty")
    history: dict = Field(..., example="history of the game")
    category_id: str | None = Field(None, example="category of the game")
    synopsis: str = Field(..., example="synopsis og the game")
    image: Optional[str] = Field(..., example="photo", decimal_places=None)
    image_background: Optional[str] = Field(..., example="photo background", decimal_places=None)
    story_line: Optional[str] = Field(..., example="story_line")
    attempts: Optional[int] = Field(..., example=3)
    summary: Optional[str] = Field(..., example="summary of the game")
    created_at: datetime
    created_by: str
    likes: list[str] = Field([], example=["123", "456"])


class SchemaListGame(BaseModel):
    count: int
    results: list[SchemaRetrieveGameStr]
    page: int
    total_pages: int


class SchemaPartialUpdateGame(BaseModel):
    # synopsis: Optional[str] = Field(..., min_length=10, example="this is a description")
    image: Optional[str] = Field(..., example="photo")


class SchemaAddItem(BaseModel):
    item_id: str
    game_id: str


class SchemaAddLocation(BaseModel):
    location_id: str
    game_id: str


class SchemaAddCharacter(BaseModel):
    character_id: str
    game_id: str


class SchemaChangeCharacter(BaseModel):
    character_id: str
    game_id: str