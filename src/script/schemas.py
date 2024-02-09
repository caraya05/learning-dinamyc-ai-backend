from pydantic import BaseModel, Field
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
    order: int
    game_id: str


class SchemaRetrieveScript(BaseModel):
    """
    Schema for retrieving a script.

    Attributes:
    id (int): The id of the script.
    title (str): The title of the script.
    description (str): The description of the script.
    """

    id: str
    title: Optional[str] = Field(None, title="The title of the script")
    description: Optional[str] = Field(None, title="The description of the script")
    order: int
    status: int = Field(0, title="The status of the script")
    status_character: int = Field(0, title="The status of the characters in the script")
    status_location: int = Field(0, title="The status of the locations in the script")
    status_scene: int = Field(0, title="The status of the scenes in the script")

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
    status: Optional[int]
    status_character: Optional[int]
    status_location: Optional[int]
    status_scene: Optional[int]
