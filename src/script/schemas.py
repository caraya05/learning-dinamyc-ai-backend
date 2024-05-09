from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional

from core import PyObjectId
from scene.schemas import SchemaRetrieveScene
from character.schemas import SchemaRetrieveCharacterStr
from location.schemas import SchemaRetrieveLocationStr
from object.schemas import SchemaRetrieveObjectStr


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")


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


class SchemaRetrieveScript(ResponseModel):
    """
    Schema for retrieving a script.

    Attributes:
    id (int): The id of the script.
    title (str): The title of the script.
    description (str): The description of the script.
    """

    title: Optional[str] = Field(None, title="The title of the script")
    description: Optional[str] = Field(None, title="The description of the script")
    order: Optional[int]
    status: Optional[int] = Field(0, title="The status of the script")
    status_character: Optional[int] = Field(0, title="The status of the characters in the script")
    status_location: Optional[int] = Field(0, title="The status of the locations in the script")
    status_scene: Optional[int] = Field(0, title="The status of the scenes in the script")

    class Config:
        orm_mode = True

class SchemaRetrieveScriptStr(ResponseModelStr):
    """
    Schema for retrieving a script.

    Attributes:
    id (int): The id of the script.
    title (str): The title of the script.
    description (str): The description of the script.
    """

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
    characters: list[SchemaRetrieveCharacterStr] = Field([], title="The characters in the script")
    locations: list[SchemaRetrieveLocationStr] = Field([], title="The locations in the script")
    objects: list[SchemaRetrieveObjectStr] = Field([], title="The objects in the script")
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

    results: list[SchemaRetrieveScriptStr]
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
