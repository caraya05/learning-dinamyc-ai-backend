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


class SchemaStateData(BaseModel):
    title: str = Field(None, example="Location Title")
    description: Optional[str] = Field(None, example="This is a location description")
    prompt_user: str = Field(None, example="This is a prompt user")
    image: Optional[str] = Field(None, example="image.jpg")
    configuration: Optional[dict] = Field(None, example="")
    connections: Optional[dict] = Field(None, example="")
    environment: Optional[dict] = Field(None, example="{}")
    sound: Optional[str] = Field(None, example="123")


class SchemaStateLocation(BaseModel):
    order: Optional[int] = Field(None, example=1)
    state: Optional[str] = Field(None, example="state")
    data: Optional[SchemaStateData] = Field(None, example={})



class SchemaCreateLocation(BaseModel):
    """
    Schema for creating a new location.

    Attributes:
    name (str): The name of the location.
    description (Optional[str]): The description of the location.
    """

    title: Optional[str]
    prompt_user: Optional[str]
    game_id: Optional[str]
    state_game: Optional[str]


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
    game_id: Optional[str]
    state_game: Optional[str]



class SchemaRetrieveLocation(ResponseModel):
    """
    Schema for retrieving a location.

    Attributes:
    id (int): The id of the location.
    name (str): The name of the location.
    description (str): The description of the location.
    """

    game_id: Optional[str] = Field(None)
    task_id: Optional[str] = Field(None, example="task_db")
    state_game: Optional[list[SchemaStateLocation]] = Field([], example=["state_game"])
    status: Optional[int] = Field(1, example="status")

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

    game_id: Optional[str] = Field(None)
    task_id: Optional[str] = Field(None, example="task_db")
    state_game: Optional[list[SchemaStateLocation]] = Field([], example=["state_game"])
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


class SchemaDeactivateLocation(BaseModel):
    """
    Schema for deactivating a location.

    Attributes:
    status (int): The status of the location.
    """

    is_active:bool = Field(False, example=False)
    state_game: str = Field(None, example="state_game")