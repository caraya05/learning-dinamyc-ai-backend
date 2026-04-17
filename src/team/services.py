from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from core.database import db
from team.models import Team, TeamMember
from team.schemas import SchemaCreateTeam, SchemaUpdateTeam, SchemaInviteUserTeam
from utils import serialize_objectid


async def _enrich_members_with_user_data(team_db: dict) -> dict:
    """
    Enriquece los miembros del equipo con información del usuario (username, email).
    Hace lookups en la colección de usuarios.
    """
    if not team_db or "members" not in team_db:
        return team_db
    
    for member in team_db.get("members", []):
        user_id = member.get("user_id")
        if user_id:
            try:
                # Buscar el usuario
                user = await db["user"].find_one({"_id": ObjectId(user_id)})
                if user:
                    member["username"] = user.get("username", "")
                    member["email"] = user.get("email", "")
            except Exception:
                # Si falla, dejar los campos vacíos
                member["username"] = ""
                member["email"] = ""
    
    return team_db


def _convert_team_ids(team_db: dict) -> dict:
    """
    Convierte recursivamente todos los ObjectId y datetime a string en el equipo.
    Garantiza que NO hay ObjectId en la respuesta.
    """
    if not team_db:
        return team_db
    
    # Convertir usando serialize_objectid que maneja recursión completa
    converted = serialize_objectid(team_db)
    
    # Verificar que realmente se convirtió (seguridad adicional)
    if converted and isinstance(converted, dict):
        return converted
    
    return team_db


async def _prepare_team_response(team_db: dict) -> dict:
    """
    Prepara el equipo para respuesta: enriquece miembros y convierte ObjectId.
    Debe usarse SIEMPRE antes de retornar un equipo al cliente.
    """
    if not team_db:
        return team_db
    
    # Primero enriquecer con datos de usuario
    team_db = await _enrich_members_with_user_data(team_db)
    
    # Luego convertir ObjectId a string
    team_db = _convert_team_ids(team_db)
    
    return team_db


# Roles de equipo con sus permisos
TEAM_ROLES = {
    "owner": ["invite", "remove", "edit_team", "edit_members", "create", "view"],
    "admin": ["invite", "remove", "edit_members", "create", "view"],
    "creator": ["create", "view"],
    "viewer": ["view"]
}


async def validate_team_role(team_id: str, user_id: str, required_roles: list):
    """Valida que el usuario tenga uno de los roles requeridos en el equipo"""
    try:
        team_db = await db["team"].find_one({"_id": ObjectId(team_id)})
        if not team_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        # Verificar si el usuario es miembro del equipo
        member = None
        for m in team_db.get("members", []):
            if str(m.get("user_id")) == str(user_id):
                member = m
                break
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of this team"
            )
        
        # Verificar si el rol actual está en los roles requeridos
        if member.get("role") not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}"
            )
        
        # Retornar sin convertir para uso interno
        return team_db
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error validating team role: {str(e)}"
        )


async def create_team_service(team_data: SchemaCreateTeam, owner_id: str):
    """Crea un nuevo equipo"""
    try:
        # Crear el modelo del equipo
        new_team = Team(
            name=team_data.name,
            description=team_data.description,
            owner_id=owner_id,
            members=[
                TeamMember(
                    user_id=owner_id,
                    role="owner"
                )
            ],
            created_by=owner_id,
            updated_by=owner_id
        )
        
        # Insertar en la base de datos
        result = await db["team"].insert_one(new_team.dict())
        team_created = await db["team"].find_one({"_id": result.inserted_id})
        
        # Preparar respuesta (enriquecer + convertir)
        return await _prepare_team_response(team_created)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating team: {str(e)}"
        )


async def get_team_service(team_id: str):
    """Obtiene un equipo por ID"""
    try:
        team_db = await db["team"].find_one({"_id": ObjectId(team_id)})
        if not team_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        return await _prepare_team_response(team_db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error getting team: {str(e)}"
        )


async def update_team_service(team_id: str, team_data: SchemaUpdateTeam, user_id: str):
    """Actualiza un equipo (solo owner)"""
    try:
        # Validar que el usuario sea owner
        await validate_team_role(team_id, user_id, ["owner"])
        
        update_data = team_data.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        update_data["updated_by"] = user_id
        
        await db["team"].update_one(
            {"_id": ObjectId(team_id)},
            {"$set": update_data}
        )
        
        team_updated = await db["team"].find_one({"_id": ObjectId(team_id)})
        return await _prepare_team_response(team_updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating team: {str(e)}"
        )


