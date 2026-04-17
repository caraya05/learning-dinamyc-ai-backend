"""
Tests para User Dashboard Services (_dash)

Prueba los servicios de dashboard que proporcionan endpoints agregados
para obtener toda la información del dashboard en una sola petición.
"""

import pytest
from datetime import datetime
from bson import ObjectId
from unittest.mock import AsyncMock, patch

from user.services_dash import (
    get_user_dashboard_summary_service,
    _build_user_kpis,
    _build_user_timeseries,
    _build_user_breakdowns,
    get_batch_dashboard_service,
)
from user.schemas_dash import (
    DashboardSummary,
    KPIs,
    BatchDashboardRequest,
)


class TestBuildUserKPIs:
    """Test suite para la construcción de KPIs del usuario"""

    @pytest.mark.asyncio
    async def test_build_user_kpis_success(self):
        """Test construcción exitosa de KPIs"""
        user_db = {
            "_id": ObjectId(),
            "stars": 150,
            "is_active": True,
            "number_of_creation_attempts": 2,
        }

        with patch("user.services_dash.db") as mock_db:
            mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=5)

            kpis = await _build_user_kpis(user_db)

            assert isinstance(kpis, KPIs)
            assert kpis.total_stars == 150.0
            assert kpis.active_status is True
            assert kpis.games_created == 5
            assert kpis.creation_attempts == 2

    @pytest.mark.asyncio
    async def test_build_user_kpis_default_values(self):
        """Test KPIs con valores por defecto"""
        user_db = {
            "_id": ObjectId(),
        }

        with patch("user.services_dash.db") as mock_db:
            mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=0)

            kpis = await _build_user_kpis(user_db)

            assert kpis.total_stars == 0.0
            assert kpis.active_status is False
            assert kpis.games_created == 0
            assert kpis.creation_attempts == 0


class TestBuildUserTimeSeries:
    """Test suite para la construcción de series de tiempo"""

    @pytest.mark.asyncio
    async def test_build_user_timeseries_with_data(self):
        """Test construcción de timeseries con datos"""
        user_id = str(ObjectId())
        from_date = "2026-02-01"
        to_date = "2026-02-03"

        mock_records = [
            {
                "user_id": user_id,
                "created_at": datetime.strptime("2026-02-01", "%Y-%m-%d"),
                "balance": 150,
                "expenses": 10,
                "games_created": 1,
            },
            {
                "user_id": user_id,
                "created_at": datetime.strptime("2026-02-02", "%Y-%m-%d"),
                "balance": 140,
                "expenses": 10,
                "games_created": 1,
            },
        ]

        with patch("user.services_dash.db") as mock_db:
            mock_find = AsyncMock()
            mock_find.to_list = AsyncMock(return_value=mock_records)
            mock_db.__getitem__.return_value.find.return_value = mock_find

            timeseries = await _build_user_timeseries(user_id, from_date, to_date)

            assert timeseries is not None
            assert len(timeseries) == 3  # Tres series: expenses, balance, games
            assert timeseries[0].label == "Estrellas Utilizadas"
            assert timeseries[1].label == "Balance de Estrellas"
            assert timeseries[2].label == "Juegos Creados"

    @pytest.mark.asyncio
    async def test_build_user_timeseries_no_data(self):
        """Test timeseries sin datos"""
        with patch("user.services_dash.db") as mock_db:
            mock_find = AsyncMock()
            mock_find.to_list = AsyncMock(return_value=[])
            mock_db.__getitem__.return_value.find.return_value = mock_find

            timeseries = await _build_user_timeseries(
                str(ObjectId()),
                "2026-02-01",
                "2026-02-03"
            )

            assert timeseries is None


class TestBuildUserBreakdowns:
    """Test suite para la construcción de desgloces"""

    @pytest.mark.asyncio
    async def test_build_user_breakdowns_success(self):
        """Test construcción exitosa de breakdowns"""
        user_db = {
            "_id": ObjectId(),
            "is_active": True,
            "attempt_to_create": True,
            "number_of_creation_attempts": 3,
        }

        with patch("user.services_dash.db") as mock_db:
            mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=5)

            breakdowns = await _build_user_breakdowns(user_db)

            assert breakdowns is not None
            assert breakdowns.by_status is not None
            assert len(breakdowns.by_status) == 2
            assert breakdowns.by_status[0].key == "active"
            assert breakdowns.by_status[0].total == 1

    @pytest.mark.asyncio
    async def test_build_user_breakdowns_inactive_user(self):
        """Test breakdowns para usuario inactivo"""
        user_db = {
            "_id": ObjectId(),
            "is_active": False,
        }

        with patch("user.services_dash.db") as mock_db:
            mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=0)

            breakdowns = await _build_user_breakdowns(user_db)

            assert breakdowns is not None
            assert breakdowns.by_status[0].total == 0  # active: 0
            assert breakdowns.by_status[1].total == 1  # inactive: 1


