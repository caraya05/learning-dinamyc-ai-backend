from pydantic import BaseModel
from typing import Optional


class SchemaCreateLocation(BaseModel):
    """
    Schema for creating a new location.

    Attributes:
    name (str): The name of the location.
    description (Optional[str]): The description of the location.
    """
    name: str
    description: str
    image: Optional[str]


class SchemaPartialUpdateLocation(BaseModel):
    """
    Schema for partially updating a location.

    Attributes:
    name (Optional[str]): The name of the location.
    description (Optional[str]): The description of the location.
    image (Optional[str]): The image of the location.
    """
    name: Optional[str]
    description: Optional[str]
    image: Optional[str]


class SchemaRetrieveLocation(BaseModel):
    """
    Schema for retrieving a location.

    Attributes:
    id (int): The id of the location.
    name (str): The name of the location.
    description (str): The description of the location.
    """
    id: int
    name: str
    description: str
    name: str

    class Config:
        orm_mode = True


class SchemaListLocation(BaseModel):
    """
    Schema for listing locations.

    Attributes:
    results (list[SchemaRetrieveLocation]): The list of locations.
    count (int): The number of locations.
    """
    results: list[SchemaRetrieveLocation]
    count: int

    class Config:
        orm_mode = True
