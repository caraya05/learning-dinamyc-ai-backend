from typing import Optional, List

from bson import ObjectId
from pydantic import BaseModel, Field


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}

class SchemaTeamMember(BaseModel):
    """Esquema de miembro de equipo"""
    user_id: str = Field(..., example="507f1f77bcf86cd799439011")
    role: str = Field(..., example="owner")
    joined_at: Optional[str] = Field(None, example="2024-01-01T00:00:00")

    class Config:
        populate_by_name = True


class SchemaCreateTeam(BaseModel):
    """Esquema para crear un nuevo equipo"""
    name: str = Field(..., min_length=1, max_length=100, example="My Game Studio")
    description: Optional[str] = Field(None, example="A team for game creation")


class SchemaUpdateTeam(BaseModel):
    """Esquema para actualizar un equipo"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, example="Updated Studio")
    description: Optional[str] = Field(None, example="Updated description")
    is_active: Optional[bool] = Field(None, example=True)


class SchemaInviteUserTeam(BaseModel):
    """Esquema para invitar un usuario al equipo por email"""
    email: str = Field(..., example="user@example.com", description="Email del usuario a invitar")
    role: str = Field(default="viewer", example="viewer", description="Rol: owner, creator, viewer, admin")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "role": "creator"
            }
        }


class SchemaUpdateTeamMemberRole(BaseModel):
    """Esquema para actualizar el rol de un miembro"""
    role: str = Field(..., example="creator")


class SchemaRetrieveTeamMember(BaseModel):
    """Esquema para recuperar información de miembro del equipo"""
    _id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(..., example="507f1f77bcf86cd799439011")
    username: Optional[str] = Field(None, example="john_doe")
    email: Optional[str] = Field(None, example="john@example.com")
    role: str = Field(..., example="owner")
    joined_at: Optional[str] = Field(None, example="2024-01-01T00:00:00")

    class Config:
        populate_by_name = True


class SchemaRetrieveTeam(ResponseModelStr):
    """Esquema para recuperar información del equipo"""
    name: str = Field(..., example="My Game Studio")
    description: Optional[str] = Field(..., example="A team for game creation")
    owner_id: str = Field(..., example="507f1f77bcf86cd799439011")
    members: List[SchemaRetrieveTeamMember] = Field(default_factory=list)
    is_active: bool = Field(..., example=True)
    created_at: Optional[str] = Field(None, example="2024-01-01T00:00:00")
    updated_at: Optional[str] = Field(None, example="2024-01-01T00:00:00")

    class Config:
        populate_by_name = True
        orm_mode = True



class SchemaListTeams(BaseModel):
    """Esquema para listar equipos"""
    results: List[SchemaRetrieveTeam] = Field(default_factory=list)
    count: int = Field(..., example=3)






