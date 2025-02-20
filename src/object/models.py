from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from datetime import datetime

class Object(BaseModel):
    game_id: Optional[str] = Field(None, example="123")
    status: Optional[int] = Field(0, example=0)
    tasks_notified: Optional[list] = Field([], example=[1, 2, 3])
    tasks_request: Optional[int] = Field(0, example=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")

class ObjectGLIC(BaseModel):
    name: str = Field(None, example="Object Name")
    prompt_user: str = Field(None, example="Prompt User")
    prompt_user_dialog: Optional[str] = Field(None, example="Prompt User Dialog")
    type_item: Optional[str] = Field(None, example="type_item")
    image: Optional[str] = Field(None, example="image.jpg")
    location_id: Optional[str] = Field(None, example="123")
    game_id: Optional[str] = Field(None, example="123")
    is_active: bool = Field(default=True, example=True)
