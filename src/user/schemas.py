import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


class SchemaBaseUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, strip_whitespace=True,
                          example="user")
    password: str = Field(..., min_length=8, example="Password123")


class SchemaUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=100,
                          example="Jhon Doe")
    phone_number: str = Field(..., max_length=10,
                              example="123456789")
    email: str = Field(..., strip_whitespace=True, unique=True,
                       regex="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", example="jhon@gmail.com")
    password: str = Field(..., min_length=8, example="password123")


class SchemaRetrieveUser(BaseModel):
    id: UUID
    username: str = Field(..., min_length=3, max_length=100,
                          example="Jhon Doe")
    phone_number: str = Field(..., max_length=10,
                              example="123456789")
    email: str = Field(..., strip_whitespace=True, unique=True, example="jhon@gmail.com")

    created_at: datetime.date = Field(default=datetime.datetime.utcnow())
    updated_at: datetime.date = Field(default=datetime.datetime.utcnow())

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
