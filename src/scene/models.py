from pydantic import BaseModel
from pydantic import Field
from datetime import datetime
from typing import Optional


class Scene(BaseModel):
    order: int = Field(..., example=1)
    title: str = Field(..., example="Scene Title")
    description: str = Field(None, example="This is a scene description")
    script_id: str = Field(..., example="123")
    game_id: str = Field(None, example="123")
    location_id: str = Field(None, example="123")
    characters_id: list[str] = Field(None, example={"123": "Character 1", "456": "Character 2"})
    start_dialogues: Optional[list[dict]] = Field(None, example={"1": "Hello", "2": "Hi"})
    end_dialogues: Optional[list[dict]] = Field(None, example={"1": "Goodbye", "2": "Bye"})
    questions: dict = Field(None, example={"1": "Question 1", "2": "Question 2"})
    dynamic: str = Field(None, example="Dynamic")
    content: str = Field(None, example="Content")
    reward: str = Field(None, example="Reward")
    count_enemies: Optional[int] = Field(None, example=1)
    enemy_id: Optional[str] = Field(None, example="123")
    is_subtract: bool = Field(None, example=True)
    start_content: Optional[str] = Field(None, example="Start Content")
    start_image: Optional[str] = Field(None, example="image.jpg")
    object_id: Optional[str] = Field(None, example="123")
    delivery_location_id: Optional[str] = Field(None, example="123")
    delivery_character_id: Optional[str] = Field(None, example="123")
    image_defeat: Optional[str] = Field(None, example="image.jpg")
    sound_id: Optional[str] = Field(None, example="123")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
