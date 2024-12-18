from datetime import datetime

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
    name: str = Field(None, example="Object Name")
    prompt_user: str = Field(None, example="Prompt User")
    prompt_user_dialog: Optional[str] = Field(None, example="Prompt User Dialog")
    type_item: Optional[str] = Field(None, example="type_item")
    image: Optional[str] = Field(None, example="image.jpg")
    interaction: Optional[list] = Field(None, example={"key": "value"})
    location_id: Optional[str] = Field(None, example="123")
    is_active: Optional[bool] = Field(None, example=True)



class SchemaStateLocation(BaseModel):
    order: Optional[int] = Field(None, example=1)
    state: Optional[str] = Field(None, example="state")
    data: Optional[SchemaStateData] = Field(None, example={})


class SchemaObject(BaseModel):
    """
    Schema for a objective.

    Attributes:
    name (str): The name of the object.
    prompt_user (str): The prompt_user of the object.
    """

    name: str
    prompt_user: str
    type_item: Optional[str] = None
    prompt_user_dialog: Optional[str] = None


class SchemaCreateObject(BaseModel):
    """
    Schema for creating a new objective.

    Attributes:
    title (str): The title of the objective.
    description (Optional[str]): The description of the objective.
    image (Optional[str]): The image of the objective.
    """

    name: str
    prompt_user: str
    type_item: Optional[str] = None
    prompt_user_dialog: Optional[str] = None
    game_id: Optional[str] = None
    location_id: Optional[str] = None
    state_game: Optional[str] = None

class SchemaPartialUpdateObject(SchemaCreateObject):
    """
    Schema for partially updating a objective.

    Attributes:
    title (Optional[str]): The title of the objective.
    description (Optional[str]): The description of the objective.
    image (Optional[str]): The image of the objective.
    """

    name: str
    prompt_user: str
    type_item: Optional[str] = None
    prompt_user_dialog: Optional[str] = None


class SchemaRetrieveObject(ResponseModel):
    """
    Schema for retrieving a objective.

    Attributes:
    id (int): The id of the objective.
    title (str): The title of the objective.
    description (str): The description of the objective.
    """
    game_id: Optional[str] = None
    task_id: Optional[str] = None
    status: Optional[int] = 1
    state_game: Optional[list[SchemaStateLocation]]

    class Config:
        orm_mode = True


class SchemaRetrieveObjectStr( ResponseModelStr):
    """
    Schema for retrieving a objective.

    Attributes:
    id (int): The id of the objective.
    title (str): The title of the objective.
    description (str): The description of the objective.
    """
    game_id: Optional[str] = None
    task_id: Optional[str] = None
    status: Optional[int] = 1
    state_game: Optional[list[SchemaStateLocation]] = []

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


class SchemaCreateItem(BaseModel):
    """
    Schema for creating a new objective.

    Attributes:
    title (str): The title of the objective.
    description (Optional[str]): The description of the objective.
    image (Optional[str]): The image of the objective.
    """

    name: str
    prompt_user: str
    type_item: Optional[str] = None
    prompt_user_dialog: Optional[str] = None
    game_id: Optional[str] = None
    state_game: Optional[str] = None
    location_id: Optional[str] = None


class ObjectLocationModel(BaseModel):
    item_id: str = Field(None, example="object_id")
    location_id: str = Field(None, example="location_id")
    characteristics: dict = Field(None, example={"key": "value"})
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(...)
    updated_by: str = Field(...)

    class Config:
        json_encoders = {ObjectId: str}


class SchemaUpdatedObjectLocation(BaseModel):
    item_id: str = Field(...)
    location_id: str = Field(...)
    game_id: str = Field(...)
    state_game: Optional[str] = Field(None)
    characteristics: dict = Field(...)


class SchemaAddItemLocation(BaseModel):
    location_id: str = Field(..., example="location_id")
    item_id: str = Field(..., example="character_id")

class SchemaAddItemGame(BaseModel):
    game_id: str = Field(..., example="game_id")
    item_id: str = Field(..., example="character_id")


class SchemaNewInteractionItem(BaseModel):
    location_id: str = Field(..., example="location_id")
    game_id: str = Field(..., example="game_id")
    prompt_user_dialog: str = Field(..., example="prompt_user_dialog")
    state_game: Optional[str] = Field(None)


class SchemaDeactivateItem(BaseModel):
    """
    Schema for deactivating a location.

    Attributes:
    status (int): The status of the location.
    """

    is_active:bool = Field(False, example=False)
    state_game: str = Field(None, example="state_game")