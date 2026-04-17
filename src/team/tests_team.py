"""
Tests para el módulo Team
"""
import pytest
from unittest.mock import AsyncMock, patch
from bson import ObjectId
from fastapi import HTTPException, status

from team.services import (
    create_team_service,
    get_team_service,
    add_member_to_team_service,
    validate_team_role
)
from team.schemas import (
    SchemaCreateTeam,
    SchemaInviteUserTeam
)


@pytest.mark.asyncio
async def test_create_team_service(sample_team):
    """Test crear un nuevo equipo"""
    with patch('team.services.db') as mock_db:
        mock_db.__getitem__.return_value.insert_one = AsyncMock(
            return_value=AsyncMock(inserted_id=ObjectId(sample_team["_id"]))
        )
        mock_db.__getitem__.return_value.find_one = AsyncMock(
            return_value=sample_team
        )

        team_data = SchemaCreateTeam(
            name="Test Team",
            description="Test team description"
        )

        result = await create_team_service(team_data, sample_team["owner_id"])

        assert result["name"] == "Test Team"
        assert result["owner_id"] == sample_team["owner_id"]


@pytest.mark.asyncio
async def test_get_team_service_not_found():
    """Test obtener equipo que no existe"""
    with patch('team.services.db') as mock_db:
        mock_db.__getitem__.return_value.find_one = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_team_service("invalid_id")

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_validate_team_role_success(sample_team):
    """Test validar rol de usuario en equipo exitosamente"""
    with patch('team.services.db') as mock_db:
        mock_db.__getitem__.return_value.find_one = AsyncMock(
            return_value=sample_team
        )

        result = await validate_team_role(
            sample_team["_id"],
            sample_team["owner_id"],
            ["owner"]
        )

        assert result["_id"] == sample_team["_id"]


@pytest.mark.asyncio
async def test_validate_team_role_insufficient_permissions():
    """Test validar rol sin permisos suficientes"""
    team = {
        "_id": "507f1f77bcf86cd799439011",
        "members": [
            {
                "user_id": "507f1f77bcf86cd799439013",
                "role": "viewer"
            }
        ]
    }

    with patch('team.services.db') as mock_db:
        mock_db.__getitem__.return_value.find_one = AsyncMock(
            return_value=team
        )

        with pytest.raises(HTTPException) as exc_info:
            await validate_team_role(
                team["_id"],
                "507f1f77bcf86cd799439013",
                ["owner", "admin"]
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_add_member_to_team_already_member():
    """Test agregar usuario que ya es miembro"""
    team = {
        "_id": "507f1f77bcf86cd799439011",
        "owner_id": "507f1f77bcf86cd799439012",
        "members": [
            {
                "user_id": "507f1f77bcf86cd799439012",
                "role": "owner"
            },
            {
                "user_id": "507f1f77bcf86cd799439013",
                "role": "creator"
            }
        ]
    }

    with patch('team.services.db') as mock_db:
        def find_one_side_effect(query):
            if "members.user_id" in query:
                return team
            return {"_id": ObjectId("507f1f77bcf86cd799439013")}

        mock_db.__getitem__.return_value.find_one = AsyncMock(
            side_effect=find_one_side_effect
        )

        member_data = SchemaInviteUserTeam(
            user_id="507f1f77bcf86cd799439013",
            role="creator"
        )

        with pytest.raises(HTTPException) as exc_info:
            await add_member_to_team_service(
                team["_id"],
                member_data,
                team["owner_id"]
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

