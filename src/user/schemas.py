import uuid
from typing import Optional

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field


class SchemaBaseUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, strip_whitespace=True,
                          example="user")
    password: str = Field(..., min_length=8, example="Password123")


class SchemaUser(BaseModel):
    id: str = Field(default_factory=uuid.uuid4, example="uuid")
    username: str = Field(..., example="Jhon Doe")
    email: EmailStr = Field(..., strip_whitespace=True, unique=True, example="jhon@gmail.com")
    password: Optional[str] = Field(..., example="password123")
    photo: Optional[str] = Field(..., example="photo.jpg")
    uid: str = Field(..., example="123")
    provider: str = Field(..., example="local")
    is_active: bool = Field(default=False, example=False)
    is_superuser: bool = Field(default=False, example=False)
    is_staff: bool = Field(default=False, example=False)
    stars: Optional[int] = Field(default=0, example=0)
    number_of_creation_attempts: Optional[int] = Field(default=0, example=0)
    attempt_to_create: Optional[bool] = Field(default=False, example=False)


class SchemaRetrieveUser(BaseModel):
    id: str
    username: str = Field(..., min_length=3, max_length=100,
                          example="Jhon Doe")
    email: str = Field(..., strip_whitespace=True, unique=True, example="jhon@gmail.com")
    stars: Optional[int] = Field(..., example=0)
    photo: Optional[str] = Field(..., example="photo.jpg")

    # created_at: datetime.date = Field(default=datetime.datetime.utcnow())
    # updated_at: datetime.date = Field(default=datetime.datetime.utcnow())

    class Config:
        orm_mode = True


class SchemaListUser(BaseModel):
    count: int
    results: list[SchemaRetrieveUser]

    class Config:
        orm_mode = True


class SchemaUpdateUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=100,
                          example="Jhon Doe")
    phone_number: str = Field(..., max_length=10,
                              example="123456789")
    email: str = Field(..., strip_whitespace=True, unique=True,
                       regex="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", example="x@y.com")


class SchemaUpdatePassword(BaseModel):
    token_change_password: str = Field(..., example="token")
    password: str = Field(..., min_length=8, example="Password123")
    new_password: str = Field(..., min_length=8, example="Password123")
    confirm_password: str = Field(..., min_length=8, example="Password123")


class SchemaPartialUpdateUser(BaseModel):
    username: Optional[str] = Field(..., min_length=3, max_length=100, example="Jhon Doe")
    phone_number: Optional[str] = Field(..., max_length=10, example="123456789")
    company_name: Optional[str] = Field(..., max_length=100, example="Company")
    email: Optional[str] = Field(..., strip_whitespace=True, unique=True,
                                 regex="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
                                 example="x@y.com")


class SchemaError(BaseModel):
    detail: str = Field(..., example="Error message")

    class Config:
        orm_mode = True
