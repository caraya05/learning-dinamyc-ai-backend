from pydantic import BaseModel
from pydantic import Field

from typing import Optional

from core.schemas import ResponseModel


class BaseConfigurationSchema(BaseModel):
    featured_games: Optional[list] = Field(
        ..., example=["game1", "game2"], description="Featured games"
    )
    popular_games: Optional[list] = Field(
        ..., example=["game1", "game2"], description="Popular games"
    )
    games_by_category: Optional[dict] = Field(
        ..., example={"category1": ["game1", "game2"]}, description="Games by category"
    )
    stars_news_users: Optional[int] = Field(..., example=0, description="Stars news users")
    stars_by_game: Optional[int] = Field(..., example=0, description="Stars by game")
    stars_by_creation_place: Optional[int] = Field(
        0, example=0, description="Stars by creation place"
    )
    stars_by_creation_location: Optional[int] = Field(
        0, example=0, description="Stars by creation location"
    )


class SchemaRetrieveConfiguration(BaseConfigurationSchema, ResponseModel):
    pass


class SchemaUpdateConfiguration(BaseConfigurationSchema):
    pass


class SchemaCreateConfiguration(SchemaUpdateConfiguration):
    pass


class SchemaListConfiguration(BaseModel):
    results: list[SchemaRetrieveConfiguration]
    count: int
