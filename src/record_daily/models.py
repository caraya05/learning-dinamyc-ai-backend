from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class DailyRecord(BaseModel):
    user_id: str = Field(..., example="User")
    balance: int = Field(..., example=0)
    expenses: int = Field(..., example=0)
    games_created: int = Field(..., example=0)
    sets_with_errors: int = Field(..., example=0)
    attempts_to_create_without_balance: int = Field(..., example=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
