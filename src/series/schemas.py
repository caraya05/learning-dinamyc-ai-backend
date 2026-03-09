from datetime import datetime
from typing import Optional, Union, List, Literal
from bson import ObjectId
from core.schemas import ResponseModel
from pydantic import BaseModel, Field, validator


class SchemaCreateSeries(BaseModel):
    title: str = Field(..., min_length=3, max_length=100, example="Series Title")
    description: Optional[str] = Field(None, example="Series description")
    image: Optional[str] = Field(None, example="image.jpg")
    category_id: Optional[str] = Field(None, example="category_id")
    main_character: Optional[str] = Field(None, example="Character Name")
    rating: Optional[float] = Field(None, example=4.5)


class SchemaRetrieveSeries(ResponseModel):
    title: str = Field(..., example="Series Title")
    description: Optional[str] = Field(None, example="Series description")
    image: Optional[str] = Field(None, example="image.jpg")
    category_id: Optional[str] = Field(None, example="category_id")
    main_character: Optional[str] = Field(None, example="Character Name")
    played_count: int = Field(0, example=0)
    views: int = Field(0, example=0)
    rating: float = Field(0.0, example=4.5)
    games_id: list[str] = Field([], example=["123", "456"])
    is_active: bool = Field(True, example=True)
    is_published: bool = Field(False, example=False)
    is_link: bool = Field(False, example=False, description="True if published by shareable link")
    publish_type: Optional[str] = Field("private", example="public")
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class SchemaRetrieveSeriesStr(ResponseModelStr):
    title: str = Field(..., example="Series Title")
    description: Optional[str] = Field(None, example="Series description")
    image: Optional[str] = Field(None, example="image.jpg")
    category_id: Optional[str] = Field(None, example="category_id")
    main_character: Optional[str] = Field(None, example="Character Name")
    played_count: int = Field(0, example=0)
    views: int = Field(0, example=0)
    rating: float = Field(0.0, example=4.5)
    games_id: list[str] = Field([], example=["123", "456"])
    is_active: bool = Field(True, example=True)
    is_published: bool = Field(False, example=False)
    is_link: bool = Field(False, example=False, description="True if published by shareable link")
    publish_type: Optional[str] = Field("private", example="public")
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


class SchemaListSeries(BaseModel):
    count: int
    results: list[SchemaRetrieveSeriesStr]
    page: int
    total_pages: int


class SchemaUpdateSeries(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100, example="Series Title")
    description: Optional[str] = Field(None, example="Series description")
    image: Optional[str] = Field(None, example="image.jpg")
    category_id: Optional[str] = Field(None, example="category_id")
    main_character: Optional[str] = Field(None, example="Character Name")
    rating: Optional[float] = Field(None, example=4.5)


class SchemaPublishSeries(BaseModel):
    is_published: bool = Field(..., example=True, description="Legacy publish flag; actual value derived from publish_type")
    publish_type: Literal["public", "link", "private"] = Field(..., example="public")


class SchemaReorderGames(BaseModel):
    games_order: List[str] = Field(..., min_items=1, description="List of game ids in the desired order")


class SchemaRemoveGame(BaseModel):
    game_id: str = Field(..., description="Game id to remove from the series")


class SchemaUpdateGameVisibility(BaseModel):
    is_hidden: bool = Field(..., description="Visibility flag scoped to the series-game relation")


class SchemaViewsInfo(BaseModel):
    games_count: int = Field(0, example=3, description="Number of games in the series")
    total_analytics_records: int = Field(0, example=45, description="Total number of analytics records across all games")


class SchemaMostViewedGameInfo(BaseModel):
    id: Optional[str] = Field(None, alias="_id", example="game_id", description="ID of the most viewed game")
    title: Optional[str] = Field(None, example="Juego más visto", description="Title of the most viewed game")
    views: int = Field(0, example=750, description="Number of views of the most viewed game")
    likes: int = Field(0, example=150, description="Number of likes of the most viewed game")
    plays: int = Field(0, example=200, description="Number of plays of the most viewed game")
    order: Optional[int] = Field(None, example=2, description="Order of the most viewed game in the series")
    image: Optional[str] = Field(None, example="image_url", description="Image URL of the most viewed game")

    class Config:
        populate_by_name = True


class SchemaPublishedSeriesListItem(BaseModel):
    id: str = Field(alias="_id")
    title: str = Field(..., example="Series Title")
    description: Optional[str] = Field(None, example="Series description")
    image: Optional[str] = Field(None, example="image.jpg")
    category_id: Optional[str] = Field(None, example="category_id")
    main_character: Optional[str] = Field(None, example="Character Name")
    played_count: int = Field(default=0, example=0)
    analytics: Optional[SchemaViewsInfo] = Field(default_factory=lambda: SchemaViewsInfo(total_views=0, total_likes=0, total_plays=0, games_count=0, total_analytics_records=0), description="Analytics aggregated from all games in the series")
    most_viewed_game_info: Optional[SchemaMostViewedGameInfo] = Field(None, description="Information of the game with most views in the series")
    rating: float = Field(default=0.0, example=4.5)
    publish_type: Optional[str] = Field("private", example="public")
    is_published: bool = Field(False, example=True)
    is_link: bool = Field(False, example=False)
    games: Optional[list] = Field(default_factory=list, example=[])

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True


class SchemaPublishedSeriesDetail(BaseModel):
    id: str = Field(alias="_id")
    title: str = Field(..., example="Series Title")
    description: Optional[str] = Field(None, example="Series description")
    image: Optional[str] = Field(None, example="image.jpg")
    category_id: Optional[str] = Field(None, example="category_id")
    main_character: Optional[str] = Field(None, example="Character Name")
    played_count: int = Field(0, example=0)
    analytics: Optional[SchemaViewsInfo] = Field(default_factory=lambda: SchemaViewsInfo( games_count=0, total_analytics_records=0), description="Analytics aggregated from all games in the series")
    most_viewed_game_info: Optional[SchemaMostViewedGameInfo] = Field(None, description="Information of the game with most views in the series")
    rating: float = Field(0.0, example=4.5)
    publish_type: Optional[str] = Field("private", example="public")
    is_published: bool = Field(False, example=True)
    is_link: bool = Field(False, example=False)
    games: Optional[list] = Field([], example=[])

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True


class SchemaListPublishedSeries(BaseModel):
    count: int
    results: list[SchemaPublishedSeriesListItem]
    page: int
    total_pages: int


class SchemaUserStats(BaseModel):
    """Response schema for user statistics endpoint"""
    total_series: int = Field(0, example=5, description="Total number of series created by the user")
    total_episodes: int = Field(0, example=24, description="Total number of episodes/games in all user series")
    published_episodes: int = Field(0, example=18, description="Total number of episodes/games in published series by the user")
    analytics_records: int = Field(0, example=156, description="Total number of analytics records for user's games")

