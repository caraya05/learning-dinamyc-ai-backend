from pydantic import BaseModel
from typing import Optional


class SchemaCreateScript(BaseModel):
    """
    Schema for creating a new script.

    Attributes:
    title (str): The title of the script.
    description (str): The description of the script.
    """

    title: str
    description: str


class SchemaRetrieveScript(BaseModel):
    """
    Schema for retrieving a script.

    Attributes:
    id (int): The id of the script.
    title (str): The title of the script.
    description (str): The description of the script.
    """

    id: int
    title: str
    description: str

    class Config:
        orm_mode = True


class SchemaListScript(BaseModel):
    """
    Schema for listing scripts.

    Attributes:
    results (list[SchemaRetrieveScript]): The list of scripts.
    count (int): The number of scripts.
    """

    results: list[SchemaRetrieveScript]
    count: int


class SchemaPartialUpdateScript(BaseModel):
    """
    Schema for partially updating a script.

    Attributes:
    title (Optional[str]): The title of the script.
    description (Optional[str]): The description of the script.
    """

    title: Optional[str]
    description: Optional[str]
