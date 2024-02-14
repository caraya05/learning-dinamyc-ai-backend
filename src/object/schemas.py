from pydantic import BaseModel
from typing import Optional


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
    type: str
    script_id: str
    game_id: str


class SchemaPartialUpdateObject(BaseModel):
    """
    Schema for partially updating a objective.

    Attributes:
    title (Optional[str]): The title of the objective.
    description (Optional[str]): The description of the objective.
    image (Optional[str]): The image of the objective.
    """
    name: Optional[str]
    description: Optional[str]
    image: Optional[str]
    type: Optional[str]


class SchemaRetrieveObject(BaseModel):
    """
    Schema for retrieving a objective.

    Attributes:
    id (int): The id of the objective.
    title (str): The title of the objective.
    description (str): The description of the objective.
    """
    id: str
    name: str
    description: str
    image: Optional[str]
    type: str

    class Config:
        orm_mode = True


class SchemaListObject(BaseModel):
    """
    Schema for listing objectives.

    Attributes:
    results (list[SchemaRetrieveObject]): The list of objectives.
    count (int): The number of objectives.
    """
    results: list[SchemaRetrieveObject]
    count: int
