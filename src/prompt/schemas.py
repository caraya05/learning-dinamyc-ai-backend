from pydantic import BaseModel
from typing import Optional


class SchemaCreatePrompt(BaseModel):
    """
    Schema for creating a prompt
    """
    title: str
    description: str
    script_id: str
    location_id: str
    characters_id: str


class SchemaPartialUpdatePrompt(BaseModel):
    """
    Schema for partially updating a prompt
    """
    title: Optional[str]
    description: Optional[str]
    script_id: Optional[str]
    location_id: Optional[str]
    characters_id: Optional[str]


class SchemaRetrievePrompt(BaseModel):
    """
    Schema for retrieving a prompt
    """
    id: str
    title: str
    description: str
    script_id: str
    location_id: str
    characters_id: str

    class Config:
        orm_mode = True


class SchemaListPrompt(BaseModel):
    """
    Schema for listing prompts
    """
    results: list[SchemaRetrievePrompt]
    count: int

    class Config:
        orm_mode = True
