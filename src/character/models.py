from datetime import datetime
from typing import Optional

from pydantic import Field
from pydantic import BaseModel

from character.enums import TypeCharacter
from character.enums import GenderCharacter
from character.enums import TypeConversation


class Character(BaseModel):
    name: str = Field(..., example="Character Name")
    description: Optional[str] = Field(None, example="This is a character")
    description_shoulder_up: Optional[str] = Field(None, example="This is a character")
    is_active: bool = Field(default=True, example=True)
    prompt_user: str = Field(None, example="prompt_user")
    prompt_user_dialog: str = Field(None, example="prompt_user_dialog")
    body_type: Optional[str] = Field(None, example="body_type")
    genre: Optional[str] = Field(None, example=GenderCharacter.MAN)
    character_type: Optional[str] = Field(None, example="character_type")
    image: Optional[str] = Field(None, example="image.jpg")
    game_id: Optional[str] = Field(None, example="game_id")
    extra_data: Optional[dict] = Field(None, example="Extra data")
    text_idle: Optional[dict] = Field(None, example="Text idle")
    conversation_type: str = Field(..., example=TypeConversation.NONE_CONVERSATION)
    conversation: Optional[list[dict]] = Field([], example=[{"key": "value"}])
    type: str = Field(..., example=TypeCharacter.LEADING_ROLE)
    characteristics: Optional[dict] = Field(None, example={"key": "value"})
    status: Optional[int] = Field(0, example=200)
    tasks_request: Optional[list[str]] = Field([], example=["task1", "task2"])
    tasks_notified: Optional[list[str]] = Field([], example=["task1", "task2"])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
