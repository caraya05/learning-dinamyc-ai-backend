from typing import Optional

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from core.schemas import ResponseModel


class SchemaUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    email: EmailStr = Field(..., strip_whitespace=True, unique=True, example="jhon@gmail.com")
    password: Optional[str] = Field(None, min_length=8, example="password123")


class SchemaRetrieveUser(ResponseModel):
    username: str = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    email: str = Field(..., strip_whitespace=True, unique=True, example="jhon@gmail.com")
    stars: Optional[int] = Field(..., example=0)
    photo: Optional[str] = Field(..., example="photo.jpg")
    plan_type: Optional[str] = Field(default="individual", example="individual")
    team_id: Optional[str] = Field(default=None, example="507f1f77bcf86cd799439011")
    team_role: Optional[str] = Field(default=None, example="owner")
    is_team_owner: Optional[bool] = Field(default=False, example=False)

