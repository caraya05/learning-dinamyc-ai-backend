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
    characters_id: list = Field([], example=["character_id"])
    weapons_id: list = Field([], example=["weapon_id"])
    created_by: str = Field(..., example="system")
    updated_by: str = Field(..., example="system")
    created_at: datetime = Field(default=datetime.utcnow())
    updated_at: datetime = Field(default=datetime.utcnow())


class SchemaRetrieveCharactersCollection(ResponseModel):
    name: Optional[str] = Field(None, example="collection_name")
    characters_id: Optional[list] = Field([], example=["character_id"])
    weapons_id: Optional[list] = Field([], example=["weapon_id"])
    image: Optional[str] = Field(None, example="image_url")


class SchemaRetrieveCharactersCollectionStr(ResponseModelStr):
    name: str = Field(None, example="collection_name")
    characters_id: Optional[list] = Field(..., example=["character_id"])
    weapons_id: Optional[list] = Field(..., example=["weapon_id"])
    image: str = Field(None, example="image_url")


class SchemaListCharactersCollection(BaseModel):
    count: int
    results: list[SchemaRetrieveCharactersCollectionStr]
