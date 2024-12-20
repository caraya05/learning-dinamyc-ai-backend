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
    state_game_init: str = Field(..., example="state_game")
    location_state_game_init: str = Field(..., example="location_state_game")
    game_id: str = Field(..., example="game_id")


class SchemaUpdateEvent(BaseModel):
    name: str = Field(..., example="Event Name")
    prompt_user_image: str = Field(..., example="prompt_user_image.jpg")
    prompt_user_text: str = Field(..., example="prompt_user_test")
    character_id: str = Field(..., example="character_id")
    type_conversation: str = Field(..., example="conversation_type")
    option_number: int = Field(..., example=1)
    state_game_init: str = Field(..., example="state_game")
    state_game_end: str = Field(..., example="state_game")
    location_state_game_init: str = Field(..., example="location_state_game")
    location_state_game_end: str = Field(..., example="location_state_game")


class SchemaRetrieveEvent(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str = Field(..., example="Event Name")
    prompt_user_image: str = Field(..., example="prompt_user_image.jpg")
    prompt_user_text: str = Field(..., example="prompt_user_test")
    type_conversation: str = Field(None, example="conversation_type")
    option_number: int = Field(None, example=1)
    state_game_init: str = Field(None, example="state_game")
    state_game_end: Optional[str] = Field(None, example="state_game")
    location_state_game_init: str = Field(None, example="location_state_game")
    location_state_game_end: Optional[str] = Field(None, example="location_state_game")
    image: Optional[str] = Field(..., example="prompt_user_image.jpg")
    text_image: Optional[str] = Field(..., example="prompt_user_image.jpg")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
    game_id: str = Field(..., example="game_id")
    character_id: str = Field(None, example="character_id")
    task_id: str = Field(None, example="task_id")

    class Config:
        json_encoders = {ObjectId: str}
        orm_mode = True


class SchemaListEvent(BaseModel):
    results: list[SchemaRetrieveEvent]
    count: int

    class Config:
        orm_mode = True
