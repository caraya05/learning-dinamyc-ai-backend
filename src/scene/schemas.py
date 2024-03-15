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
    game_id: str
    characters_id: list[str]
    location_id: str
    start_dialogues: list[dict]
    end_dialogues: list[dict]
    questions: dict | None
    content: str
    dynamic: str
    reward: str
    count_enemies: int
    enemy_id: str | None
    is_subtractable: bool
    start_content: str | None
    start_image: str | None
    object_id: str | None
    delivery_location_id: str | None
    delivery_character_id: str | None
    image_defeat: str | None


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
    characters_id: Optional[list[str]] | None
    location_id: Optional[str] | None
    content: str
    dynamic: str


    class Config:
        orm_mode = True


class SchemaRetrieveSceneComplete(BaseModel):
    """
    Schema for retrieving a scene with all the related fields
    """
    id: str
    order: int
    title: str
    description: str | None
    script_id: str
    game_id: Optional[str]
    characters_id: list[str]
    location_id: Optional[str] | None
    start_dialogues: Optional[list[dict]] | None
    end_dialogues: Optional[list[dict]] | None
    questions: Optional[dict] | None
    content: Optional[str] | None
    dynamic: Optional[str] | None
    reward: Optional[str] | None
    count_enemies: Optional[int]
    enemy_id: Optional[str]
    is_subtractable: bool = False
    start_content: Optional[str]
    start_image: Optional[str]
    object_id: Optional[str]
    delivery_location_id: Optional[str]
    delivery_character_id: Optional[str]
    image_defeat: Optional[str]

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
