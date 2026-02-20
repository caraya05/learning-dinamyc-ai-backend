from bson import ObjectId

from pydantic import BaseModel, ConfigDict
from pydantic import Field

from typing import Optional, Any

from core import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")


class SchemaInteractionVideo(BaseModel):
    url: Optional[str] = Field(None, example="https://storage.googleapis.com/qwestar/location-interactions/6949c6b6637f32684a99b357/state-6949c689637f32684a99b34a/dialog-2-21e5fa0d-19b3-4897-9734-20ed502f9bda.mp4")
    dialog_number: Optional[int] = Field(None, example=2)
    compressed_quality: Optional[str] = Field(None, example="medium")
    file_name: Optional[str] = Field(None, example="location-interactions/6949c6b6637f32684a99b357/state-6949c689637f32684a99b34a/dialog-2-21e5fa0d-19b3-4897-9734-20ed502f9bda.mp4")


class SchemaStateData(BaseModel):
    title: Optional[str] = Field(None, example="Location Title")
    description: Optional[str] = Field(None, example="This is a location description")
    prompt_user: Optional[str] = Field(None, example="This is a prompt user")
    image: Optional[str] = Field(None, example="image.jpg")
    configuration: Optional[dict] = Field(None, example="")
    connections: Optional[dict] = Field(None, example="")
    environment: Optional[dict] = Field(None, example="{}")
    is_active: Optional[bool] = Field(None, example=True)
    interaction_videos: Optional[SchemaInteractionVideo] = Field(default_factory=list, example=[])
    # sound: Optional[str] = Field(None, example="123")
    # sound_mp3: Optional[str] = Field(None, example="123.mp3")


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
    url_image_reference (Optional[str]): Reference image URL for the location.
    """

    title: Optional[str] = None
    prompt_user: Optional[str] = None
    prompt_user_description: Optional[str] = Field(None, example="This is a prompt user")
    game_id: Optional[str] = None
    state_game: Optional[str] = None
    url_image_reference: Optional[str] = Field(None, example=None, description="Reference image URL for the location")


class SchemaPartialUpdateLocation(BaseModel):
    """
    Schema for partially updating a location.

    Attributes:
    name (Optional[str]): The name of the location.
    description (Optional[str]): The description of the location.
    image (Optional[str]): The image of the location.
    """

    title: Optional[str] = Field(None, example="Location Title")
    prompt_user: Optional[str] = Field(None, example="This is a prompt user")
    configuration: Optional[dict] = Field(None, example={})
    connections: Optional[dict] = Field(None, example={})
    game_id: Optional[str] = Field(None, example="game_id")
    state_game: Optional[str] = Field(None, example="state_game")


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
    state_game: Optional[list[SchemaStateLocation]] = Field(default_factory=list, example=[])
    status: Optional[int] = Field(1, example="status")
    characters: Optional[list[dict]] = Field(default_factory=list)
    tasks_request: Optional[list[str]] = Field(default_factory=list)
    tasks_notified: Optional[list[str]] = Field(default_factory=list)
    created_at: Optional[Any] = Field(None)
    created_by: Optional[str] = Field(None)
    updated_at: Optional[Any] = Field(None)
    updated_by: Optional[str] = Field(None)

    model_config = ConfigDict(from_attributes=True)


class SchemaListLocation(BaseModel):
    """
    Schema for listing locations.

    Attributes:
    results (list[SchemaRetrieveLocation]): The list of locations.
    count (int): The number of locations.
    """

    results: list[SchemaRetrieveLocationStr] = Field(default_factory=list)
    count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SchemaDeactivateLocation(BaseModel):
    """
    Schema for deactivating a location.

    Attributes:
    status (int): The status of the location.
    """

    is_active: bool = Field(False, example=False)
    state_game: Optional[str] = Field(None, example="state_game")


class SchemaLocationInteractionVideo(BaseModel):
    """
    Schema for uploading interaction video to a location.

    Attributes:
    location_id (str): The location ID.
    state (str): The state/state_game ID.
    dialog_number (int): The dialog number in the interaction.
    """

    location_id: str = Field(..., example="location_id")
    state: str = Field(..., example="state_game_id")
    dialog_number: int = Field(..., example=1, description="Dialog number in the interaction")
