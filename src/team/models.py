import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TeamMember(BaseModel):
    """Representa un miembro del equipo"""
    user_id: str = Field(..., example="507f1f77bcf86cd799439011")
    role: str = Field(..., example="owner")  # owner, creator, viewer, admin
    joined_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class Team(BaseModel):
    """Modelo de equipo para planes colaborativos"""
    name: str = Field(..., min_length=1, max_length=100, example="My Game Studio")
    description: Optional[str] = Field(default=None, example="A team for game creation")
    owner_id: str = Field(..., example="507f1f77bcf86cd799439011")
    members: List[TeamMember] = Field(default_factory=list)
    is_active: bool = Field(default=True, example=True)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    created_by: str = Field(default="system", example="system")
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_by: str = Field(default="system", example="system")
    selected_visual_style_id: Optional[str] = Field(default=None, example="507f1f77bcf86cd799439012")


