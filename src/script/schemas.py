from pydantic import BaseModel, Field
from typing import Optional
from scene.schemas import SchemaRetrieveScene
from character.schemas import SchemaRetrieveCharacter
from location.schemas import SchemaRetrieveLocation
from object.schemas import SchemaRetrieveObject


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

    id: Optional[str]
    title: Optional[str] = Field(None, title="The title of the script")
    description: Optional[str] = Field(None, title="The description of the script")
    order: Optional[int]
    status: Optional[int] = Field(0, title="The status of the script")
    status_character: Optional[int] = Field(0, title="The status of the characters in the script")
    status_location: Optional[int] = Field(0, title="The status of the locations in the script")
    status_scene: Optional[int] = Field(0, title="The status of the scenes in the script")

    class Config:
        orm_mode = True


class SchemaRetrieveScriptComplete(SchemaRetrieveScript):
    scenes: list[SchemaRetrieveScene] = Field([], title="The scenes in the script")
    characters: list[SchemaRetrieveCharacter] = Field([], title="The characters in the script")
    locations: list[SchemaRetrieveLocation] = Field([], title="The locations in the script")
    objects: list[SchemaRetrieveObject] = Field([], title="The objects in the script")
    start_info: dict = Field({}, title="The start info of the script")
    end_info: dict = Field({}, title="The end info of the script")
    is_final: bool = Field(False, title="The final status of the script")

    class Config:
        orm_mode = True


class SchemaListScript(BaseModel):
    """
    Schema for listing scripts.

    Attributes:
    results (list[SchemaRetrieveScript]): The list of scripts.
    count (int): The number of scripts.
    """

    results: list[SchemaRetrieveScriptComplete]
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
