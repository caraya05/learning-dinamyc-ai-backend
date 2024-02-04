from pydantic import BaseModel
from typing import Optional


class SchemaCreateScene(BaseModel):
    """
    Schema for creating a scene
    """
    order: int
    title: str
    description: str
    script_id: str
    characters_id: list[str]
    location_id: str
    dialogues: list[dict]
    content: str
    dynamic: str


class SchemaPartialUpdateScene(BaseModel):
    """
    Schema for partially updating a scene
    """
    order: Optional[int]
    title: Optional[str]
    description: Optional[str]
    script_id: Optional[str]
    characters: Optional[list[str]]


class SchemaRetrieveScene(BaseModel):
    """
    Schema for retrieving a scene
    """
    id: str
    order: int
    title: str
    description: str
    script_id: str
    characters_id: list[str]
    location_id: str
    dialogues: list[dict]
    content: str
    dynamic: str

    class Config:
        orm_mode = True


class SchemaListScene(BaseModel):
    """
    Schema for listing scenes
    """
    results: list[SchemaRetrieveScene]
    count: int

    class Config:
        orm_mode = True
