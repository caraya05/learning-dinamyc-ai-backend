from pydantic import BaseModel
from pydantic import Field
from typing import Optional


class SchemaRetrieveConfiguration(BaseModel):
    stars_by_game: Optional[int] = Field(..., example=0, description="Stars by game")

    class Config:
        orm_mode = True
