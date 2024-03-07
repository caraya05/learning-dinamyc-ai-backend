from pydantic import BaseModel


class SchemaRetrieveCategory(BaseModel):
    id: str
    name: str
    description: str

    class Config:
        orm_mode = True


class SchemaListCategory(BaseModel):
    results: list[SchemaRetrieveCategory]
    count: int

    class Config:
        orm_mode = True
