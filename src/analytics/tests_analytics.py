"""
Tests unitarios para el módulo de analytics.

Pruebas usando pytest-asyncio para funciones async.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from analytics.schemas import (
    AnalyticCreate,
    AnalyticDB,
    ProgressEnum,
    UserResponseSchema,
)
from analytics.exceptions import (
    AnalyticNotFoundError,
    InvalidProgressError,
    InvalidScoreError,
    DatabaseError,
)
from analytics.services import (
    create_analytic_service,
    get_analytics_by_user_service,
    query_analytics_service,
)
from analytics.services_responses import update_session_complete


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_analytic_data():
    """Datos de ejemplo para una analítica."""
    return {
        "game_id": "game_123",
        "session_id": "sess_456",
        "start_time": datetime.now(timezone.utc),
        "progress": 1,
        "completed": False,
        "duration": 0,
        "score": 0,
        "user_id": "user_abc123",
    }


@pytest.fixture
def sample_user_response():
    """Datos de ejemplo para una respuesta de usuario."""
    return {
        "question_id": "q1",
        "question": "¿Cuál es la capital de Colombia?",
        "answer": "Bogotá",
        "timestamp": datetime.now(timezone.utc),
        "is_correct": True,
    }


@pytest.fixture
def mock_db():
    """Mock de la base de datos."""
    with patch("analytics.services.db") as mock:
        yield mock


# ============================================================================
# TESTS: SCHEMAS (Validación Pydantic)
# ============================================================================

class TestAnalyticCreateSchema:
    """Tests para validación del schema AnalyticCreate."""

    def test_crear_con_todos_campos(self):
        """Debe crear un AnalyticCreate con todos los campos."""
        data = {
            "game_id": "game_123",
            "session_id": "sess_456",
            "start_time": "2026-02-25T14:12:00Z",
            "progress": 1,
            "completed": False,
            "duration": 0,
            "score": 100,
        }
        analytic = AnalyticCreate(**data)
        assert analytic.game_id == "game_123"
        assert analytic.progress == ProgressEnum.LEVEL_1

    def test_crear_con_campos_minimos(self):
        """Debe crear un AnalyticCreate con campos mínimos."""
        data = {}
        analytic = AnalyticCreate(**data)
        assert analytic.game_id is None
        assert analytic.progress is None

    def test_crear_con_algunos_campos(self):
        """Debe crear un AnalyticCreate con algunos campos."""
        data = {"game_id": "game_123", "score": 50}
        analytic = AnalyticCreate(**data)
        assert analytic.game_id == "game_123"
        assert analytic.score == 50
        assert analytic.session_id is None

    def test_validar_progress_valido(self):
        """Debe validar que progress esté en rango 1-3."""
        data = {"progress": 2}
        analytic = AnalyticCreate(**data)
        assert analytic.progress == ProgressEnum.LEVEL_2

    def test_rechazar_progress_invalido(self):
        """Debe rechazar progress fuera de rango."""
        data = {"progress": 5}
        with pytest.raises(ValueError):
            AnalyticCreate(**data)

    def test_rechazar_score_negativo(self):
        """Debe rechazar score negativo."""
        data = {"score": -10}
        with pytest.raises(ValueError):
            AnalyticCreate(**data)

    def test_rechazar_duration_negativa(self):
        """Debe rechazar duration negativa."""
        data = {"duration": -100}
        with pytest.raises(ValueError):
            AnalyticCreate(**data)


class TestUserResponseSchema:
    """Tests para validación del schema UserResponseSchema."""

    def test_crear_respuesta_completa(self):
        """Debe crear una respuesta completa."""
        data = {
            "question_id": "q1",
            "question": "¿Pregunta?",
            "answer": "Respuesta",
            "timestamp": datetime.now(timezone.utc),
            "is_correct": True,
        }
        response = UserResponseSchema(**data)
        assert response.question_id == "q1"
        assert response.is_correct is True

    def test_crear_respuesta_con_campos_opcionales(self):
        """Debe crear respuesta con campos opcionales."""
        data = {
            "question_id": "q1",
            "question": None,
            "answer": None,
            "timestamp": None,
            "is_correct": None,
        }
        response = UserResponseSchema(**data)
        assert response.question_id == "q1"
        assert response.question is None

    def test_crear_respuesta_vacia(self):
        """Debe crear respuesta vacía."""
        response = UserResponseSchema()
        assert response.question_id is None
        assert response.is_correct is None


class TestAnalyticDBSchema:
    """Tests para validación del schema AnalyticDB (respuesta)."""

    def test_alias_id_underscore(self):
        """Debe permitir usar 'id' o '_id'."""
        data = {
            "_id": "507f1f77bcf86cd799439011",
            "game_id": "game_123",
        }
        analytic = AnalyticDB(**data)
        assert analytic.id == "507f1f77bcf86cd799439011"


# ============================================================================
# TESTS: EXCEPCIONES
# ============================================================================

class TestExceptions:
    """Tests para excepciones personalizadas."""

    def test_analytic_not_found_error(self):
        """Debe lanzar AnalyticNotFoundError con mensaje."""
        with pytest.raises(AnalyticNotFoundError) as exc_info:
            raise AnalyticNotFoundError("sess_123", "session_id")
        assert "sess_123" in str(exc_info.value)
        assert "session_id" in str(exc_info.value)

    def test_invalid_progress_error(self):
        """Debe lanzar InvalidProgressError."""
        with pytest.raises(InvalidProgressError) as exc_info:
            raise InvalidProgressError(5)
        assert "5" in str(exc_info.value)
        assert "1 y 3" in str(exc_info.value)

    def test_invalid_score_error(self):
        """Debe lanzar InvalidScoreError."""
        with pytest.raises(InvalidScoreError) as exc_info:
            raise InvalidScoreError(-10)
        assert "-10" in str(exc_info.value)

    def test_unauthorized_access_error(self):
        """Debe lanzar UnauthorizedAnalyticAccessError."""
        with pytest.raises(UnauthorizedAnalyticAccessError) as exc_info:
            raise UnauthorizedAnalyticAccessError("user_1", "analytic_123")
        assert "user_1" in str(exc_info.value)

    def test_database_error(self):
        """Debe lanzar DatabaseError."""
        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError("insert_one", "Connection failed")
        assert "insert_one" in str(exc_info.value)


# ============================================================================
# TESTS: SERVICES - CREATE
# ============================================================================

class TestCreateAnalyticService:
    """Tests para create_analytic_service."""

    @pytest.mark.asyncio
    async def test_crear_analtica_exitosa(self, mock_db, sample_analytic_data):
        """Debe crear una analítica exitosamente."""
        # Setup mock
        mock_db.__getitem__.return_value.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id="123")
        )
        mock_db.__getitem__.return_value.find_one = AsyncMock(
            return_value={
                "_id": "123",
                **sample_analytic_data,
            }
        )

        # Ejecutar
        result = await create_analytic_service(sample_analytic_data)

        # Verificar
        assert result["_id"] == "123"
        assert result["user_id"] == "user_abc123"
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_validar_progress_en_creacion(self, mock_db):
        """Debe validar progress al crear."""
        data = {"progress": 5}  # Inválido

        with pytest.raises(InvalidProgressError):
            await create_analytic_service(data)

    @pytest.mark.asyncio
    async def test_agregar_timestamp_creacion(self, mock_db, sample_analytic_data):
        """Debe agregar timestamp de creación."""
        mock_db.__getitem__.return_value.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id="123")
        )
        mock_db.__getitem__.return_value.find_one = AsyncMock(
            return_value={"_id": "123", **sample_analytic_data}
        )

        await create_analytic_service(sample_analytic_data)

        # Verificar que created_at fue agregado
        call_args = mock_db.__getitem__.return_value.insert_one.call_args
        inserted_data = call_args[0][0]
        assert "created_at" in inserted_data


# ============================================================================
# TESTS: SERVICES - QUERY
# ============================================================================

class TestGetAnalyticsByUserService:
    """Tests para get_analytics_by_user_service."""

    @pytest.mark.asyncio
    async def test_obtener_analticas_por_usuario(self, mock_db):
        """Debe obtener analíticas de un usuario."""
        # Setup mock
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__.return_value = [
            {"_id": "1", "game_id": "game_1", "user_id": "user_123"},
            {"_id": "2", "game_id": "game_2", "user_id": "user_123"},
        ]

        mock_db.__getitem__.return_value.find.return_value.skip.return_value.limit.return_value.sort.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=2)

        # Ejecutar
        results, count = await get_analytics_by_user_service("user_123")

        # Verificar
        assert len(results) == 2
        assert count == 2
        assert results[0]["_id"] == "1"
        assert results[1]["_id"] == "2"

    @pytest.mark.asyncio
    async def test_obtener_analticas_vacio(self, mock_db):
        """Debe retornar lista vacía si no hay registros."""
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__.return_value = []

        mock_db.__getitem__.return_value.find.return_value.skip.return_value.limit.return_value.sort.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=0)

        results, count = await get_analytics_by_user_service("user_no_existe")

        assert len(results) == 0
        assert count == 0

    @pytest.mark.asyncio
    async def test_paginacion_skip_limit(self, mock_db):
        """Debe aplicar skip y limit correctamente."""
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__.return_value = []

        mock_db.__getitem__.return_value.find.return_value.skip.return_value.limit.return_value.sort.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=100)

        await get_analytics_by_user_service("user_123", skip=10, limit=20)

        # Verificar que skip(10) y limit(20) fueron llamados
        mock_db.__getitem__.return_value.find.return_value.skip.assert_called_with(10)
        mock_db.__getitem__.return_value.find.return_value.skip.return_value.limit.assert_called_with(20)


class TestQueryAnalyticsService:
    """Tests para query_analytics_service."""

    @pytest.mark.asyncio
    async def test_consulta_con_filtro_usuario(self, mock_db):
        """Debe filtrar por usuario."""
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__.return_value = []

        mock_db.__getitem__.return_value.find.return_value.skip.return_value.limit.return_value.sort.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=0)

        await query_analytics_service(user_id="user_123")

        # Verificar que find fue llamado con user_id
        call_args = mock_db.__getitem__.return_value.find.call_args
        query = call_args[0][0]
        assert "user_id" in query

    @pytest.mark.asyncio
    async def test_consulta_con_filtro_progress(self, mock_db):
        """Debe filtrar por progress."""
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__.return_value = []

        mock_db.__getitem__.return_value.find.return_value.skip.return_value.limit.return_value.sort.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=0)

        await query_analytics_service(progress=2)

        call_args = mock_db.__getitem__.return_value.find.call_args
        query = call_args[0][0]
        assert query.get("progress") == 2

    @pytest.mark.asyncio
    async def test_consulta_progress_invalido(self, mock_db):
        """Debe rechazar progress inválido."""
        with pytest.raises(InvalidProgressError):
            await query_analytics_service(progress=5)

    @pytest.mark.asyncio
    async def test_consulta_con_multiples_filtros(self, mock_db):
        """Debe aplicar múltiples filtros."""
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__.return_value = []

        mock_db.__getitem__.return_value.find.return_value.skip.return_value.limit.return_value.sort.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=0)

        await query_analytics_service(
            user_id="user_123",
            game_id="game_456",
            progress=2,
            completed=True
        )

        call_args = mock_db.__getitem__.return_value.find.call_args
        query = call_args[0][0]
        assert query.get("user_id") == "user_123"
        assert query.get("game_id") == "game_456"
        assert query.get("progress") == 2
        assert query.get("completed") is True


# ============================================================================
# TESTS: SERVICES - UPDATE
# ============================================================================

class TestUpdateSessionComplete:
    """Tests para update_session_complete."""

    @pytest.mark.asyncio
    async def test_actualizar_campos_validos(self, mock_db):
        """Debe actualizar campos válidos."""
        mock_db.__getitem__.return_value.update_one = AsyncMock(
            return_value=MagicMock(matched_count=1, modified_count=1)
        )
        mock_db.__getitem__.return_value.find_one = AsyncMock(
            return_value={"_id": "123", "score": 100}
        )

        result = await update_session_complete("sess_123", {"score": 100})

        assert result["score"] == 100

    @pytest.mark.asyncio
    async def test_rechazar_score_negativo(self, mock_db):
        """Debe rechazar actualización con score negativo."""
        with pytest.raises(InvalidScoreError):
            await update_session_complete("sess_123", {"score": -10})

    @pytest.mark.asyncio
    async def test_rechazar_progress_invalido(self, mock_db):
        """Debe rechazar progress inválido."""
        with pytest.raises(InvalidProgressError):
            await update_session_complete("sess_123", {"progress": 5})

    @pytest.mark.asyncio
    async def test_sesion_no_encontrada(self, mock_db):
        """Debe lanzar error si sesión no existe."""
        mock_db.__getitem__.return_value.update_one = AsyncMock(
            return_value=MagicMock(matched_count=0)
        )

        with pytest.raises(AnalyticNotFoundError):
            await update_session_complete("sess_no_existe", {"score": 100})

    @pytest.mark.asyncio
    async def test_ignorar_campos_protegidos(self, mock_db):
        """Debe ignorar campos protegidos (_id, id)."""
        mock_db.__getitem__.return_value.update_one = AsyncMock(
            return_value=MagicMock(matched_count=1, modified_count=1)
        )
        mock_db.__getitem__.return_value.find_one = AsyncMock(
            return_value={"_id": "123"}
        )

        await update_session_complete("sess_123", {"_id": "new_id", "score": 100})

        # Verificar que _id no fue enviado a update_one
        call_args = mock_db.__getitem__.return_value.update_one.call_args
        update_data = call_args[0][1]["$set"]
        assert "_id" not in update_data
        assert "score" in update_data


# ============================================================================
# TESTS DE INTEGRACIÓN (si tienes FastAPI TestClient)
# ============================================================================

class TestAnalyticsEndpoints:
    """Tests de integración para endpoints (requiere TestClient)."""

    def test_post_analytics_creacion(self):
        """Test del endpoint POST /analytics/ (requiere client fixture)."""
        pytest.skip("Requiere FastAPI TestClient - implementar con conftest.py")

    def test_get_analytics_user(self):
        """Test del endpoint GET /analytics/user/{id}."""
        pytest.skip("Requiere FastAPI TestClient - implementar con conftest.py")

    def test_put_analytics_update(self):
        """Test del endpoint PUT /analytics/session/{id}."""
        pytest.skip("Requiere FastAPI TestClient - implementar con conftest.py")


# ============================================================================
# TESTS DE EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Tests para casos límite y edge cases."""

    def test_progress_valores_limites(self):
        """Debe aceptar progress 1, 2, 3 pero no 0 o 4."""
        for valid_progress in [ProgressEnum.LEVEL_1, ProgressEnum.LEVEL_2, ProgressEnum.LEVEL_3]:
            analytic = AnalyticCreate(progress=valid_progress)
            assert analytic.progress == valid_progress

        for invalid_progress in [0, 4, -1, 100]:
            with pytest.raises((ValueError, TypeError)):
                AnalyticCreate(progress=invalid_progress)

    def test_valores_cero_validos(self):
        """Campos numéricos con 0 deben ser válidos."""
        data = {
            "score": 0,
            "views": 0,
            "likes": 0,
            "plays": 0,
            "duration": 0,
        }
        analytic = AnalyticCreate(**data)
        assert analytic.score == 0
        assert analytic.views == 0

    def test_valores_grandes(self):
        """Debe aceptar valores grandes."""
        data = {
            "score": 999999,
            "views": 1000000,
            "duration": 86400,  # 1 día en segundos
        }
        analytic = AnalyticCreate(**data)
        assert analytic.score == 999999
        assert analytic.views == 1000000

    def test_strings_vacios(self):
        """Debe aceptar strings vacíos en campos opcionales."""
        data = {
            "game_id": "",
            "session_id": "",
            "question": "",
        }
        analytic = AnalyticCreate(**data)
        assert analytic.game_id == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])



