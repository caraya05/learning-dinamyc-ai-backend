from pydantic import BaseModel
from pydantic import Field
from typing import List
from typing import Dict
from datetime import datetime


class Configuration(BaseModel):
    featured_games: List[str] = Field(None, example=["game1", "game2"])
    popular_games: List[str] = Field(None, example=["game1", "game2"])
    games_by_category: Dict[str, List[str]] = Field(None, example={"category1": ["game1", "game2"]})
    stars_news_users: int = Field(None, example=0)
    stars_by_game: int = Field(None, example=0)
    stars_by_creation_place: int = Field(None, example=0)
    stars_by_creation_location: int = Field(None, example=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
