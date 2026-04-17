from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from team.schemas import (
    SchemaCreateTeam,
    SchemaUpdateTeam,
    SchemaInviteUserTeam,
    SchemaUpdateTeamMemberRole,
    SchemaRetrieveTeam,
    SchemaListTeams
)
from team.services import (
    create_team_service,
    get_team_service,
    update_team_service,
    add_member_to_team_service,
    remove_member_from_team_service,
    update_member_role_service,
    list_teams_by_user_service,
    delete_team_service
)

router = APIRouter(prefix="/team", tags=["team"])


@router.post("", response_model=SchemaRetrieveTeam, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: SchemaCreateTeam,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    """
    Crear un nuevo equipo. El usuario actual se convierte en owner.
    """
    team_created = await create_team_service(team_data, str(user.get("_id")))
    return team_created


@router.get("/{team_id}", response_model=SchemaRetrieveTeam)
async def get_team(
    team_id: str,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    """
    Obtener información de un equipo por ID.
    """
    team = await get_team_service(team_id)
    return team


@router.patch("/{team_id}", response_model=SchemaRetrieveTeam)
async def update_team(
    team_id: str,
    team_data: SchemaUpdateTeam,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    """
    Actualizar información del equipo. Solo el owner puede hacerlo.
    """
    team_updated = await update_team_service(team_id, team_data, str(user.get("_id")))
    return team_updated


@router.post("/{team_id}/members", response_model=SchemaRetrieveTeam, status_code=status.HTTP_201_CREATED)
async def add_member_to_team(
    team_id: str,
    member_data: SchemaInviteUserTeam,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    """
    Agregar un miembro al equipo. Solo owner o admin pueden hacerlo.
    """
    team_updated = await add_member_to_team_service(
        team_id,
        member_data,
        str(user.get("_id"))
    )
    return team_updated


@router.delete("/{team_id}/members/{member_id}", response_model=SchemaRetrieveTeam)
async def remove_member_from_team(
    team_id: str,
    member_id: str,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    """
    Remover un miembro del equipo. Solo owner o admin pueden hacerlo.
    """
    team_updated = await remove_member_from_team_service(
        team_id,
        member_id,
        str(user.get("_id"))
    )
    return team_updated


@router.patch("/{team_id}/members/{member_id}/role")
async def update_member_role(
    team_id: str,
    member_id: str,
    role_data: SchemaUpdateTeamMemberRole,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    """
    Actualizar el rol de un miembro. Solo el owner puede hacerlo.
    """
    team_updated = await update_member_role_service(
        team_id,
        member_id,
        role_data.role,
        str(user.get("_id"))
    )
    return team_updated


@router.get("", response_model=SchemaListTeams)
async def list_teams(
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    """
    Listar todos los equipos del usuario actual.
    """
    teams = await list_teams_by_user_service(str(user.get("_id")))
    return SchemaListTeams(results=teams, count=len(teams))


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    """
    Eliminar un equipo. Solo el owner puede hacerlo.
    """
    await delete_team_service(team_id, str(user.get("_id")))
    return None




