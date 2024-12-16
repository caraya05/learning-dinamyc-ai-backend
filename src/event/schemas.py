from datetime import datetime
from typing import Optional, Dict

from bson import ObjectId
from pydantic import BaseModel
from pydantic import Field

from core import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")


class SchemaCreateEvent(BaseModel):
    name: str = Field(..., example="Event Name")
    prompt_user_image: str = Field(..., example="prompt_user_image.jpg")
    prompt_user_text: str = Field(..., example="prompt_user_test")
    conversation_type: str = Field(..., example="conversation_type")
    option_number: int = Field(..., example=1)
    state_game_init: str = Field(..., example="state_game")
    location_state_game_init: str = Field(..., example="location_state_game")
    game_id: str = Field(..., example="game_id")


class SchemaUpdateEvent(BaseModel):
    name: str = Field(..., example="Event Name")
    prompt_user_image: str = Field(..., example="prompt_user_image.jpg")
    prompt_user_text: str = Field(..., example="prompt_user_test")
    conversation_type: str = Field(..., example="conversation_type")
    option_number: int = Field(..., example=1)
    state_game_init: str = Field(..., example="state_game")
    state_game_end: str = Field(..., example="state_game")
    location_state_game_init: str = Field(..., example="location_state_game")
    location_state_game_end: str = Field(..., example="location_state_game")


class SchemaRetrieveEvent(BaseModel):
    name: str = Field(..., example="Event Name")
    prompt_user_image: str = Field(..., example="prompt_user_image.jpg")
    prompt_user_text: str = Field(..., example="prompt_user_test")
    conversation_type: str = Field(..., example="conversation_type")
    option_number: int = Field(..., example=1)
    state_game_init: str = Field(..., example="state_game")
    state_game_end: Optional[str] = Field(..., example="state_game")
    location_state_game_init: str = Field(..., example="location_state_game")
    location_state_game_end: Optional[str] = Field(..., example="location_state_game")
    image: Optional[str] = Field(..., example="prompt_user_image.jpg")
    text_image: Optional[str] = Field(..., example="prompt_user_image.jpg")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
    game_id: str = Field(..., example="game_id")
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}
        orm_mode = True


class SchemaListEvent(BaseModel):
    results: list[SchemaRetrieveEvent]
    count: int

    class Config:
        orm_mode = True