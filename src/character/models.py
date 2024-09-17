from datetime import datetime
from typing import Optional

from pydantic import Field
from pydantic import BaseModel

from character.enums import TypeCharacter
from character.enums import GenderCharacter


class Character(BaseModel):
    name: str = Field(..., example="Character Name")
    description: str = Field(..., example="This is a character")
    description_shoulder_up: Optional[str] = Field(None, example="This is a character")
    is_active: bool = Field(default=True, example=True)
    prompt_user: Optional[str] = Field(None, example="prompt_user")
    body_type: Optional[str] = Field(..., example="body_type")
    genre: Optional[str] = Field(None, example=GenderCharacter.MAN)
    character_type: Optional[str] = Field(..., example="character_type")
    image: Optional[str] = Field(None, example="image.jpg")
    game_id: Optional[str] = Field(None, example="game_id")
    extra_data: Optional[dict] = Field(None, example="Extra data")
    text_idle: Optional[dict] = Field(None, example="Text idle")
    type: Optional[str] = Field(..., example=TypeCharacter.LEADING_ROLE)
    characteristics: Optional[dict] = Field(None, example={"key": "value"})
    audio: Optional[str] = Field(None, example="audio")
    status: Optional[int] = Field(0, example=200)
    tasks_request: Optional[list[str]] = Field([], example=["task1", "task2"])
    tasks_notified: Optional[list[str]] = Field([], example=["task1", "task2"])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
