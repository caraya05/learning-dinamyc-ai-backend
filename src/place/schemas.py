from bson import ObjectId

from pydantic import BaseModel
from pydantic import Field

from typing import Optional

from core import PyObjectId


class SchemaIdBase(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class SchemaIdBaseStr(BaseModel):
    id: str = Field(alias="_id")


class SchemaRetrievePlace(SchemaIdBase):
    title: Optional[str]
    description: Optional[str]
    image: Optional[str]
    prompt_user: Optional[str]
    locations_id: Optional[list[str]] = Field(None)


class SchemaRetrievePlaceStr(SchemaIdBaseStr):
    title: Optional[str]
    image: Optional[str]
    prompt_user: Optional[str]
    # locations_id: Optional[list] = []


class SchemaCreatePlace(BaseModel):
    """
    Schema for creating a new place.

    Attributes:
    name (str): The name of the place.
    description (Optional[str]): The description of the place.
    """
    title: Optional[str] = Field(None, example="Location Title")
    image: Optional[str] = Field(None, example="image.jpg")
    prompt_user: Optional[str] = Field(None, example="This is a prompt user")


class SchemaPartialUpdatePlace(BaseModel):
    """
    Schema for partially updating a place.

    Attributes:
    name (Optional[str]): The name of the place.
    description (Optional[str]): The description of the place.
    image (Optional[str]): The image of the place.
    """
    title: Optional[str]
    image: Optional[str]
    prompt_user: Optional[str]


class SchemeListPlace(BaseModel):
    """
    Schema for listing places.

    Attributes:
    name (str): The name of the place.
    description (Optional[str]): The description of the place.
    """
    results: list[SchemaRetrievePlaceStr]
    count: int
    page: int
    total_pages: int
