from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import Field
from pydantic import BaseModel

from core import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")


class SchemaCreateCharactersCollection(BaseModel):
    name: str = Field(..., example="Collection Name")
    description_base: str = Field(..., example="This is a character collection")
    characters_id: list = Field(..., example=["character_id"])
    created_by: str = Field(..., example="system")
    updated_by: str = Field(..., example="system")
    created_at: datetime = Field(default=datetime.utcnow())
    updated_at: datetime = Field(default=datetime.utcnow())


class SchemaRetrieveCharactersCollection(ResponseModel):
    name: str
    description_base: str = Field(..., example="This is a character collection")
    characters_id: Optional[list] = Field([], example=["character_id"])
    weapons_id: Optional[list] = Field([], example=["weapon_id"])


class SchemaRetrieveCharactersCollectionStr(ResponseModelStr):
    name: str
    description_base: str = Field(..., example="This is a character collection")
    characters_id: Optional[list] = Field(..., example=["character_id"])
    weapons_id: Optional[list] = Field(..., example=["weapon_id"])


class SchemaListCharactersCollection(BaseModel):
    count: int
    results: list[SchemaRetrieveCharactersCollection]
