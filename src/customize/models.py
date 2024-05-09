from pydantic import BaseModel
from pydantic import Field
from typing import Optional

from datetime import datetime
from customize.enums import CharacterType
from customize.enums import GenderType
from customize.enums import CustomizeType


class Customize(BaseModel):
    type_character: str = Field(..., example=CharacterType.HUMAN)
    reference_ui: Optional[str] = Field(None, example="UI reference")
    gender: str = Field(..., example=GenderType.MAN)
    description: str = Field(..., example="This is a description")
    type_customize: str = Field(..., example=CustomizeType.CLOTHES)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="", example="system")
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="", example="system")
