from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


class SchemaCreateGame(BaseModel):
    title: str = Field(..., min_length=3, max_length=100,
                       example="Call of suty")
    # image: str = Field(..., example="image")
    characters: list[dict] = Field(..., example=[{
        "type": "character",
        "description": "character"
    }])
    location: str = Field(..., example="location")
    story_line: Optional[str] = Field(..., example="story_line")
    is_multiverse: Optional[bool] = Field(..., example=False)
    multiverse: Optional[list[str]] = Field(..., example=None)
    is_future_travel: Optional[bool] = Field(..., example=False)
    is_past_travel: Optional[bool] = Field(..., example=False)


class SchemaRetrieveGame(BaseModel):
    id: UUID
    title: str = Field(..., min_length=3, max_length=100,
                       example="Call of suty")
    summary: str = Field(..., example="sumary")
    location: str = Field(..., example="location")
    description: str = Field(..., min_length=8, example="this is a description")
    story_line: Optional[str] = Field(..., example="story_line")
    is_multiverse: Optional[bool] = Field(..., example="is_multiverse")
    multiverse: Optional[list[str]] = Field(..., example="multiverse")
    is_future_travel: Optional[bool] = Field(..., example="is_future_travel")
    is_past_travel: Optional[bool] = Field(..., example="is_past_travel")

    class Config:
        orm_mode = True


class SchemaListGame(BaseModel):
    count: int
    results: list[SchemaRetrieveGame]

    class Config:
        orm_mode = True


class SchemaPartialUpdateGame(BaseModel):
    # title: Optional[str] = Field(..., min_length=3, max_length=100,
    #                              example="Call of suty")
    # description: Optional[str] = Field(..., min_length=8, example="this is a description")
    image: Optional[str] = Field(..., example="photo")
    # story_line: Optional[str] = Field(..., example="story_line")
