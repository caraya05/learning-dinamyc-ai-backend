from pydantic import Field
from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel

from core.database import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")


class SchemaRetrieveCategory(ResponseModel):
    name: str
    description: str
    is_active: bool

    class Config:
        orm_mode = True


class SchemaRetrieveCategoryActive(ResponseModelStr):
    name: str
    description: str

    class Config:
        orm_mode = True


class SchemaRetrieveCategoryStr(ResponseModelStr):
    name: str
    description: str
    is_active: bool

    class Config:
        orm_mode = True


class SchemaListCategoryActive(BaseModel):
    results: list[SchemaRetrieveCategoryActive]
    count: int

    class Config:
        orm_mode = True


class SchemaListCategory(BaseModel):
    results: list[SchemaRetrieveCategoryStr]
    count: int

    class Config:
        orm_mode = True


class SchemaUpdateCategory(BaseModel):
    name: str
    description: str
    is_active: bool


class SchemaUpdateDocumentCategory(SchemaUpdateCategory):
    updated_at: datetime = datetime.utcnow()
    updated_by: str


class SchemaCreateCategory(SchemaUpdateCategory):
    pass
