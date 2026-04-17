"""
Utilidades para el módulo de Team
"""
from typing import List, Dict, Optional
from bson import ObjectId


def is_valid_team_role(role: str) -> bool:
    """Valida si el rol es válido"""
    valid_roles = ["owner", "creator", "viewer", "admin"]
    return role in valid_roles


def get_role_permissions(role: str) -> List[str]:
    """Retorna los permisos para un rol específico"""
    permissions_map = {
        "owner": ["invite", "remove", "edit_team", "edit_members", "create", "view"],
        "admin": ["invite", "remove", "edit_members", "create", "view"],
        "creator": ["create", "view"],
        "viewer": ["view"]
    }
    return permissions_map.get(role, [])


def has_permission(role: str, permission: str) -> bool:
    """Verifica si un rol tiene un permiso específico"""
    permissions = get_role_permissions(role)
    return permission in permissions


def serialize_team(team_db: Dict) -> Dict:
    """Serializa un documento de equipo para respuesta JSON"""
    if not team_db:
        return None
    
    team_db["_id"] = str(team_db["_id"])
    if "members" in team_db:
        for member in team_db["members"]:
            if isinstance(member.get("user_id"), ObjectId):
                member["user_id"] = str(member["user_id"])
    
    return team_db


def serialize_teams(teams: List[Dict]) -> List[Dict]:
    """Serializa una lista de documentos de equipo"""
    return [serialize_team(team) for team in teams]

