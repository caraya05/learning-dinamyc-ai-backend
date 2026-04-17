"""
Configuración de tests para el módulo Team
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_db():
    """Mock de la base de datos"""
    return AsyncMock()


@pytest.fixture
def sample_team():
    """Equipo de ejemplo para tests"""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "name": "Test Team",
        "description": "Test team description",
        "owner_id": "507f1f77bcf86cd799439012",
        "members": [
            {
                "user_id": "507f1f77bcf86cd799439012",
                "role": "owner"
            }
        ],
        "is_active": True,
        "created_at": "2026-03-16T10:00:00",
        "created_by": "system",
        "updated_at": "2026-03-16T10:00:00",
        "updated_by": "system"
    }


@pytest.fixture
def sample_user():
    """Usuario de ejemplo para tests"""
    return {
        "_id": "507f1f77bcf86cd799439012",
        "username": "testuser",
        "email": "test@example.com",
        "plan_type": "individual",
        "team_id": None,
        "team_role": None,
        "is_team_owner": False
    }

