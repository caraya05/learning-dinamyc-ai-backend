"""
Services para Dashboard de Usuarios (_dash)

Proporciona endpoints agregados que devuelven toda la información necesaria
para construir un dashboard en una sola petición.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from core.database import db
from user.schemas_dash import (
    DashboardSummary,
    KPIs,
    UserProfileDash,
    TimeSeriesData,
    TimeSeriesPoint,
    Breakdowns,
    BreakdownItem,
    SeriesData,
    GameInfoForSeries,
    MonthlySeriesMetrics,
    SeriesCompletionMetrics,
)


async def _build_user_kpis(user_db: dict) -> KPIs:
    """
    Construye las tarjetas de KPI del usuario.

    Args:
        user_db: Documento del usuario desde MongoDB

    Returns:
        KPIs: Objeto con todos los KPIs
    """
    stars = user_db.get("stars", 0)
    is_active = user_db.get("is_active", False)

    # Contar series creadas
    series_count = await db["game"].count_documents({"created_by": str(user_db.get("_id"))})

    # Obtener IDs de games creados por el usuario
    games_list = await db["game"].find({"created_by": str(user_db.get("_id"))}).to_list(None)
    game_ids = [str(g.get("_id")) for g in games_list]

    # Contar analytics de esos games
    analytics_count = 0
    if game_ids:
        analytics_count = await db["analytics"].count_documents({"gameId": {"$in": game_ids}})

    # Contar tokens cargados
    tokens_charged_records = await db["star_recharge"].find({
        "user_id": str(user_db.get("_id"))
    }).to_list(None)

    tokens_charged = 0.0
    if tokens_charged_records:
        tokens_charged = sum([item.get("stars_recharged", 0) for item in tokens_charged_records])

    # Contar tokens usados (games_created * 10)
    tokens_used = series_count * 10

    return KPIs(
        total_stars=float(stars),
        active_status=is_active,
        series_created=series_count,
        count_analytics=analytics_count,
        charged_tokens=tokens_charged,
        used_tokens=tokens_used,
    )


async def _build_user_timeseries(
        user_id: str,
        from_date: str,
        to_date: str,
        group_by: str = "day",
) -> Optional[List[TimeSeriesData]]:
    """
    Construye las series de tiempo para gráficos mes a mes.

    Calcula por mes:
    - Series creadas
    - Analytics registradas
    - Tokens cargados
    - Tokens usados

    Args:
        user_id: ID del usuario
        from_date: Fecha de inicio
        to_date: Fecha de fin
        group_by: 'day', 'week' o 'month'

    Returns:
        Lista de series de tiempo o None si no hay datos
    """
    try:
        from_datetime = datetime.strptime(from_date, "%Y-%m-%d")
        to_datetime = datetime.strptime(to_date, "%Y-%m-%d")

        # ============ SERIES CREADAS POR MES ============
        series_by_month = await db["series"].aggregate([
            {
                "$match": {
                    "created_by": user_id,
                    "created_at": {
                        "$gte": from_datetime,
                        "$lte": to_datetime,
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m",
                            "date": "$created_at"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]).to_list(None)

        series_dict = {item["_id"]: item["count"] for item in series_by_month}

        # ============ ANALYTICS POR MES ============
        # Obtener games del usuario
        games_list = await db["game"].find({"created_by": user_id}).to_list(None)
        game_ids = [str(g.get("_id")) for g in games_list]

        analytics_by_month = {}
        if game_ids:
            analytics_result = await db["analytics"].aggregate([
                {
                    "$match": {
                        "game_id": {"$in": game_ids},
                        "created_at": {
                            "$gte": from_datetime,
                            "$lte": to_datetime,
                        }
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "format": "%Y-%m",
                                "date": "$created_at"
                            }
                        },
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"_id": 1}}
            ]).to_list(None)

            analytics_dict = {item["_id"]: item["count"] for item in analytics_result}
        else:
            analytics_dict = {}

        # ============ TOKENS CARGADOS POR MES ============
        tokens_charged_result = await db["star_recharge"].aggregate([
            {
                "$match": {
                    "user_id": user_id,
                    "created_at": {
                        "$gte": from_datetime,
                        "$lte": to_datetime,
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m",
                            "date": "$created_at"
                        }
                    },
                    "total": {"$sum": "$stars_recharged"}
                }
            },
            {"$sort": {"_id": 1}}
        ]).to_list(None)

        tokens_charged_dict = {item["_id"]: item["total"] for item in tokens_charged_result}

        # ============ TOKENS USADOS POR MES ============
        tokens_used_result = await db["game"].aggregate([
            {
                "$match": {
                    "created_by": user_id,
                    "created_at": {
                        "$gte": from_datetime,
                        "$lte": to_datetime,
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m",
                            "date": "$created_at"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]).to_list(None)

        tokens_used_dict = {item["_id"]: item["count"] for item in tokens_used_result}

        # Generar todos los meses en el rango
        all_months = []
        current_date = from_datetime
        while current_date <= to_datetime:
            month_str = current_date.strftime("%Y-%m")
            all_months.append(month_str)
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        # Construir puntos de serie por mes
        series_points = [
            TimeSeriesPoint(
                date=month,
                value=series_dict.get(month, 0),
            )
            for month in all_months
        ]

        analytics_points = [
            TimeSeriesPoint(
                date=month,
                value=analytics_dict.get(month, 0),
            )
            for month in all_months
        ]

        tokens_charged_points = [
            TimeSeriesPoint(
                date=month,
                value=tokens_charged_dict.get(month, 0.0),
            )
            for month in all_months
        ]

        tokens_used_points = [
            TimeSeriesPoint(
                date=month,
                value=tokens_used_dict.get(month, 0.0),
            )
            for month in all_months
        ]

        return [
            TimeSeriesData(
                label="Series Creadas",
                data_points=series_points,
            ),
            TimeSeriesData(
                label="Analytics Registradas",
                data_points=analytics_points,
            ),
            TimeSeriesData(
                label="Tokens Cargados",
                data_points=tokens_charged_points,
            ),
            TimeSeriesData(
                label="Tokens Usados",
                data_points=tokens_used_points,
            ),
        ]

    except Exception as e:
        print(f"Error in _build_user_timeseries: {str(e)}")
        return None


async def _build_user_breakdowns(user_db: dict) -> Optional[Breakdowns]:
    """
    Construye los desgloces (breakdowns) del usuario.

    Args:
        user_db: Documento del usuario desde MongoDB

    Returns:
        Breakdowns: Objeto con los desgloces
    """
    try:
        # Desglose por estado
        is_active = user_db.get("is_active", False)
        status_breakdown = [
            BreakdownItem(
                key="active",
                label="Activo",
                total=1 if is_active else 0,
                percentage=100.0 if is_active else 0.0,
            ),
            BreakdownItem(
                key="inactive",
                label="Inactivo",
                total=0 if is_active else 1,
                percentage=0.0 if is_active else 100.0,
            ),
        ]

        # Desglose por estado de creación
        attempt_to_create = user_db.get("attempt_to_create", False)
        creation_breakdown = [
            BreakdownItem(
                key="without_balance",
                label="Intentos Sin Balance",
                total=user_db.get("number_of_creation_attempts", 0),
                percentage=100.0 if user_db.get("number_of_creation_attempts", 0) > 0 else 0.0,
            ),
            BreakdownItem(
                key="with_balance",
                label="Creaciones Realizadas",
                total=await db["game"].count_documents({"created_by": str(user_db.get("_id"))}),
                percentage=None,
            ),
        ]

        return Breakdowns(
            by_status=status_breakdown,
            by_creation_status=creation_breakdown,
        )

    except Exception as e:
        print(f"Error in _build_user_breakdowns: {str(e)}")
        return None


async def _get_user_series_with_analytics(user_id: str) -> Optional[List[dict]]:
    """
    Construye la lista de series del usuario con información de analíticas.

    Para cada serie:
    1. Obtiene todos los juegos asociados
    2. Cuenta las analíticas de cada juego
    3. Selecciona el juego con más analíticas
    4. Ordena las series por cantidad total de analíticas (descendente)

    Args:
        user_id: ID del usuario

    Returns:
        Lista de series ordenadas por cantidad de analíticas (descendente) o None
    """
    try:
        # Obtener todas las series del usuario
        series_list = await db["series"].find({"created_by": user_id}).to_list(None)

        if not series_list:
            return None

        # Procesar cada serie
        series_with_analytics = []

        for series_db in series_list:
            series_id = str(series_db.get("_id"))
            games_ids = series_db.get("games_id", [])

            # Inicializar contadores
            total_analytics = 0
            top_game = None
            games_count = len(games_ids)

            if games_count > 0:
                # Convertir IDs de string a ObjectId si es necesario
                games_ids_obj = []
                for game_id in games_ids:
                    if isinstance(game_id, str):
                        try:
                            games_ids_obj.append(ObjectId(game_id))
                        except:
                            games_ids_obj.append(game_id)
                    else:
                        games_ids_obj.append(game_id)

                # Obtener todos los juegos de esta serie
                games = await db["game"].find({
                    "_id": {"$in": games_ids_obj}
                }).to_list(None)

                # Para cada juego, contar analíticas
                games_analytics = {}
                for game in games:
                    game_id = str(game.get("_id"))
                    analytics_count = await db["analytics"].count_documents({
                        "game_id": game_id
                    })
                    games_analytics[game_id] = {
                        "game": game,
                        "analytics_count": analytics_count
                    }
                    total_analytics += analytics_count

                # Seleccionar el juego con más analíticas
                if games_analytics:
                    top_game_id = max(games_analytics, key=lambda x: games_analytics[x]["analytics_count"])
                    top_game_data = games_analytics[top_game_id]
                    top_game = GameInfoForSeries(
                        game_id=top_game_id,
                        title=top_game_data["game"].get("title"),
                        analytics_count=top_game_data["analytics_count"]
                    )

            # Crear objeto SeriesData
            series_data = SeriesData(
                series_id=series_id,
                title=series_db.get("title", ""),
                description=series_db.get("description"),
                image=series_db.get("image"),
                rating=series_db.get("rating", 0.0),
                is_active=series_db.get("is_active", True),
                is_published=series_db.get("is_published", False),
                publish_type=series_db.get("publish_type", "private"),
                created_at=series_db.get("created_at", datetime.utcnow()),
                games_count=games_count,
                total_analytics=total_analytics,
                top_game=top_game
            )

            series_with_analytics.append(series_data)

        # Ordenar por cantidad de analíticas (descendente)
        series_with_analytics.sort(key=lambda x: x.total_analytics, reverse=True)

        return series_with_analytics if series_with_analytics else None

    except Exception as e:
        print(f"Error in _get_user_series_with_analytics: {str(e)}")
        return None


async def get_user_dashboard_summary_service(
        user_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        timezone: str = "UTC",
) -> DashboardSummary:
    """
    Obtiene el resumen completo del dashboard para un usuario específico.

    Devuelve:
    - Información del usuario
    - KPIs principales (estrellas, juegos, intentos)
    - Series de tiempo de actividad
    - Desgloces por dimensión
    - Series con información de analíticas

    Args:
        user_id: ID del usuario
        from_date: Fecha de inicio (YYYY-MM-DD). Si es None, usa últimos 30 días
        to_date: Fecha de fin (YYYY-MM-DD). Si es None, usa la fecha actual
        timezone: Zona horaria para cortes de fecha

    Returns:
        DashboardSummary: Objeto completo del dashboard

    Raises:
        HTTPException: Si el usuario no existe o hay error en la consulta
    """
    try:
        # Procesar fechas
        if not to_date:
            to_date = datetime.utcnow().strftime("%Y-%m-%d")
        if not from_date:
            to_datetime = datetime.strptime(to_date, "%Y-%m-%d")
            from_datetime = to_datetime - timedelta(days=30)
            from_date = from_datetime.strftime("%Y-%m-%d")

        # Obtener información del usuario
        user_db = await db["user"].find_one({"_id": ObjectId(user_id)})

        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )

        # Construir perfil del usuario
        user_profile = UserProfileDash(
            user_id=str(user_db.get("_id")),
            username=user_db.get("username", ""),
            email=user_db.get("email", ""),
            photo=user_db.get("photo"),
            is_active=user_db.get("is_active", False),
            is_superuser=user_db.get("is_superuser", False),
            is_staff=user_db.get("is_staff", False),
        )

        # Construir KPIs
        kpis = await _build_user_kpis(user_db)

        # Construir series de tiempo
        timeseries = await _build_user_timeseries(str(user_db.get("_id")), from_date, to_date)

        # Construir desgloces
        breakdowns = await _build_user_breakdowns(user_db)

        # Construir series con analíticas
        series_data = await _get_user_series_with_analytics(str(user_db.get("_id")))

        # Construir métricas de completación de series (incluye tokens)
        completion_metrics = await get_series_completion_metrics_service(
            user_id=str(user_db.get("_id")),
            from_date=from_date,
            to_date=to_date,
        )

        # Construir respuesta del dashboard
        dashboard = DashboardSummary(
            range_applied={
                "from": from_date,
                "to": to_date,
                "timezone": timezone,
            },
            user=user_profile,
            kpis=kpis,
            timeseries=timeseries,
            breakdowns=breakdowns,
            series=series_data,
            series_completion_metrics=completion_metrics,
            generated_at=datetime.utcnow(),
        )

        return dashboard

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_user_dashboard_summary_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al obtener dashboard del usuario: {str(e)}"
        )


async def get_all_users_dashboard_summary_service(
        skip: int = 0,
        limit: int = 10,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        timezone: str = "UTC",
) -> dict:
    """
    Obtiene un resumen agregado de todos los usuarios para un dashboard administrativo.

    Args:
        skip: Número de registros a saltar
        limit: Número máximo de registros a devolver
        from_date: Fecha de inicio
        to_date: Fecha de fin
        timezone: Zona horaria

    Returns:
        Dict con KPIs totales y lista de usuarios
    """
    try:
        # Procesar fechas
        if not to_date:
            to_date = datetime.utcnow().strftime("%Y-%m-%d")
        if not from_date:
            to_datetime = datetime.strptime(to_date, "%Y-%m-%d")
            from_datetime = to_datetime - timedelta(days=30)
            from_date = from_datetime.strftime("%Y-%m-%d")

        # Obtener todos los usuarios
        users = await db["user"].find().skip(skip).limit(limit).to_list(None)
        total_users = await db["user"].count_documents({})

        # Calcular KPIs globales
        active_users_count = await db["user"].count_documents({"is_active": True})
        total_stars = await db["user"].aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$stars"}}}
        ]).to_list(None)

        total_stars_value = total_stars[0]["total"] if total_stars else 0

        global_kpis = KPIs(
            total_stars=float(total_stars_value),
            active_status=active_users_count > 0,
            series_created=await db["game"].count_documents({}),
        )

        return {
            "range_applied": {
                "from": from_date,
                "to": to_date,
                "timezone": timezone,
            },
            "global_kpis": global_kpis,
            "users_count": total_users,
            "active_users_count": active_users_count,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total_users,
            },
            "generated_at": datetime.utcnow(),
        }

    except Exception as e:
        print(f"Error in get_all_users_dashboard_summary_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al obtener resumen global del dashboard: {str(e)}"
        )


async def get_all_users_detailed_service(
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "games_created",
        order: str = "desc",
) -> dict:
    """
    Obtiene un listado simplificado de TODOS los usuarios con información esencial.

    Información devuelta por usuario:
    - id: ID del usuario
    - nombre: Nombre de usuario (username)
    - correo: Correo electrónico
    - cuando_se_crea: Fecha de creación
    - cantidad_stars: Saldo actual de estrellas
    - cantidad_series_creadas: Total de series/juegos creados
    - cantidad_stars_usadas: Estrellas consumidas (series_creadas * 10)
    - cantidad_vistas: Total de vistas en los juegos/series del usuario

    Args:
        skip: Número de usuarios a saltar (para paginación)
        limit: Número máximo de usuarios a devolver
        sort_by: Campo por el cual ordenar ('games_created', 'stars', 'views', 'created_at')
        order: Dirección del ordenamiento ('asc' para ascendente, 'desc' para descendente)

    Returns:
        Dict con lista de usuarios simplificados y metadata de paginación

    Raises:
        HTTPException: Si hay error en la consulta
    """
    try:
        # Obtener todos los usuarios (sin límite para poder ordenarlos)
        users_db = await db["user"].find().to_list(None)
        total_users = await db["user"].count_documents({})

        # Construir lista de usuarios simplificados
        users_detailed = []
        for user_db in users_db:
            user_id_str = str(user_db.get("_id"))

            # Contar juegos/series del usuario
            games_count = await db["game"].count_documents({"created_by": user_id_str})

            # Calcular estrellas usadas (games_created * 10)
            stars_used = games_count * 10

            # Obtener todas las analíticas de los juegos del usuario
            total_views = 0
            if games_count > 0:
                # Obtener todos los game_ids del usuario
                games = await db["game"].find({"created_by": user_id_str}).to_list(None)
                game_ids = [str(game.get("_id")) for game in games]

                # Sumar vistas de todas las analíticas de esos juegos
                if game_ids:
                    total_views = await db["analytics"].count_documents({"gameId": {"$in": game_ids}})

            # Construir objeto simplificado del usuario
            user_detail = {
                "user_id": user_id_str,
                "username": user_db.get("username", ""),
                "email": user_db.get("email", ""),
                "created_at": user_db.get("created_at", datetime.utcnow()),
                "stars": float(user_db.get("stars", 0)),
                "games_created": games_count,
                "stars_used": stars_used,
                "views": total_views,
            }
            users_detailed.append(user_detail)

        # Ordenar usuarios según parámetro
        reverse_order = order.lower() == "desc"

        if sort_by == "games_created":
            users_detailed.sort(key=lambda x: x["games_created"], reverse=reverse_order)
        elif sort_by == "stars":
            users_detailed.sort(key=lambda x: x["stars"], reverse=reverse_order)
        elif sort_by == "views":
            users_detailed.sort(key=lambda x: x["views"], reverse=reverse_order)
        elif sort_by == "created_at":
            users_detailed.sort(key=lambda x: x["created_at"], reverse=reverse_order)

        # Aplicar paginación después de ordenar
        users_paginated = users_detailed[skip:skip + limit]

        return {
            "users": users_paginated,
            "total": total_users,
            "skip": skip,
            "limit": limit,
            "sort_by": sort_by,
            "order": order,
            "generated_at": datetime.utcnow(),
        }

    except Exception as e:
        print(f"Error in get_all_users_detailed_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al obtener listado de usuarios: {str(e)}"
        )


async def get_global_kpis_service(
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
) -> dict:
    """
    Obtiene los KPIs globales agregados de todo el sistema.

    Devuelve métricas de:
    - Total de estrellas en el sistema
    - Usuarios activos
    - Series creadas en el período
    - Analíticas registradas en el período
    - Usuarios que crearon series en el período

    Args:
        from_date: Fecha de inicio (YYYY-MM-DD). Si es None, usa los últimos 30 días
        to_date: Fecha de fin (YYYY-MM-DD). Si es None, usa la fecha actual

    Returns:
        Dict con KPIs globales y series de tiempo mensual

    Raises:
        HTTPException: Si hay error en la consulta
    """
    try:
        # Procesar fechas
        if not to_date:
            to_date = datetime.utcnow().strftime("%Y-%m-%d")
        if not from_date:
            to_datetime = datetime.strptime(to_date, "%Y-%m-%d")
            from_datetime = to_datetime - timedelta(days=30)
            from_date = from_datetime.strftime("%Y-%m-%d")

        from_datetime = datetime.strptime(from_date, "%Y-%m-%d")
        to_datetime = datetime.strptime(to_date, "%Y-%m-%d")

        # ============ CALCULAR KPIs GLOBALES ============

        # Total de estrellas en el sistema
        total_stars_agg = await db["user"].aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$stars"}}}
        ]).to_list(None)
        total_stars = total_stars_agg[0]["total"] if total_stars_agg else 0

        # Total de usuarios activos
        active_users_count = await db["user"].count_documents({"is_active": True})
        total_users_count = await db["user"].count_documents({})

        # Total de usuarios en lista de espera (is_preview = False)
        waitlist_users_count = await db["user"].count_documents({"is_preview": False})

        # Series creadas en el período
        series_created = await db["game"].count_documents({
            "created_at": {
                "$gte": from_datetime,
                "$lte": to_datetime,
            }
        })

        # Analíticas registradas en el período
        analytics_count = await db["analytics"].count_documents({
            "created_at": {
                "$gte": from_datetime,
                "$lte": to_datetime,
            }
        })

        # Usuarios únicos que crearon series en el período
        users_creators = await db["series"].aggregate([
            {
                "$match": {
                    "created_at": {
                        "$gte": from_datetime,
                        "$lte": to_datetime,
                    }
                }
            },
            {
                "$group": {
                    "_id": "$created_by",
                }
            },
            {
                "$count": "total"
            }
        ]).to_list(None)
        unique_creators = users_creators[0]["total"] if users_creators else 0

        # ============ CONSTRUIR SERIES DE TIEMPO MENSUAL ============

        # Series creadas por mes
        series_by_month = await db["series"].aggregate([
            {
                "$match": {
                    "created_at": {
                        "$gte": from_datetime,
                        "$lte": to_datetime,
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m",
                            "date": "$created_at"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]).to_list(None)

        # Usuarios creadores por mes
        users_by_month = await db["series"].aggregate([
            {
                "$match": {
                    "created_at": {
                        "$gte": from_datetime,
                        "$lte": to_datetime,
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m",
                            "date": "$created_at"
                        }
                    },
                    "unique_users": {"$addToSet": "$created_by"}
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "user_count": {"$size": "$unique_users"}
                }
            },
            {"$sort": {"_id": 1}}
        ]).to_list(None)

        # Analíticas por mes
        analytics_by_month = await db["analytics"].aggregate([
            {
                "$match": {
                    "created_at": {
                        "$gte": from_datetime,
                        "$lte": to_datetime,
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m",
                            "date": "$created_at"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]).to_list(None)

        # Convertir resultados a diccionarios
        series_dict = {item["_id"]: item["count"] for item in series_by_month}
        users_dict = {item["_id"]: item["user_count"] for item in users_by_month}
        analytics_dict = {item["_id"]: item["count"] for item in analytics_by_month}

        # Generar TODOS los meses entre from_date y to_date
        all_months = []
        current_date = from_datetime
        while current_date <= to_datetime:
            month_str = current_date.strftime("%Y-%m")
            all_months.append(month_str)
            # Avanzar al siguiente mes
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        # Construir puntos de serie
        series_points = [
            {
                "month": month,
                "value": series_dict.get(month, 0),
            }
            for month in all_months
        ]

        users_points = [
            {
                "month": month,
                "value": users_dict.get(month, 0),
            }
            for month in all_months
        ]

        analytics_points = [
            {
                "month": month,
                "value": analytics_dict.get(month, 0),
            }
            for month in all_months
        ]

        return {
            "range_applied": {
                "from": from_date,
                "to": to_date,
            },
            "global_kpis": {
                "total_stars": float(total_stars),
                "active_users": active_users_count,
                "total_users": total_users_count,
                "users_percentage": round(
                    (active_users_count / total_users_count * 100) if total_users_count > 0 else 0, 2),
                "series_created": series_created,
                "analytics_registered": analytics_count,
                "unique_creators": unique_creators,
                "waitlist_users": waitlist_users_count,
            },
            "timeseries": {
                "series_created_by_month": series_points,
                "users_creators_by_month": users_points,
                "analytics_registered_by_month": analytics_points,
            },
            "generated_at": datetime.utcnow(),
        }

    except Exception as e:
        print(f"Error in get_global_kpis_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al obtener KPIs globales: {str(e)}"
        )


async def get_series_completion_metrics_service(
        user_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
) -> Optional[SeriesCompletionMetrics]:
    """
    Obtiene métricas de completación de series del usuario en un rango de fechas.

    Calcula para cada mes:
    - Series creadas en el mes
    - Series completadas (todos los juegos fueron jugados y completados)
    - Series parcialmente completadas (al menos un juego fue jugado)
    - Porcentaje de completación
    - Promedio de juegos jugados por serie
    - Total de analíticas registradas
    - Total de analíticas completadas

    Args:
        user_id: ID del usuario
        from_date: Fecha de inicio (YYYY-MM-DD). Si es None, usa últimos 30 días
        to_date: Fecha de fin (YYYY-MM-DD). Si es None, usa la fecha actual

    Returns:
        SeriesCompletionMetrics con desglose mensual

    Raises:
        HTTPException: Si hay error en la consulta
    """
    try:
        # Procesar fechas
        if not to_date:
            to_date = datetime.utcnow().strftime("%Y-%m-%d")
        if not from_date:
            to_datetime = datetime.strptime(to_date, "%Y-%m-%d")
            from_datetime = to_datetime - timedelta(days=30)
            from_date = from_datetime.strftime("%Y-%m-%d")

        from_datetime = datetime.strptime(from_date, "%Y-%m-%d")
        to_datetime = datetime.strptime(to_date, "%Y-%m-%d")

        # Obtener todas las series del usuario creadas en el período
        series_list = await db["game"].find({
            "created_by": user_id,
            "created_at": {
                "$gte": from_datetime,
                "$lte": to_datetime,
            }
        }).to_list(None)

        # Agrupar series por mes
        series_by_month = {}
        for series_db in series_list:
            month_key = series_db.get("created_at", datetime.utcnow()).strftime("%Y-%m")
            if month_key not in series_by_month:
                series_by_month[month_key] = []
            series_by_month[month_key].append(series_db)

        # Procesar cada mes
        monthly_metrics_list = []
        total_series_created = 0
        total_series_completed = 0
        total_series_partially_completed = 0
        total_tokens_charged = 0.0
        total_tokens_used = 0.0

        # Obtener registros de tokens para el período
        recharge_records = await db["star_recharge"].find({
            "user_id": user_id,
            "created_at": {
                "$gte": from_datetime,
                "$lte": to_datetime,
            }
        }).to_list(None)

        daily_records = await db["record_daily"].find({
            "user_id": user_id,
            "created_at": {
                "$gte": from_datetime,
                "$lte": to_datetime,
            }
        }).to_list(None)

        # Agrupar tokens por mes
        tokens_charged_by_month = {}
        tokens_used_by_month = {}

        for recharge in recharge_records:
            stars = recharge.get("stars_recharged", 0)
            total_tokens_charged += stars
            month_key = recharge.get("created_at", datetime.utcnow()).strftime("%Y-%m")
            if month_key not in tokens_charged_by_month:
                tokens_charged_by_month[month_key] = 0
            tokens_charged_by_month[month_key] += stars

        for record in daily_records:
            stars_used = record.get("stars_used", 0)
            total_tokens_used += stars_used
            month_key = record.get("created_at", datetime.utcnow()).strftime("%Y-%m")
            if month_key not in tokens_used_by_month:
                tokens_used_by_month[month_key] = 0
            tokens_used_by_month[month_key] += stars_used

        # Generar todos los meses en el rango
        all_months = []
        current_date = from_datetime
        while current_date <= to_datetime:
            month_str = current_date.strftime("%Y-%m")
            all_months.append(month_str)
            # Avanzar al siguiente mes
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        for month in all_months:
            series_in_month = series_by_month.get(month, [])

            if not series_in_month:
                # Mes sin series
                monthly_metrics_list.append(MonthlySeriesMetrics(
                    month=month,
                    series_created=0,
                    series_completed=0,
                    series_partially_completed=0,
                    completion_percentage=0.0,
                    avg_games_played_per_series=0.0,
                    total_analytics=0,
                    total_completed_analytics=0,
                ))
                continue

            # Procesar series del mes
            series_completed_count = 0
            series_partially_completed_count = 0
            total_games_played_in_month = 0
            total_analytics_in_month = 0
            total_completed_analytics_in_month = 0

            for game_db in series_in_month:
                game_id = str(game_db.get("_id"))

                # Obtener analíticas de este juego
                series_analytics = await db["analytics"].find({
                    "gameId": game_id
                }).to_list(None)

                total_analytics_in_month += len(series_analytics)
                completed_analytics = len([a for a in series_analytics if a.get("completed", False)])
                total_completed_analytics_in_month += completed_analytics

                # Contar juegos jugados
                games_played = len(set(a.get("gameId") for a in series_analytics if a.get("gameId")))
                total_games_played_in_month += games_played

                # Determinar si juego está completado (tiene al menos una analítica completada)
                has_completed_analytics = any(a.get("completed", False) for a in series_analytics)

                if has_completed_analytics:
                    series_completed_count += 1
                elif len(series_analytics) > 0:
                    series_partially_completed_count += 1

            # Calcular métricas del mes
            series_count = len(series_in_month)
            completion_percentage = (series_completed_count / series_count * 100) if series_count > 0 else 0.0
            avg_games_played = (total_games_played_in_month / series_count) if series_count > 0 else 0.0

            total_series_created += series_count
            total_series_completed += series_completed_count
            total_series_partially_completed += series_partially_completed_count

            monthly_metrics_list.append(MonthlySeriesMetrics(
                month=month,
                series_created=series_count,
                series_completed=series_completed_count,
                series_partially_completed=series_partially_completed_count,
                completion_percentage=round(completion_percentage, 2),
                avg_games_played_per_series=round(avg_games_played, 2),
                total_analytics=total_analytics_in_month,
                total_completed_analytics=total_completed_analytics_in_month,
                tokens_charged=tokens_charged_by_month.get(month, 0.0),
                tokens_used=tokens_used_by_month.get(month, 0.0),
            ))

        # Calcular resumen agregado
        overall_completion_percentage = (
            (total_series_completed / total_series_created * 100)
            if total_series_created > 0 else 0.0
        )

        tokens_balance = total_tokens_charged - total_tokens_used

        summary = {
            "total_series_created": total_series_created,
            "total_series_completed": total_series_completed,
            "total_series_partially_completed": total_series_partially_completed,
            "overall_completion_percentage": round(overall_completion_percentage, 2),
            "total_tokens_charged": round(total_tokens_charged, 2),
            "total_tokens_used": round(total_tokens_used, 2),
            "tokens_balance": round(tokens_balance, 2),
        }

        # Construir respuesta
        metrics = SeriesCompletionMetrics(
            range_applied={
                "from": from_date,
                "to": to_date,
            },
            monthly_metrics=monthly_metrics_list,
            summary=summary,
            generated_at=datetime.utcnow(),
        )

        return metrics

    except Exception as e:
        print(f"Error in get_series_completion_metrics_service: {str(e)}")
        # Retornar None en lugar de lanzar excepción
        return None


async def get_waitlist_users_export_service() -> List[dict]:
    """
    Obtiene todos los usuarios en lista de espera (is_preview = False).

    Retorna lista de usuarios con información para exportar a Excel:
    - username: Nombre del usuario
    - email: Correo del usuario
    - created_at: Fecha de creación

    Returns:
        List[dict]: Lista de usuarios en lista de espera

    Raises:
        HTTPException: Si hay error en la consulta
    """
    try:
        # Obtener usuarios donde is_preview = False (lista de espera)
        users_waitlist = await db["user"].find(
            {"is_preview": False}
        ).to_list(None)

        # Transformar datos para exportación
        result = []
        for user in users_waitlist:
            result.append({
                "username": user.get("username", ""),
                "email": user.get("email", ""),
                "created_at": user.get("created_at", datetime.utcnow()),
            })

        return result

    except Exception as e:
        print(f"Error in get_waitlist_users_export_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al obtener usuarios en lista de espera: {str(e)}"
        )


async def recharge_user_stars_service(user_id: str, stars_amount: float) -> dict:
    """
    Recarga estrellas a un usuario específico.

    Realiza las siguientes operaciones:
    1. Obtiene el usuario por ID
    2. Registra la recarga en colección 'star_recharge'
    3. Actualiza el saldo de estrellas del usuario
    4. Retorna información de la recarga

    Args:
        user_id: ID del usuario
        stars_amount: Cantidad de estrellas a recargar

    Returns:
        dict: Información de la recarga (before, after, etc)

    Raises:
        HTTPException: Si el usuario no existe o hay error
    """
    try:
        # Obtener usuario
        user = await db["user"].find_one({"_id": ObjectId(user_id)})

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )

        # Obtener saldo anterior
        stars_before = user.get("stars", 0)
        stars_after = stars_before + stars_amount

        # Crear registro de recarga
        recharge_record = {
            "user_id": user_id,
            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "stars_recharged": stars_amount,
            "stars_before": stars_before,
            "stars_after": stars_after,
            "created_at": datetime.utcnow(),
            "status": "completed"
        }

        # Insertar registro de recarga
        recharge_result = await db["star_recharge"].insert_one(recharge_record)

        # Actualizar saldo del usuario
        await db["user"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"stars": stars_after}}
        )

        # Retornar información de la recarga
        return {
            "recharge_id": str(recharge_result.inserted_id),
            "user_id": user_id,
            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "stars_recharged": stars_amount,
            "stars_before": stars_before,
            "stars_after": stars_after,
            "created_at": datetime.utcnow(),
            "status": "completed"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in recharge_user_stars_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al recargar estrellas: {str(e)}"
        )
