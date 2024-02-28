from pydantic import BaseModel


class SchemaCreateCustomize(BaseModel):
    reference_ui: str
    genre: str
    type: str
    description: str
    type_customize: str
    type_character: str


class SchemaRetrieveCustomize(BaseModel):
    id: str
    reference_ui: str

    # genre: str
    # type:  str
    # description: str
    # type_customize: str
    # type_character: str

    class Config:
        orm_mode = True


class SchemaPartialUpdateCustomize(BaseModel):
    reference_ui: str
    genre: str
    type: str
    description: str
    type_customize: str
    type_character: str


class SchemaListCustomize(BaseModel):
    results: list[SchemaRetrieveCustomize]
    count: int


class SchemaRetrieveMiniCustomize(BaseModel):
    id: str
    reference_ui: str
    description: str

    class Config:
        orm_mode = True


class SchemaListMiniCustomize(BaseModel):
    results: list[SchemaRetrieveMiniCustomize]
    count: int

    class Config:
        orm_mode = True
