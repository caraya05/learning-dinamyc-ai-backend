import datetime

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field


class User(BaseModel):
    username: str = Field(..., example="user")
    email: EmailStr = Field(..., example="user@example.com")
    photo: str = Field(None, example="photo.jpg")
    uid: str = Field(None, example="123")
    provider: str = Field(default="local", example="local")
    password: str = Field(..., min_length=8, example="password123")
    is_active: bool = Field(default=False, example=False)
    is_superuser: bool = Field(default=False, example=False)
    is_staff: bool = Field(default=False, example=False)
    stars: int = Field(default=0, example=0)
    number_of_creation_attempts: int = Field(default=0, example=0)
    attempt_to_create: bool = Field(default=False, example=False)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
    is_preview: bool = Field(default=False, example=False)
