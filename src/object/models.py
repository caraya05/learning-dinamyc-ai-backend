from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class Object(BaseModel):
    name: str = Field(..., example="Object Name")
    description: str = Field(..., example="This is an object description")
    function: str = Field("", example="Function")
    image: str = Field(..., example="image.jpg")
    game_id: str = Field("", example="123")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
