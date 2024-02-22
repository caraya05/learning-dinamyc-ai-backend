from pydantic import BaseModel


class SchemaCreateCustomize(BaseModel):
    name: str
    genre: str
    type: str
    description: str
    type_character: str


class SchemaRetrieveCustomize(BaseModel):
    id: str
    name: str
    genre: str
    type: str
    description: str
    type_character: str


class SchemaPartialUpdateCustomize(BaseModel):
    name: str
    genre: str
    type: str
    description: str
    type_character: str


class SchemaListCustomize(BaseModel):
    results: list[SchemaRetrieveCustomize]
    count: int
