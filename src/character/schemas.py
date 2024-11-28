from datetime import datetime
from typing import Optional, Dict

from bson import ObjectId
from pydantic import BaseModel
from pydantic import Field

from character.enums import TypeCharacter
from character.enums import GenderCharacter
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
    sound: Optional[str] = Field(None, example="123")


class SchemaStateItem(BaseModel):
    order: Optional[int] = Field(None, example=1)
    state: Optional[str] = Field(None, example="state")
    data: Optional[SchemaStateData] = Field(None, example={})



class SchemaDataCharacter(BaseModel):
    name: str = Field(..., example="Character Name")
    description: Optional[str] = Field(None, example="This is a character")
    description_shoulder_up: Optional[str] = Field(None, example="This is a character")
    is_active: bool = Field(default=True, example=True)
    prompt_user: str = Field(None, example="prompt_user")
    # prompt_user_dialog: str = Field(None, example="prompt_user_dialog")
    body_type: Optional[str] = Field(None, example="body_type")
    genre: Optional[str] = Field(None, example=GenderCharacter.MAN)
    character_type: Optional[str] = Field(None, example="character_type")
    image: Optional[str] = Field(None, example="image.jpg")
    locations_id: Optional[list] = Field(None, example="location_id")
    extra_data: Optional[dict] = Field(None, example="Extra data")
    # conversation_type: str = Field(...)
    interaction: Optional[list[dict]] = Field([], example=[{"key": "value"}])
    type: Optional[str] = Field(None, example=TypeCharacter.NPC)
    characteristics: Optional[dict] = Field(None, example={"key": "value"})


class SchemaStateLocation(BaseModel):
    order: Optional[int] = Field(None, example=1)
    state: Optional[str] = Field(None, example="state")
    data: Optional[SchemaDataCharacter] = Field(None, example={})


class SchemaCreateCharacter(BaseModel):
    name: str = Field(..., max_length=100, example="Jhon Doe")
    prompt_user: str = Field(..., example="prompt_user")
    prompt_user_dialog: Optional[str] = Field(None, example="prompt_user_dialog")
    conversation_type: str = Field(..., example="conversation_type")
    game_id: Optional[str] = Field(None, example="location_id")
    location_id: Optional[str] = Field(None, example="location_id")


class SchemaRetrieveCharacter(ResponseModel):
    game_id: Optional[str] = Field(..., example="game_id")
    task_id: Optional[str] = Field(None, example="task_db")
    status: Optional[str] = Field(1, example="status")
    state_game: Optional[list[SchemaStateLocation]] = Field([], example=["state_game"])


class SchemaRetrieveCharacterStr(ResponseModelStr):
    game_id: Optional[str] = Field(..., example="game_id")
    task_id: Optional[str] = Field(None, example="task_db")
    status: Optional[str] = Field(1, example="status")
    state_game: Optional[list[SchemaStateLocation]] = Field([], example=["state_game"])

    # weapon: Optional[SchemaRetrieveWeapon] = Field(None, example="weapon")


class SchemaCreateCharacterCollection(BaseModel):
    prompt_user: str = Field(..., example="prompt_user")
    name: str = Field(..., example="name")


class SchemaUpdateCharacterCollection(BaseModel):
    name: Optional[str] = Field(None, max_length=100, example="Jhon Doe")
    prompt_user: Optional[str] = Field(None, example="prompt_user")
    prompt_user_dialog: Optional[str] = Field(None, example="prompt_user_dialog")
    conversation_type: Optional[str] = Field(None, example="conversation_type")
    location_id: Optional[str] = Field(None, example="location_id")
    game_id: Optional[str] = Field(None, example="game_id")


class SchemaPartialUpdateCharacter(BaseModel):
    image: Optional[str] = Field(None, example="image")


class SchemaListCharacter(BaseModel):
    results: list[SchemaRetrieveCharacterStr]
    count: int

    class Config:
        orm_mode = True


class SchemaUpdatePhotoCharacter(BaseModel):
    image: str = Field(..., example="image")


class SchemaAddCharacterLocation(BaseModel):
    location_id: str = Field(..., example="location_id")
    character_id: str = Field(..., example="character_id")


class SchemaNewInteraction(BaseModel):
    location_id: str = Field(..., example="location_id")
    game_id: str = Field(..., example="game_id")
    conversation_type: str = Field(..., example="conversation_type")
    prompt_user_dialog: str = Field(..., example="prompt_user_dialog")
    options_dialog: Optional[list[dict]] = Field(..., example=[{"key": "value"}])


class CharacterLocationModel(BaseModel):
    character_id: str = Field(...)
    location_id: str = Field(...)
    game_id: str = Field(...)
    characteristics: Dict[str, str] = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(...)
    updated_by: str = Field(...)

    class Config:
        json_encoders = {ObjectId: str}


class SchemaUpdatedCharacterLocation(BaseModel):
    character_id: str = Field(...)
    location_id: str = Field(...)
    game_id: str = Field(...)
    characteristics: Dict[str, str] = Field(...)
