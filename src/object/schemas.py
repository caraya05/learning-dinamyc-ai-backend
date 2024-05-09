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


class SchemaObject(BaseModel):
    """
    Schema for a objective.

    Attributes:
    title (str): The title of the objective.
    description (str): The description of the objective.
    image (str): The image of the objective.
    """

    name: str
    description: str
    image: str
    function: Optional[str | None] = None
    script_id: Optional[str]
    game_id: Optional[str | None] = None


class SchemaCreateObject(BaseModel):
    """
    Schema for creating a new objective.

    Attributes:
    title (str): The title of the objective.
    description (Optional[str]): The description of the objective.
    image (Optional[str]): The image of the objective.
    """

    name: str
    description: str
    image: Optional[str]


class SchemaPartialUpdateObject(SchemaCreateObject):
    """
    Schema for partially updating a objective.

    Attributes:
    title (Optional[str]): The title of the objective.
    description (Optional[str]): The description of the objective.
    image (Optional[str]): The image of the objective.
    """
    pass


class SchemaRetrieveObject(SchemaObject, ResponseModel):
    """
    Schema for retrieving a objective.

    Attributes:
    id (int): The id of the objective.
    title (str): The title of the objective.
    description (str): The description of the objective.
    """

    class Config:
        orm_mode = True


class SchemaRetrieveObjectStr(SchemaCreateObject, ResponseModelStr):
    """
    Schema for retrieving a objective.

    Attributes:
    id (int): The id of the objective.
    title (str): The title of the objective.
    description (str): The description of the objective.
    """

    class Config:
        orm_mode = True


class SchemaListObject(BaseModel):
    """
    Schema for listing objectives.

    Attributes:
    results (list[SchemaRetrieveObject]): The list of objectives.
    count (int): The number of objectives.
    """

    results: list[SchemaRetrieveObjectStr]
    count: int

    class Config:
        orm_mode = True