async def add_member_to_team_service(
    team_id: str, 
    member_data: SchemaInviteUserTeam, 
    user_id: str
):
    """Agrega un miembro al equipo por email (solo owner/admin). Crea el usuario si no existe."""
    try:
        # Validar que el usuario sea owner o admin
        team_db = await validate_team_role(team_id, user_id, ["creator", "viewer", "admin", "owner"])
        
        # Validar que el email sea válido
        if not member_data.email or "@" not in member_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email inválido"
            )
        
        # Verificar si el usuario ya existe
        user_to_add = await db["user"].find_one({"email": member_data.email})
        
        if not user_to_add:
            # Crear el usuario si no existe
            from user.services import create_user_service_basic
            
            # Crear usuario básico con email, username, team_id y role
            new_user = await create_user_service_basic(
                email=member_data.email,
                username=member_data.email.split("@")[0],  # Username del email
                created_by=user_id,
                team_id=team_id,  # Pasar el team_id
                role=member_data.role  # Pasar el role
            )
            user_to_add = new_user
            member_user_id = str(new_user.get("_id"))
        else:
            member_user_id = str(user_to_add.get("_id"))
        
        # Verificar que el usuario no sea ya miembro del team
        for member in team_db.get("members", []):
            if str(member.get("user_id")) == member_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El usuario ya es miembro de este equipo"
                )
        
        # Crear el nuevo miembro
        new_member = TeamMember(
            user_id=member_user_id,
            role=member_data.role
        )
        
        # Agregar el miembro al equipo
        await db["team"].update_one(
            {"_id": ObjectId(team_id)},
            {
                "$push": {"members": new_member.dict()},
                "$set": {
                    "updated_at": datetime.utcnow(),
                    "updated_by": user_id
                }
            }
        )
        
        # Actualizar el usuario para que tenga los datos del equipo
        await db["user"].update_one(
            {"_id": ObjectId(member_user_id)},
            {
                "$set": {
                    "team_id": team_id,
                    "team_role": member_data.role,
                    "is_team_owner": member_data.role == "owner",
                    "plan_type": "team",
                    "is_preview": True,
                    "updated_at": datetime.utcnow(),
                    "updated_by": user_id
                }
            }
        )
        
        # Obtener el equipo actualizado
        team_updated = await db["team"].find_one({"_id": ObjectId(team_id)})
        
        return await _prepare_team_response(team_updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error adding member to team: {str(e)}"
        )


async def remove_member_from_team_service(
    team_id: str,
    member_id: str,
    user_id: str
):
    """Remueve un miembro del equipo (solo owner/admin)"""
    try:
        # Validar que el usuario sea owner o admin
        team_db = await validate_team_role(team_id, user_id, ["owner", "admin"])
        
        # Verificar que el miembro existe
        member_exists = False
        for member in team_db.get("members", []):
            if str(member.get("user_id")) == str(member_id):
                member_exists = True
                break
        
        if not member_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in team"
            )
        
        # Verificar que no sea el último owner
        owner_count = sum(1 for m in team_db.get("members", []) if m.get("role") == "owner")
        if owner_count == 1 and str(member_id) == str(team_db.get("owner_id")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner from the team"
            )
        
        # Remover el miembro
        await db["team"].update_one(
            {"_id": ObjectId(team_id)},
            {
                "$pull": {"members": {"user_id": member_id}},
                "$set": {
                    "updated_at": datetime.utcnow(),
                    "updated_by": user_id
                }
            }
        )
        
        # Actualizar el usuario para remover datos del equipo
        await db["user"].update_one(
            {"_id": ObjectId(member_id)},
            {
                "$set": {
                    "team_id": None,
                    "team_role": None,
                    "is_team_owner": False,
                    "plan_type": "individual",
                    "is_preview": False,
                    "updated_at": datetime.utcnow(),
                    "updated_by": user_id
                }
            }
        )
        
        team_updated = await db["team"].find_one({"_id": ObjectId(team_id)})
        
        return await _prepare_team_response(team_updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error removing member from team: {str(e)}"
        )


async def update_member_role_service(
    team_id: str,
    member_id: str,
    new_role: str,
    user_id: str
):
    """Actualiza el rol de un miembro del equipo (solo owner)"""
    try:
        # Validar que el nuevo rol sea válido
        if new_role not in TEAM_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Valid roles: {list(TEAM_ROLES.keys())}"
            )
        
        # Validar que el usuario sea owner
        team_db = await validate_team_role(team_id, user_id, ["owner"])
        
        # Verificar que el miembro existe
        member_exists = False
        for member in team_db.get("members", []):
            if str(member.get("user_id")) == str(member_id):
                member_exists = True
                break
        
        if not member_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in team"
            )
        
        # Actualizar el rol del miembro
        await db["team"].update_one(
            {"_id": ObjectId(team_id), "members.user_id": member_id},
            {
                "$set": {
                    "members.$.role": new_role,
                    "updated_at": datetime.utcnow(),
                    "updated_by": user_id
                }
            }
        )
        
        # Actualizar el usuario
        await db["user"].update_one(
            {"_id": ObjectId(member_id)},
            {
                "$set": {
                    "team_role": new_role,
                    "is_team_owner": new_role == "owner",
                    "updated_at": datetime.utcnow(),
                    "updated_by": user_id
                }
            }
        )
        
        team_updated = await db["team"].find_one({"_id": ObjectId(team_id)})
        
        return await _prepare_team_response(team_updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating member role: {str(e)}"
        )


async def list_teams_by_user_service(user_id: str):
    """Lista todos los equipos de un usuario"""
    try:
        teams = await db["team"].find(
            {"members.user_id": user_id}
        ).to_list(None)
        
        return [await _prepare_team_response(team) for team in teams]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error listing teams: {str(e)}"
        )


async def delete_team_service(team_id: str, user_id: str):
    """Elimina un equipo (solo owner)"""
    try:
        # Validar que el usuario sea owner
        await validate_team_role(team_id, user_id, ["owner"])
        
        # Remover el equipo
        result = await db["team"].delete_one({"_id": ObjectId(team_id)})
        
        # Actualizar todos los usuarios del equipo
        await db["user"].update_many(
            {"team_id": team_id},
            {
                "$set": {
                    "team_id": None,
                    "team_role": None,
                    "is_team_owner": False,
                    "plan_type": "individual",
                    "is_preview": False,
                    "updated_at": datetime.utcnow(),
                    "updated_by": user_id
                }
            }
        )
        
        return result.deleted_count > 0
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting team: {str(e)}"
        )



















