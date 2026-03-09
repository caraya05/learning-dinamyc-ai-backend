"""
Configuración y fixtures de pytest para tests de analytics.

Este archivo contiene fixtures compartidas y configuración global para los tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from analytics.schemas import AnalyticCreate, UserResponseSchema, ProgressEnum


# ============================================================================
# CONFIGURACIÓN DE ASYNCIO
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Crea un event loop para tests async."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# FIXTURES COMPARTIDAS
# ============================================================================

@pytest.fixture
def sample_analytic_create():
    """Analítica de ejemplo para crear."""
    return AnalyticCreate(
        game_id="test_game_123",
        session_id="test_session_456",
        start_time=datetime.now(timezone.utc),
        progress=ProgressEnum.LEVEL_1,
        completed=False,
        duration=0,
        score=0,
    )


@pytest.fixture
def sample_analytic_db():
    """Analítica de ejemplo desde base de datos."""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "game_id": "test_game_123",
        "session_id": "test_session_456",
        "start_time": datetime.now(timezone.utc),
        "end_time": None,
        "progress": 1,
        "completed": False,
        "duration": 0,
        "score": 0,
        "user_id": "test_user_123",
        "created_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_user_response():
    """Respuesta de usuario de ejemplo."""
    return UserResponseSchema(
        question_id="q1",
        question="¿Cuál es la capital?",
        answer="Bogotá",
        timestamp=datetime.now(timezone.utc),
        is_correct=True,
    )


@pytest.fixture
def mock_db_connection():
    """Mock de conexión a MongoDB."""
    with patch("analytics.services.db") as mock_db:
        # Configurar estructura básica del mock
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        # Configurar métodos de cursor
        mock_cursor = MagicMock()
        mock_collection.find.return_value.skip.return_value.limit.return_value.sort.return_value = mock_cursor

        yield mock_db


@pytest.fixture
def mock_auth_user():
    """Usuario autenticado de ejemplo."""
    return {
        "_id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "user",
    }


# ============================================================================
# FIXTURES PARA TESTS DE ENDPOINTS (FastAPI)
# ============================================================================

@pytest.fixture
def mock_dependencies():
    """Mock de dependencias de FastAPI."""
    return {
        "auth": AsyncMock(return_value={"_id": "test_user_123"}),
        "auth_schema": AsyncMock(return_value={"credentials": "Bearer token"}),
    }


# ============================================================================
# MARCADORES PERSONALIZADOS
# ============================================================================

def pytest_configure(config):
    """Registra marcadores personalizados."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
    config.addinivalue_line(
        "markers", "db: mark test that requires database"
    )


# ============================================================================
# HOOKS Y UTILIDADES
# ============================================================================

@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset de mocks entre tests."""
    yield
    # Cleanup después de cada test


@pytest.fixture
def sample_responses_list():
    """Lista de respuestas de ejemplo."""
    return [
        UserResponseSchema(
            question_id=f"q{i}",
            question=f"Pregunta {i}?",
            answer=f"Respuesta {i}",
            timestamp=datetime.now(timezone.utc),
            is_correct=i % 2 == 0,
        )
        for i in range(1, 6)
    ]


# ============================================================================
# FIXTURES PARA DATOS DE PRUEBA
# ============================================================================

@pytest.fixture
def analytic_data_samples():
    """Múltiples muestras de datos de analíticas."""
    return [
        {
            "game_id": f"game_{i}",
            "session_id": f"sess_{i}",
            "score": i * 100,
            "user_id": "user_123",
        }
        for i in range(1, 6)
    ]


@pytest.fixture
def invalid_data_samples():
    """Muestras de datos inválidos para testing de validaciones."""
    return [
        {"progress": 5},  # Fuera de rango
        {"progress": 0},  # Fuera de rango
        {"score": -100},  # Negativo
        {"duration": -50},  # Negativo
        {"views": -10},   # Negativo
        {"likes": -5},    # Negativo
        {"plays": -1},    # Negativo
    ]



