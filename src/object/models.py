from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class Object(BaseModel):
    name: str = Field(None, example="Object Name")
    prompt_user: str = Field(None, example="Prompt User")
    description: str = Field(None, example="This is an object description")
    function: str = Field(None, example="Function")
    image: str = Field(None, example="image.jpg")
    game_id: str = Field(None, example="123")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
