from bson import ObjectId

from pydantic import BaseModel
from pydantic import Field

from typing import Optional

from core import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")


class SchemaCreateLocation(BaseModel):
    """
    Schema for creating a new location.

    Attributes:
    name (str): The name of the location.
    description (Optional[str]): The description of the location.
    """
    title: Optional[str]
    description: Optional[str]
    image: Optional[str]
    prompt_user: Optional[str]
    # place_id: Optional[str]
    game_id: Optional[str]
    environment: Optional[dict]



class SchemaPartialUpdateLocation(BaseModel):
    """
    Schema for partially updating a location.

    Attributes:
    name (Optional[str]): The name of the location.
    description (Optional[str]): The description of the location.
    image (Optional[str]): The image of the location.
    """
    title: Optional[str]
    description: Optional[str]
    prompt_user: Optional[str]
    image: Optional[str]
    configuration: Optional[dict]
    environment: Optional[dict]
    connections: Optional[dict]


class SchemaRetrieveLocation(ResponseModel):
    """
    Schema for retrieving a location.

    Attributes:
    id (int): The id of the location.
    name (str): The name of the location.
    description (str): The description of the location.
    """

    title: Optional[str]
    description: Optional[str]
    image: Optional[str]
    prompt_user: Optional[str]
    attempts: Optional[int] = 3
    configuration: Optional[dict] = {}
    connections: Optional[dict] = {}
    sound_id: Optional[str | dict] = Field(None)
    characters: Optional[list] = []
    environment: Optional[dict] = {}

    class Config:
        orm_mode = True


class SchemaRetrieveLocationStr(ResponseModelStr):
    """
    Schema for retrieving a location.

    Attributes:
    id (int): The id of the location.
    name (str): The name of the location.
    description (str): The description of the location.
    """

    title: str
    description: Optional[str]
    image: Optional[str]
    attempts: Optional[int]
    configuration: Optional[dict]
    connections: Optional[dict]
    sound_id: Optional[str | dict] = Field(None)
    environment: Optional[dict] = {}

    class Config:
        orm_mode = True


class SchemaListLocation(BaseModel):
    """
    Schema for listing locations.

    Attributes:
    results (list[SchemaRetrieveLocation]): The list of locations.
    count (int): The number of locations.
    """

    results: list[SchemaRetrieveLocationStr]
    count: int

    class Config:
        orm_mode = True
