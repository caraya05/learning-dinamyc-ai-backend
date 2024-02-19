from pydantic import BaseModel
from typing import Optional


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


class SchemaRetrieveWeapon(BaseModel):
    """
    Schema for retrieving a weapon.

    Attributes:
    id (int): The id of the weapon.
    name (str): The name of the weapon.
    description (str): The description of the weapon.
    """
    id: str
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
    results: list[SchemaRetrieveWeapon]

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
