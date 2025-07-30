from pydantic import BaseModel, EmailStr
from datetime import datetime


class Token(BaseModel):
    access: str
    refresh: str
    token_type: str


class Credentials(BaseModel):
    email: str
    password: str


class Refresh(BaseModel):
    refresh: str


class GameCode(BaseModel):
    code: str


class VerificationRequest(BaseModel):
    email: EmailStr


class VerificationCode(BaseModel):
    email: EmailStr
    code: str


class VerificationCodeDB(BaseModel):
    email: EmailStr
    code: str
    created_at: datetime
