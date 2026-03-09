"""
Módulo de Analytics - Gestión de sesiones y análisis de juegos.

Proporciona servicios, esquemas y endpoints para registrar y analizar
sesiones de juego de usuarios.
"""

# Schemas
from analytics.schemas import (
    AnalyticCreate,
    AnalyticDB,
    AnalyticListResponse,
    AnalyticUpdate,
    ProgressEnum,
    UserResponseSchema,
)

# Services
from analytics.services import (
    create_analytic_service,
    get_analytics_by_user_service,
    get_analytics_by_game_service,
    query_analytics_service,
)

from analytics.services_responses import update_session_complete

# Exceptions
from analytics.exceptions import (
    AnalyticsException,
    AnalyticNotFoundError,
    InvalidAnalyticDataError,
    UnauthorizedAnalyticAccessError,
    DatabaseError,
)

# Router
from analytics.routers import router

__all__ = [
    # Schemas
    "AnalyticCreate",
    "AnalyticDB",
    "AnalyticListResponse",
    "AnalyticUpdate",
    "ProgressEnum",
    "UserResponseSchema",
    # Services
    "create_analytic_service",
    "get_analytics_by_user_service",
    "get_analytics_by_game_service",
    "query_analytics_service",
    "update_session_complete",
    # Exceptions
    "AnalyticsException",
    "AnalyticNotFoundError",
    "InvalidAnalyticDataError",
    "UnauthorizedAnalyticAccessError",
    "DatabaseError",
    # Router
    "router",
]
