from datetime import datetime

from pydantic import BaseModel

from pydantic import Field


class CharactersCollection(BaseModel):
    name: str
    description_base: str = Field(..., example="This is a character collection")
    created_by: str = Field(..., example="system")
    updated_by: str = Field(..., example="system")
    created_at: datetime = Field(datetime.utcnow(), example="2021-01-01T00:00:00")
    updated_at: datetime = Field(datetime.utcnow(), example="2021-01-01T00:00:00")
    characters_id: list = Field(..., example=["character_id"])
    weapons_id: list = Field(..., example=["weapon_id"])
