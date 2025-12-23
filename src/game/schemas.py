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
    image_minimalist: Optional[str] = Field(None, example="photo", decimal_places=None)
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
    prompt_image: Optional[str] = Field(None, example="prompt_user")
    description: Optional[str] = Field(None, example="description")
    event_init: Optional[str] = Field(None, example="event_init")
    event_end: Optional[str] = Field(None, example="event_end")
    provisional_id: Optional[str] = Field(None, example="provisional_id")
    locations: Optional[list[dict]] = Field(None, example=["location1", "location2"])
    locations_states: Optional[list[dict]] = Field(None, example=["location_state1", "location_state2"])
    characters: Optional[list[dict]] = Field(None, example=["character1", "character2"])
    characters_states: Optional[list[dict]] = Field(None, example=["character_state1", "character_state2"])
    events: Optional[list[dict]] = Field(None, example=["event1", "event2"])
    state_games: Optional[list[dict]] = Field(None, example=["state_game1", "state_game2"])
    game_provisional: Optional[dict] = Field(None, example={"provisional_field": "value"})
    number_music_track: Optional[int] = Field(0, example=0)


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class SchemaRetrieveGameStr(ResponseModelStr):
    title: Optional[str] = Field(None, min_length=3, max_length=100, example="Call of suty")
    history: Optional[str] = Field(None, example="history of the game")
    category_id: Optional[str] | None = Field(None, example="category of the game")
    synopsis: Optional[str] = Field(None, example="synopsis og the game")
    image: Optional[str] = Field(None, example="photo", decimal_places=None)
    image_minimalist: Optional[str] = Field(None, example="photo", decimal_places=None)
    image_background: Optional[str] = Field(None, example="photo background", decimal_places=None)
    summary: Optional[str] = Field(None, example="summary of the game")
    created_at: datetime
    created_by: str
    likes: list[str] = Field([], example=["123", "456"])
    plays: int = Field(0, example=0)
    last_date_played: Optional[datetime] = Field(None, example=datetime.utcnow())
    status: Optional[int] = Field(1, example="status")
    reject_note: Optional[str] = Field(None, example="reject_note")
    published_at: Optional[datetime] = Field(None, example=datetime.utcnow())
    is_published: Optional[bool] = Field(False, example=True)
    prompt_image: Optional[str] = Field(None, example="prompt_user")
    description: Optional[str] = Field(None, example="description")
    is_active: Optional[bool] = Field(False, example=True)
    event_init: Optional[str] = Field(None, example="event_init")
    event_end: Optional[str] = Field(None, example="event_end")
    provisional_id: Optional[str] = Field(None, example="provisional_id")
    game_provisional: Optional[dict] = Field(None, example={"provisional_field": "value"})


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
    event_init: Optional[str] = Field(None, example="event_init")
    event_end: Optional[str] = Field(None, example="event_end")
