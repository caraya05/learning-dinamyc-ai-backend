from pydantic import BaseModel


class Token(BaseModel):
    access: str
    refresh: str
    token_type: str


class Credentials(BaseModel):
    email: str
    password: str


class Refresh(BaseModel):
    refresh_token: str
