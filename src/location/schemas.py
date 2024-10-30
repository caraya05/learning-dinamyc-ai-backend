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
    prompt_user: Optional[str]


class SchemaPartialUpdateLocation(BaseModel):
    """
    Schema for partially updating a location.

    Attributes:
    name (Optional[str]): The name of the location.
    description (Optional[str]): The description of the location.
    image (Optional[str]): The image of the location.
    """

    title: Optional[str]
    prompt_user: Optional[str]
    configuration: Optional[dict]
    connections: Optional[dict]


class SchemaRetrieveLocation(ResponseModel):
    """
    Schema for retrieving a location.

    Attributes:
    id (int): The id of the location.
    name (str): The name of the location.
    description (str): The description of the location.
    """

    title: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    image: Optional[str] = Field(None)
    prompt_user: Optional[str] = Field(None)
    configuration: Optional[dict] = {}
    connections: Optional[dict] = {}
    sound: Optional[str | dict] = Field(None)
    characters: Optional[list] = []
    environment: Optional[dict] = {}
    status: Optional[int] = Field(1, example="status")
    task_id: Optional[str] = Field(None, example="task_db")

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

    title: Optional[str]
    description: Optional[str]
    image: Optional[str]
    configuration: Optional[dict]
    connections: Optional[dict]
    sound_id: Optional[str] = Field(None)
    environment: Optional[dict] = {}
    status: Optional[int] = Field(1, example="status")

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
