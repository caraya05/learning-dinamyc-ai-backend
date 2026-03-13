from typing import Optional, List
from datetime import datetime
import datetime as dt
from pydantic import BaseModel, Field


# ============================================================================
# KPI Models
# ============================================================================

class KPICard(BaseModel):
    """Modelo para una tarjeta de KPI"""
    label: str = Field(..., example="Total Estrellas")
    value: float = Field(..., example=150)
    unit: Optional[str] = Field(default=None, example="estrellas")
    trend: Optional[str] = Field(default=None, example="up", description="up|down|stable")
    percentage_change: Optional[float] = Field(default=None, example=12.5)


class KPIs(BaseModel):
    """Modelo para todas las tarjetas de KPI del usuario"""
    total_stars: float = Field(..., example=150, description="Total de estrellas disponibles")
    active_status: bool = Field(..., example=True, description="Indica si el usuario está activo")
    series_created: int = Field(..., example=5, description="Total de juegos creados")
    count_analytics: int = Field(..., example=20, description="Total de analíticas registradas")
    charged_tokens: float = Field(..., example=1000.0, description="Tokens cargados")
    used_tokens: float = Field(..., example=500.0, description="Tokens usados")


# ============================================================================
# Time Series Models
# ============================================================================

class TimeSeriesPoint(BaseModel):
    """Punto de datos para series de tiempo"""
    date: str = Field(..., example="2026-02-25", description="Fecha en formato YYYY-MM-DD")
    value: float = Field(..., example=10)
    label: Optional[str] = Field(default=None)


class TimeSeriesData(BaseModel):
    """Series de tiempo para gráficos"""
    label: str = Field(..., example="Estrellas Utilizadas")
    data_points: List[TimeSeriesPoint] = Field(..., description="Puntos de datos por día")


# ============================================================================
# Breakdown Models
# ============================================================================

class BreakdownItem(BaseModel):
    """Elemento de desglose (ej: por status, por categoría)"""
    key: str = Field(..., example="active", description="Clave única")
    label: str = Field(..., example="Activo")
    total: int = Field(..., example=10)
    percentage: Optional[float] = Field(default=None, example=66.7)


class Breakdowns(BaseModel):
    """Desglose por diferentes dimensiones"""
    by_status: Optional[List[BreakdownItem]] = Field(
        default=None,
        description="Desglose por estado (activo, inactivo, etc)"
    )
    by_creation_status: Optional[List[BreakdownItem]] = Field(
        default=None,
        description="Desglose por estado de creación de juegos"
    )


# ============================================================================
# User Profile Section
# ============================================================================

class UserProfileDash(BaseModel):
    """Perfil del usuario en el dashboard"""
    user_id: str = Field(..., example="507f1f77bcf86cd799439011")
    username: str = Field(..., example="jhon_doe")
    email: str = Field(..., example="jhon@gmail.com")
    is_active: bool = Field(..., example=True)


# ============================================================================
# Series Models (with top game analytics)
# ============================================================================

class GameInfoForSeries(BaseModel):
    """Información del juego con más analíticas en una serie"""
    game_id: str = Field(..., example="507f1f77bcf86cd799439011")
    title: Optional[str] = Field(None, example="Game Title")
    analytics_count: int = Field(default=0, example=15, description="Cantidad de analíticas de este juego")
    games_in_series: Optional[List[dict]] = Field(None, description="Lista de todos los juegos de la serie: id, title, analytics_count")


class SeriesData(BaseModel):
    """Datos de una serie con información de su juego con más analíticas"""
    series_id: str = Field(..., example="507f1f77bcf86cd799439011")
    is_active: bool = Field(default=True, example=True)
    is_published: bool = Field(default=False, example=False)
    publish_type: Optional[str] = Field("private", example="public")
    created_at: datetime = Field(..., example="2026-02-25T16:18:59")
    games_count: int = Field(default=0, example=3, description="Total de juegos en la serie")
    total_analytics: int = Field(default=0, example=45, description="Total de analíticas de todos los juegos de la serie")
    top_game: Optional[GameInfoForSeries] = Field(None, description="Juego con más analíticas + lista de todos los juegos de la serie")


