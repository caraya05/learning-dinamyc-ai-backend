from typing import Optional

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from core.schemas import ResponseModel


class SchemaUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    email: EmailStr = Field(..., strip_whitespace=True, unique=True, example="jhon@gmail.com")
    password: str = Field(None, min_length=8, example="password123")


class SchemaRetrieveUser(ResponseModel):
    username: str = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    email: str = Field(..., strip_whitespace=True, unique=True, example="jhon@gmail.com")
    stars: Optional[int] = Field(..., example=0)
    photo: Optional[str] = Field(..., example="photo.jpg")
