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
    history: Optional[str] = Field(None, example="history of the game")
    category_id: Optional[str] = Field(None, example="category of the game")
    synopsis: Optional[str] = Field(None, example="synopsis og the game")
    image: Optional[str] = Field(None, example="photo", decimal_places=None)
    image_background: Optional[str] = Field(None, example="photo background", decimal_places=None)
    summary: Optional[str] = Field(None, example="summary of the game")
    character_principal: Optional[str] = Field(None, example="Character principal")
    created_at: datetime
    created_by: str
    likes: list[str] = Field([], example=["123", "456"])
    plays: int = Field(0, example=0)
    status: Optional[int] = Field(1, example="status")
    reject_note: Optional[str] = Field(None, example="reject_note")
    published_at: Optional[datetime] = Field(None, example=datetime.utcnow())
    is_published: Optional[bool] = Field(False, example=True)
    code_access: Optional[str] = Field(None, example="123456")


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class SchemaRetrieveGameStr(ResponseModelStr):
    title: Optional[str] = Field(..., min_length=3, max_length=100, example="Call of suty")
    history: Optional[str] = Field(..., example="history of the game")
    category_id: Optional[str] | None = Field(None, example="category of the game")
    synopsis: Optional[str] = Field(..., example="synopsis og the game")
    image: Optional[str] = Field(..., example="photo", decimal_places=None)
    image_minimalist: Optional[str] = Field(None, example="photo", decimal_places=None)
    image_background: Optional[str] = Field(..., example="photo background", decimal_places=None)
    summary: Optional[str] = Field(..., example="summary of the game")
    created_at: datetime
    created_by: str
    likes: list[str] = Field([], example=["123", "456"])
    plays: int = Field(0, example=0)
    last_date_played: Optional[datetime] = Field(None, example=datetime.utcnow())
    status: Optional[int] = Field(1, example="status")
    reject_note: Optional[str] = Field(None, example="reject_note")
    published_at: Optional[datetime] = Field(None, example=datetime.utcnow())
    is_published: Optional[bool] = Field(False, example=True)


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


class SchemaUpdateGameV2(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100, example="Call of suty")
    prompt_image: Optional[str] = Field(None, example="prompt_user")
    description: Optional[str] = Field(None, example="description")
