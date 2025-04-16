from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class Event(BaseModel):
    name: str = Field(None, example="Event Name")
    prompt_user_image: str = Field(None, example="prompt_user_image.jpg")
    prompt_user_text: str = Field(None, example="prompt_user_test")
    type_conversation: Optional[str] = Field(None, example="conversation_type")
    character_id: Optional[str] = Field(None, example="character_id")
    option_number: Optional[int] = Field(None, example=1)
    character_principal: str = Field(None, example="character_principal")
    state_game_init: str = Field(None, example="state_game")
    state_game_end: Optional[str] = Field(None, example="state_game")
    location_state_game_init: str = Field(None, example="location_state_game")
    location_state_game_end: Optional[str] = Field(None, example="location_state_game")
    image: Optional[str] = Field(None, example="prompt_user_image.jpg")
    text_image: Optional[str] = Field(None, example="prompt_user_image.jpg")
    game_id: str = Field(None, example="game_id")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
    is_final: Optional[bool] = Field(default=False, example=False)
