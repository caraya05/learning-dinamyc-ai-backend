
from bson import ObjectId
from pydantic import BaseModel
from pydantic import Field

from core import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")



class SchemaStateGameCreate(BaseModel):
    game_id: str = Field(None, example="game_id")


class SchemaStateGameRetrieve(ResponseModelStr):
    game_id: str = Field(None, example="game_id")
    order: int = Field(None, example=1)


class SchemaStateGameList(BaseModel):
    results: list[SchemaStateGameRetrieve]
    count: int = Field(None, example=1)



