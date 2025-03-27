from datetime import datetime
from typing import Optional

from pydantic import Field
from pydantic import BaseModel

from character.enums import TypeCharacter
from character.enums import GenderCharacter
from character.enums import TypeConversation
from character.schemas import SchemaOpenAnswer, SchemaOptionMultiple


class Character(BaseModel):
    game_id: Optional[str] = Field(None, example="game_id")
    status: Optional[int] = Field(0, example=200)
    tasks_request: Optional[list[str]] = Field([], example=["task1", "task2"])
    tasks_notified: Optional[list[str]] = Field([], example=["task1", "task2"])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")


class CharacterGLIC(BaseModel):
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
    locations_id: Optional[str] = Field(None, example="location_id")
    extra_data: Optional[dict] = Field(None, example="Extra data")
    conversation_type: str = Field(..., example=TypeConversation.NONE_CONVERSATION)
    conversation: Optional[list[dict]] = Field([], example=[{"key": "value"}])
    type: Optional[str] = Field(None, example=TypeCharacter.NPC)
    characteristics: Optional[dict] = Field(None, example={"key": "value"})
    options_dialog: Optional[SchemaOpenAnswer | SchemaOptionMultiple] = Field(
        None, example={"key": "value"}
    )
    personalization: Optional[dict] = Field(None, example={"key": "value"})
