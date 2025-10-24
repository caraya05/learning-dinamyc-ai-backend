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
    name: Optional[str] = Field(None, example="Event Name")
    prompt_user_image: Optional[str] = Field(None, example="prompt_user_image.jpg")
    prompt_user_text: Optional[str] = Field(None, example="prompt_user_test")
    character_id: Optional[str] = Field(None, example="character_id")
    type_conversation: Optional[str] = Field(None, example="conversation_type")
    option_number: Optional[int] = Field(None, example=1)
    state_game_init: Optional[str] = Field(None, example="state_game")
    state_game_end: Optional[str] = Field(None, example="state_game")
    location_state_game_init: Optional[str] = Field(None, example="location_state_game")
    location_state_game_end: Optional[str] = Field(None, example="location_state_game")
    audio: Optional[str] = Field(None, example={"url": "audio_url", "duration": 10})
    audio_mp3: Optional[str] = Field(None, example={"url": "audio_url", "duration": 10})
    game_id: str = Field(..., example="game_id")
    is_final: Optional[bool] = Field(default=False, example=False)
    image: Optional[str] = Field(None, example="image_url")


class SchemaCreateEventAdmin(BaseModel):
    name: Optional[str] = Field(None, example="Event Name")
    prompt_user_image: Optional[str] = Field(None, example="prompt_user_image.jpg")
    prompt_user_text: Optional[str] = Field(None, example="prompt_user_test")
    character_id: Optional[str] = Field(None, example="character_id")
    type_conversation: Optional[str] = Field(None, example="conversation_type")
    option_number: Optional[int] = Field(None, example=1)
    state_game_init: Optional[str] = Field(None, example="state_game")
    state_game_end: Optional[str] = Field(None, example="state_game")
    location_state_game_init: Optional[str] = Field(None, example="location_state_game")
    location_state_game_end: Optional[str] = Field(None, example="location_state_game")
    audio: Optional[str] = Field(None, example={"url": "audio_url", "duration": 10})
    audio_mp3: Optional[str] = Field(None, example={"url": "audio_url", "duration": 10})
    game_id: str = Field(None, example="game_id")
    image: Optional[str] = Field(None, example="prompt_user_image.jpg")


class SchemaUpdateEvent(BaseModel):
    name: Optional[str] = Field(None, example="Event Name")
    prompt_user_image: Optional[str] = Field(None, example="prompt_user_image.jpg")
    prompt_user_text: Optional[str] = Field(None, example="prompt_user_test")
    character_id: Optional[str] = Field(None, example="character_id")
    type_conversation: Optional[str] = Field(None, example="conversation_type")
    option_number: Optional[int] = Field(None, example=1)
    state_game_init: Optional[str] = Field(None, example="state_game")
    state_game_end: Optional[str] = Field(None, example="state_game")
    location_state_game_init: Optional[str] = Field(None, example="location_state_game")
    location_state_game_end: Optional[str] = Field(None, example="location_state_game")
    is_final: Optional[bool] = Field(default=False, example=False)

class SchemaUpdateEventAdmin(BaseModel):
    name: Optional[str] = Field(None, example="Event Name")
    prompt_user_image: Optional[str] = Field(None, example="prompt_user_image.jpg")
    prompt_user_text: Optional[str] = Field(None, example="prompt_user_test")
    character_id: Optional[str] = Field(None, example="character_id")
    type_conversation: Optional[str] = Field(None, example="conversation_type")
    option_number: Optional[int] = Field(None, example=1)
    state_game_init: Optional[str] = Field(None, example="state_game")
    state_game_end: Optional[str] = Field(None, example="state_game")
    location_state_game_init: Optional[str] = Field(None, example="location_state_game")
    location_state_game_end: Optional[str] = Field(None, example="location_state_game")
    image: Optional[str] = Field(None, example="prompt_user_image.jpg")


class SchemaRetrieveEvent(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str = Field(None, example="Event Name")
    prompt_user_image: str = Field(None, example="prompt_user_image.jpg")
    prompt_user_text: str = Field(None, example="prompt_user_test")
    type_conversation: str = Field(None, example="conversation_type")
    option_number: int = Field(None, example=1)
    state_game_init: str = Field(None, example="state_game")
    state_game_end: Optional[str] = Field(None, example="state_game")
    location_state_game_init: str = Field(None, example="location_state_game")
    location_state_game_end: Optional[str] = Field(None, example="location_state_game")
    image: Optional[str] = Field(None, example="prompt_user_image.jpg")
    text_image: Optional[str] = Field(None, example="prompt_user_image.jpg")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
    game_id: str = Field(None, example="game_id")
    character_id: str = Field(None, example="character_id")
    task_id: str = Field(None, example="task_id")
    audio: Optional[str] = Field(None, example={"url": "audio_url", "duration": 10})
    audio_mp3: Optional[str] = Field(None, example={"url": "audio_url", "duration": 10})
    is_final: Optional[bool] = Field(default=False, example=False)

    class Config:
        json_encoders = {ObjectId: str}
        orm_mode = True


class SchemaListEvent(BaseModel):
    results: list[SchemaRetrieveEvent]
    count: int

    class Config:
        orm_mode = True
