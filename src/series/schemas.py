from datetime import datetime
from typing import Optional, Union
from bson import ObjectId
from core.schemas import ResponseModel
from pydantic import BaseModel, Field, validator


class SchemaCreateSeries(BaseModel):
    title: str = Field(..., min_length=3, max_length=100, example="Series Title")
    description: Optional[str] = Field(None, example="Series description")
    image: Optional[str] = Field(None, example="image.jpg")
    category_id: Optional[str] = Field(None, example="category_id")
    main_character: Optional[str] = Field(None, example="Character Name")


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
    is_published: bool = Field(..., example=True, description="Whether to publish or unpublish the series")


class SchemaViewsInfo(BaseModel):
    total: int = Field(0, example=100, description="Total views from all games in the series")
    most_viewed_game: int = Field(0, example=50, description="Views of the game with most views in the series")


class SchemaPublishedSeriesDetail(BaseModel):
    id: str = Field(alias="_id")
    title: str = Field(..., example="Series Title")
    description: Optional[str] = Field(None, example="Series description")
    image: Optional[str] = Field(None, example="image.jpg")
    category_id: Optional[str] = Field(None, example="category_id")
    main_character: Optional[str] = Field(None, example="Character Name")
    played_count: int = Field(0, example=0)
    views: int = Field(0, example=0)
    rating: float = Field(0.0, example=4.5)
    games: Optional[list] = Field([], example=[])

    class Config:
        json_encoders = {ObjectId: str}


class SchemaPublishedSeriesListItem(BaseModel):
    id: str = Field(alias="_id")
    title: str = Field(..., example="Series Title")
    description: Optional[str] = Field(None, example="Series description")
    image: Optional[str] = Field(None, example="image.jpg")
    category_id: Optional[str] = Field(None, example="category_id")
    main_character: Optional[str] = Field(None, example="Character Name")
    played_count: int = Field(default=0, example=0)
    views: Union[SchemaViewsInfo, dict] = Field(default_factory=lambda: SchemaViewsInfo(total=0, most_viewed_game=0), description="Views analytics from games in the series")
    rating: float = Field(default=0.0, example=4.5)
    games: Optional[list] = Field(default_factory=list, example=[])

    @validator("views", pre=True)
    @classmethod
    def validate_views(cls, v):
        if isinstance(v, dict):
            return SchemaViewsInfo(
                total=v.get("total", 0),
                most_viewed_game=v.get("most_viewed_game", 0)
            )
        return v

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True


class SchemaListPublishedSeries(BaseModel):
    count: int
    results: list[SchemaPublishedSeriesListItem]
    page: int
    total_pages: int









