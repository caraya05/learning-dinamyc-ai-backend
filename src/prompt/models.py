from pydantic import BaseModel
from pydantic import Field
from datetime import datetime

from prompt.enums import PromptType


class Prompt(BaseModel):
    title: str = Field(..., example="Prompt Title")
    description: str = Field(..., example="This is a prompt description")
    prompt_system: str = Field(..., example="Prompt System")
    category: str = Field(..., example=PromptType.CHARACTER)
    is_active: bool = Field(..., example=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
