from pydantic import BaseModel
from pydantic import Field
from datetime import datetime
from typing import Optional

from sound.enums import SoundType


class Sound(BaseModel):
    name: str = Field(..., example="Sound Name")
    description: str = Field(..., example="This is a sound description")
    file: str = Field(None, example="file.mp3")
    category: str = Field(..., example="Category")
    type: SoundType = Field(..., example=SoundType.situational)
    is_active: bool = Field(default=True, example=True)
    is_deleted: bool = Field(default=False, example=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
