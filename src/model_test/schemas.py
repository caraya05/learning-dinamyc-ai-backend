from pydantic import BaseModel, Field

class ItemBase(BaseModel):
    name: str = Field(..., example="Test Item", description="Nombre del ítem")
    description: str = Field(None, example="Descripción opcional")

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int = Field(..., example=1)

    class Config:
        orm_mode = True

