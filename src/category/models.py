from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class Category(BaseModel):
    name: str = Field(..., example="Category Name")
    description: str = Field(..., example="This is a category")
    order: int = Field(None, example=1)
    is_active: bool = Field(default=True, example=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="", example="system")