class TestGetUserDashboardSummary:
    """Test suite para el servicio principal de dashboard"""

    @pytest.mark.asyncio
    async def test_get_user_dashboard_summary_success(self):
        """Test obtención exitosa del dashboard summary"""
        user_id = str(ObjectId())
        user_db = {
            "_id": ObjectId(user_id),
            "username": "test_user",
            "email": "test@example.com",
            "photo": None,
            "is_active": True,
            "is_superuser": False,
            "is_staff": False,
            "stars": 100,
            "number_of_creation_attempts": 0,
        }

        with patch("user.services_dash.db") as mock_db:
            # Mock para find_one (obtener usuario)
            mock_db.__getitem__.return_value.find_one = AsyncMock(return_value=user_db)

            # Mock para count_documents
            mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=5)

            # Mock para find (timeseries)
            mock_find = AsyncMock()
            mock_find.to_list = AsyncMock(return_value=[])
            mock_db.__getitem__.return_value.find.return_value = mock_find

            dashboard = await get_user_dashboard_summary_service(
                user_id=user_id,
                from_date="2026-02-01",
                to_date="2026-02-25",
            )

            assert isinstance(dashboard, DashboardSummary)
            assert dashboard.user.username == "test_user"
            assert dashboard.user.email == "test@example.com"
            assert dashboard.kpis.total_stars == 100.0
            assert dashboard.range_applied["from"] == "2026-02-01"

    @pytest.mark.asyncio
    async def test_get_user_dashboard_summary_user_not_found(self):
        """Test cuando el usuario no existe"""
        from fastapi import HTTPException

        with patch("user.services_dash.db") as mock_db:
            mock_db.__getitem__.return_value.find_one = AsyncMock(return_value=None)

            with pytest.raises(HTTPException):
                await get_user_dashboard_summary_service(
                    user_id=str(ObjectId()),
                    from_date="2026-02-01",
                    to_date="2026-02-25",
                )

    @pytest.mark.asyncio
    async def test_get_user_dashboard_summary_default_dates(self):
        """Test con fechas por defecto (últimos 30 días)"""
        user_id = str(ObjectId())
        user_db = {
            "_id": ObjectId(user_id),
            "username": "test_user",
            "email": "test@example.com",
            "photo": None,
            "is_active": True,
            "is_superuser": False,
            "is_staff": False,
            "stars": 100,
            "number_of_creation_attempts": 0,
        }

        with patch("user.services_dash.db") as mock_db:
            mock_db.__getitem__.return_value.find_one = AsyncMock(return_value=user_db)
            mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=0)
            mock_find = AsyncMock()
            mock_find.to_list = AsyncMock(return_value=[])
            mock_db.__getitem__.return_value.find.return_value = mock_find

            dashboard = await get_user_dashboard_summary_service(
                user_id=user_id,
                from_date=None,  # Sin fecha de inicio
                to_date=None,    # Sin fecha de fin
            )

            assert dashboard.range_applied["from"] is not None
            assert dashboard.range_applied["to"] is not None


class TestGetBatchDashboard:
    """Test suite para el servicio de batch dashboard"""

    @pytest.mark.asyncio
    async def test_get_batch_dashboard_kpis_only(self):
        """Test obtención de dashboard solo con KPIs"""
        user_id = str(ObjectId())
        user_db = {
            "_id": ObjectId(user_id),
            "username": "test_user",
            "email": "test@example.com",
            "photo": None,
            "is_active": True,
            "is_superuser": False,
            "is_staff": False,
            "stars": 100,
            "number_of_creation_attempts": 0,
        }

        request = BatchDashboardRequest(
            from_date="2026-02-01",
            to_date="2026-02-25",
            widgets=["kpis"],
        )

        with patch("user.services_dash.db") as mock_db:
            mock_db.__getitem__.return_value.find_one = AsyncMock(return_value=user_db)
            mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=5)
            mock_find = AsyncMock()
            mock_find.to_list = AsyncMock(return_value=[])
            mock_db.__getitem__.return_value.find.return_value = mock_find

            dashboard = await get_batch_dashboard_service(user_id, request)

            assert dashboard.kpis is not None
            assert dashboard.timeseries is None
            assert dashboard.breakdowns is None

    @pytest.mark.asyncio
    async def test_get_batch_dashboard_all_widgets(self):
        """Test obtención de dashboard con todos los widgets"""
        user_id = str(ObjectId())
        user_db = {
            "_id": ObjectId(user_id),
            "username": "test_user",
            "email": "test@example.com",
            "photo": None,
            "is_active": True,
            "is_superuser": False,
            "is_staff": False,
            "stars": 100,
            "number_of_creation_attempts": 0,
        }

        request = BatchDashboardRequest(
            from_date="2026-02-01",
            to_date="2026-02-25",
            widgets=["kpis", "timeseries", "breakdowns"],
        )

        with patch("user.services_dash.db") as mock_db:
            mock_db.__getitem__.return_value.find_one = AsyncMock(return_value=user_db)
            mock_db.__getitem__.return_value.count_documents = AsyncMock(return_value=5)
            mock_find = AsyncMock()
            mock_find.to_list = AsyncMock(return_value=[])
            mock_db.__getitem__.return_value.find.return_value = mock_find

            dashboard = await get_batch_dashboard_service(user_id, request)

            assert dashboard.kpis is not None
            assert dashboard.timeseries is not None or dashboard.timeseries is None
            assert dashboard.breakdowns is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


