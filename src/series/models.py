from datetime import datetime
from pydantic import BaseModel
from pydantic import Field
from typing import Optional


class Series(BaseModel):
    title: Optional[str] = Field(None, example="Series Title")
    description: Optional[str] = Field(None, example="This is a series description")
    image: Optional[str] = Field(None, example="image.jpg")
    category_id: Optional[str] = Field(None, example="Category")
    played_count: Optional[int] = Field(0, example=0)
    views: Optional[int] = Field(0, example=0)
    rating: Optional[float] = Field(0.0, example=4.5)
    main_character: Optional[str] = Field(None, example="Character Name")
    games_id: Optional[list[str]] = Field([], example=["123", "456"])
    hidden_games: Optional[list[str]] = Field([], example=["123"], description="Game ids hidden within the series context")
    is_active: Optional[bool] = Field(True, example=True)
    is_published: Optional[bool] = Field(False, example=False)
    is_link: Optional[bool] = Field(False, example=False, description="True if published via link access")
    publish_type: Optional[str] = Field("private", example="public")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
