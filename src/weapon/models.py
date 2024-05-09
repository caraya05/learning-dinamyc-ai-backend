from pydantic import BaseModel
from pydantic import Field
from datetime import datetime
from typing import Optional, Dict


class Weapon(BaseModel):
    name: Optional[str] = Field(None, example="Weapon Name")
    description: Optional[str] = Field(None, example="This is a weapon description")
    type: str = Field(..., example="Type")
    image: Optional[str] = Field(None, example="image.jpg")
    script_id: str = Field(..., example="123")
    game_id: str = Field(..., example="123")
    extra_data: Optional[Dict[str, str]] = Field(None, example={"key": "value"})
    character_id: Optional[str] = Field(None, example="123")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
