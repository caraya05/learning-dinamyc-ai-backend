import datetime
from typing import Optional
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field


class User(BaseModel):
    username: str = Field(default="", example="user")
    email: EmailStr | str = Field(default="", example="user@example.com")
    photo: Optional[str] = Field(default=None, example="photo.jpg")
    uid: Optional[str] = Field(default=None, example="123")
    provider: str = Field(default="local", example="local")
    password: str = Field(default="", min_length=8, example="password123")
    is_active: bool = Field(default=False, example=False)
    is_superuser: bool = Field(default=False, example=False)
    is_staff: bool = Field(default=False, example=False)
    stars: int = Field(default=0, example=0)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
    is_preview: bool = Field(default=False, example=False)
    plan_type: str = Field(default="individual", example="individual")  # individual or team
    team_id: Optional[str] = Field(default=None, example="507f1f77bcf86cd799439011")
    team_role: Optional[str] = Field(default=None, example="owner")  # owner, creator, viewer, admin
    is_team_owner: bool = Field(default=False, example=False)
