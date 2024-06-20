from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional

from core import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")


class SchemaCreateWeapon(BaseModel):
    """
    Schema for creating a new weapon.

    Attributes:
    name (str): The name of the weapon.
    description (Optional[str]): The description of the weapon.
    image (Optional[str]): The image of the weapon.
    """

    name: str
    description: Optional[str]
    image: Optional[str]
    type: str
    script_id: str
    game_id: str
    character_id: Optional[str]
    extra_data: Optional[dict]


class SchemaPartialUpdateWeapon(BaseModel):
    """
    Schema for partially updating a weapon.

    Attributes:
    name (Optional[str]): The name of the weapon.
    description (Optional[str]): The description of the weapon.
    image (Optional[str]): The image of the weapon.
    """

    name: Optional[str]
    description: Optional[str]

    image: Optional[str]
    type: Optional[str]

class SchemaPartialUpdateWeaponCollection(BaseModel):
    """
    Schema for partially updating a weapon.

    Attributes:
    name (Optional[str]): The name of the weapon.
    description (Optional[str]): The description of the weapon.
    image (Optional[str]): The image of the weapon.
    """

    name: Optional[str]
    prompt_user: Optional[str]
    type: Optional[str]


class SchemaRetrieveWeapon(ResponseModel):
    """
    Schema for retrieving a weapon.

    Attributes:
    id (int): The id of the weapon.
    name (str): The name of the weapon.
    description (str): The description of the weapon.
    """

    name: str
    description: str
    image: Optional[str]
    type: str

    class Config:
        orm_mode = True


class SchemaRetrieveWeaponStr(ResponseModelStr):
    """
    Schema for retrieving a weapon.

    Attributes:
    id (int): The id of the weapon.
    name (str): The name of the weapon.
    description (str): The description of the weapon.
    """

    name: str
    description: str
    image: Optional[str]
    type: str

    class Config:
        orm_mode = True


class SchemaListWeapon(BaseModel):
    """
    Schema for listing weapons.

    Attributes:
    id (int): The id of the weapon.
    name (str): The name of the weapon.
    description (str): The description of the weapon.
    """

    count: int
    results: list[SchemaRetrieveWeaponStr]

    class Config:
        orm_mode = True


class SchemaCreateForType(BaseModel):
    """
    Schema for creating a new weapon.

    Attributes:
    name (str): The name of the weapon.
    description (Optional[str]): The description of the weapon.
    image (Optional[str]): The image of the weapon.
    """

    type: str
    script_id: str
    game_id: str
    character_id: Optional[str]


class SchemaCreateWeaponCollectionBD(BaseModel):
    """
    Schema for creating a new weapon collection.

    Attributes:
    prompt_user (str): The prompt for the weapon collection.
    name (str): The name of the weapon collection.
    body_type (str): The body type of the weapon collection.
    collection_id (str): The id of the weapon collection.
    """

    name: str
    type: str
    prompt_user: str
    description: Optional[str]
    order: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")


class SchemaCreateWeaponCollection(BaseModel):
    """
    Schema for creating a new weapon collection.

    Attributes:
    prompt_user (str): The prompt for the weapon collection.
    name (str): The name of the weapon collection.
    body_type (str): The body type of the weapon collection.
    collection_id (str): The id of the weapon collection.
    """

    name: str
    type: str
    prompt_user: str
    collection_id: str