# ============================================================================
# Series Completion Metrics Models (MUST BE BEFORE DashboardSummary)
# ============================================================================

class MonthlySeriesMetrics(BaseModel):
    """Métricas de series completadas para un mes específico"""
    month: str = Field(..., example="2026-02", description="Mes en formato YYYY-MM")
    series_created: int = Field(default=0, example=5, description="Total de series creadas en el mes")
    series_completed: int = Field(default=0, example=3, description="Series completadas (con todos los juegos jugados)")
    series_partially_completed: int = Field(default=0, example=1, description="Series con al menos un juego completado")
    completion_percentage: float = Field(default=0.0, example=60.0, description="Porcentaje de series completadas")
    avg_games_played_per_series: float = Field(default=0.0, example=2.5, description="Promedio de juegos jugados por serie")
    total_analytics: int = Field(default=0, example=450, description="Total de analíticas registradas")
    total_completed_analytics: int = Field(default=0, example=270, description="Total de analíticas completadas")
    tokens_charged: float = Field(default=0.0, example=500.0, description="Tokens/Estrellas cargadas en el mes")
    tokens_used: float = Field(default=0.0, example=400.0, description="Tokens/Estrellas usadas en el mes")


class SeriesCompletionMetrics(BaseModel):
    """Resumen de métricas de completación de series en un rango de fechas"""
    range_applied: dict = Field(
        ...,
        description="Rango de fechas aplicado",
        example={"from": "2026-01-01", "to": "2026-02-28"}
    )
    monthly_metrics: List[MonthlySeriesMetrics] = Field(
        ...,
        description="Métricas desglosadas por mes"
    )
    summary: dict = Field(
        ...,
        description="Resumen agregado del período",
        example={
            "total_series_created": 15,
            "total_series_completed": 8,
            "overall_completion_percentage": 53.3,
            "total_series_partially_completed": 5,
            "total_tokens_charged": 1000.0,
            "total_tokens_used": 750.0,
            "tokens_balance": 250.0
        }
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(dt.UTC),
        description="Timestamp de generación del reporte"
    )




# ============================================================================
# Main Dashboard Summary Response
# ============================================================================

class DashboardSummary(BaseModel):
    """Respuesta agregada del dashboard del usuario"""

    # Metadata
    range_applied: dict = Field(
        ...,
        description="Rango de fechas aplicado",
        example={"from": "2026-02-01", "to": "2026-02-25", "timezone": "America/Bogota"}
    )

    # User Profile
    user: UserProfileDash = Field(..., description="Información del usuario")

    # KPIs
    kpis: KPIs = Field(..., description="Tarjetas de KPI principales")

    # Time Series
    timeseries: Optional[List[TimeSeriesData]] = Field(
        default=None,
        description="Series de tiempo para gráficos"
    )

    # Breakdowns
    breakdowns: Optional[Breakdowns] = Field(
        default=None,
        description="Desglose por diferentes dimensiones"
    )

    # Series
    series: Optional[List[SeriesData]] = Field(
        default=None,
        description="Series del usuario ordenadas por cantidad de analíticas (descendente)"
    )



    # Timestamp
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(dt.UTC),
        description="Timestamp de generación del reporte"
    )



# ============================================================================
# Batch Dashboard Request/Response
# ============================================================================

class BatchDashboardRequest(BaseModel):
    """Request para obtener múltiples widgets en una sola llamada"""
    from_date: str = Field(..., example="2026-02-01", description="Fecha de inicio (YYYY-MM-DD)")
    to_date: str = Field(..., example="2026-02-25", description="Fecha de fin (YYYY-MM-DD)")
    timezone: Optional[str] = Field(default="UTC", example="America/Bogota")
    group_by: Optional[str] = Field(
        default="day",
        example="day",
        description="Agrupar series de tiempo por: day|week|month"
    )
    widgets: Optional[List[str]] = Field(
        default=None,
        example=["kpis", "timeseries", "breakdowns"],
        description="Widgets a calcular. Si es None, calcula todos."
    )
















