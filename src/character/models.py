from datetime import datetime
from typing import Optional

from pydantic import Field
from pydantic import BaseModel

from character.enums import TypeCharacter
from character.enums import GenderCharacter


class Character(BaseModel):
    description: str = Field(..., example="This is a character")
    name: str = Field(..., example="Character Name")
    is_active: bool = Field(default=True, example=True)
    order: int = Field(default=0, example=0)
    image: Optional[str] = Field(None, example="image.jpg")
    gender: str = Field(..., example=GenderCharacter.MAN)
    game_id: Optional[str] = Field(..., example="game_id")
    attempts: Optional[int] = Field(3, example=1)
    extra_data: Optional[dict] = Field(None, example="Extra data")
    text_idle: Optional[dict] = Field(None, example="Text idle")
    type: Optional[str] = Field(..., example=TypeCharacter.LEADING_ROLE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
