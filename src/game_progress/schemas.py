from pydantic import BaseModel
from typing import Optional


class SchemaCreateGameProgress(BaseModel):
    """
    Schema for creating a game progress
    """
    # user_id: str
    game_id: str
    scene_id: str
    object: list[str]
    life: int
    location_id: str


class SchemaPartialUpdateGameProgress(BaseModel):
    """
    Schema for partially updating a game progress
    """
    game_id: Optional[str]
    scene_id: Optional[str]
    object: Optional[list[str]]
    life: Optional[int]


class SchemaRetrieveGameProgress(BaseModel):
    """
    Schema for retrieving a game progress
    """
    id: str
    user_id: str
    game_id: str
    scene_id: str
    object: list[str]
    life: int
    location_id: str
    is_complete: bool

    class Config:
        orm_mode = True


class SchemaListGameProgress(BaseModel):
    """
    Schema for listing game progress
    """
    results: list[SchemaRetrieveGameProgress]
    count: int

    class Config:
        orm_mode = True
