from bson import ObjectId

from pydantic import BaseModel
from pydantic import Field

from typing import Optional

from core.database import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}

    def __iter__(self):
        yield 'id', self.id


class SchemaCreatePrompt(BaseModel):
    """
    Schema for creating a prompt
    """

    title: str
    description: str
    prompt_system: str
    category: str
    is_active: bool


class SchemaPartialUpdatePrompt(BaseModel):
    """
    Schema for partially updating a prompt
    """

    title: str
    description: str
    prompt_system: str
    category: str
    is_active: bool


class SchemaRetrievePrompt(ResponseModel):
    """
    Schema for retrieving a prompt
    """

    title: Optional[str]
    description: Optional[str]
    prompt_system: Optional[str]
    category: Optional[str]
    is_active: bool = True

    class Config:
        orm_mode = True


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}

    def __iter__(self):
        yield 'id', self.id


class SchemaRetrieveListPrompt(ResponseModelStr):
    """
    Schema for retrieving a prompt
    """
    title: Optional[str] = Field(..., example="Prompt Title")
    description: Optional[str] = Field(..., example="This is a prompt description")
    prompt_system: Optional[str] = Field(..., example="Prompt System")
    category: Optional[str] = Field(..., example="Prompt Category")
    is_active: bool = True

    class Config:
        orm_mode = True


class SchemaListPrompt(BaseModel):
    """
    Schema for listing prompts
    """

    results: list[SchemaRetrieveListPrompt]
    count: int

    class Config:
        orm_mode = True
