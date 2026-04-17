"""
Services para Dashboard de Usuarios (_dash)

Proporciona endpoints agregados que devuelven toda la información necesaria
para construir un dashboard en una sola petición.
"""

from datetime import datetime, timedelta
from typing import Optional, List
import asyncio
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


async def _build_user_kpis(user_db: dict, games_list: Optional[List[dict]] = None) -> KPIs:
    """
    Construye las tarjetas de KPI del usuario.

    Args:
        user_db: Documento del usuario desde MongoDB
        games_list: Lista de games del usuario (para reutilizar datos)

    Returns:
        KPIs: Objeto con todos los KPIs
    """
    stars = user_db.get("stars", 0)
    is_active = user_db.get("is_active", False)
    user_id = str(user_db.get("_id"))

    # Obtener IDs de games creados por el usuario (si no se proporcionó)
    if games_list is None:
        games_list = await db["game"].find({"created_by": user_id}).to_list(None)

    series_count = len(games_list)
    game_ids = [str(g.get("_id")) for g in games_list]

    # Contar analytics de esos games y tokens cargados en paralelo
    analytics_count_task = (
        db["analytics"].count_documents({"gameId": {"$in": game_ids}})
        if game_ids else asyncio.sleep(0)
    )

    tokens_task = db["star_recharge"].aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$stars_recharged"}}}
    ]).to_list(None)

    # Ejecutar en paralelo
    if game_ids:
        analytics_result = await asyncio.gather(analytics_count_task, tokens_task)
        analytics_count = analytics_result[0]
        tokens_records = analytics_result[1]
    else:
        tokens_records = await tokens_task
        analytics_count = 0

    # Extraer tokens cargados del agregado
    tokens_charged = 0.0
    if tokens_records and tokens_records[0]:
        tokens_charged = float(tokens_records[0].get("total", 0))

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
        game_ids: Optional[List[str]] = None,
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
        game_ids: Lista de game_ids del usuario (para reutilizar datos)
        group_by: 'day', 'week' o 'month'

    Returns:
        Lista de series de tiempo o None si no hay datos
    """
    try:
        from_datetime = datetime.strptime(from_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
        to_datetime = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

        # Obtener games del usuario si no se proporciona
        if game_ids is None:
            games_list = await db["game"].find({"created_by": user_id}).to_list(None)
            game_ids = [str(g.get("_id")) for g in games_list]

        # Ejecutar todas las agregaciones en paralelo
        series_agg_task = db["game"].aggregate([
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

        analytics_agg_task = (
            db["analytics"].aggregate([
                {
                    "$match": {
                        "$or": [
                            {"gameId": {"$in": game_ids}},
                            {"game_id": {"$in": game_ids}}
                        ],
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
            if game_ids else asyncio.sleep(0)
        )

        tokens_charged_agg_task = db["star_recharge"].aggregate([
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

        tokens_used_agg_task = db["game"].aggregate([
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

        # Ejecutar todas las agregaciones en paralelo
        results = await asyncio.gather(
            series_agg_task,
            analytics_agg_task,
            tokens_charged_agg_task,
            tokens_used_agg_task,
        )

        series_by_month = results[0]
        analytics_result = results[1] if isinstance(results[1], list) else []
        tokens_charged_result = results[2]
        tokens_used_result = results[3]

        # Convertir resultados a diccionarios
        series_dict = {item["_id"]: item["count"] for item in series_by_month}
        analytics_dict = {item["_id"]: item["count"] for item in analytics_result}
        tokens_charged_dict = {item["_id"]: item["total"] for item in tokens_charged_result}
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


async def _build_user_breakdowns(user_db: dict, games_list: Optional[List[dict]] = None) -> Optional[Breakdowns]:
    """
    Construye los desgloces (breakdowns) del usuario.

    Args:
        user_db: Documento del usuario desde MongoDB
        games_list: Lista de games del usuario (para reutilizar datos)

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

        # Reutilizar games_list si se proporciona, si no obtenerla
        if games_list is None:
            games_list = await db["game"].find({"created_by": str(user_db.get("_id"))}).to_list(None)

        games_created_count = len(games_list)

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
                total=games_created_count,
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

    - Obtiene todas las series del usuario
    - Obtiene los juegos de cada serie
    - Cuenta analíticas por juego
    - Devuelve series ordenadas por cantidad de analíticas

    Args:
        user_id: ID del usuario

    Returns:
        Lista de series con sus juegos y analíticas o None si no hay datos
    """
    try:
        # Agregación: series con sus juegos y analíticas
        series_data = await db["series"].aggregate([
            {
                "$match": {"created_by": user_id}
            },
            {
                "$lookup": {
                    "from": "game",
                    "let": {"serie_id": {"$toString": "$_id"}},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {"$eq": ["$serie_id", "$$serie_id"]}
                            }
                        }
                    ],
                    "as": "games"
                }
            },
            {
                "$lookup": {
                    "from": "analytics",
                    "let": {"game_ids": {"$map": {"input": "$games", "as": "g", "in": {"$toString": "$$g._id"}}}},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$or": [
                                        {"$in": ["$gameId", "$$game_ids"]},
                                        {"$in": ["$game_id", "$$game_ids"]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "all_analytics"
                }
            },
            {
                "$addFields": {
                    "serie_id": {"$toString": "$_id"},
                    "total_analytics": {"$size": "$all_analytics"},
                    "games_count": {"$size": "$games"},
                    "hidden_games_count": {
                        "$size": {
                            "$filter": {
                                "input": "$games",
                                "as": "g",
                                "cond": {"$eq": ["$$g.is_hidden", True]}
                            }
                        }
                    }
                }
            },
            {
                "$sort": {"total_analytics": -1}
            },
            {
                "$project": {
                    "serie_id": 1,
                    "title": 1,
                    "image": 1,
                    "is_active": 1,
                    "is_published": 1,
                    "publish_type": 1,
                    "published_at": 1,
                    "created_at": 1,
                    "total_analytics": 1,
                    "games_count": 1,
                    "hidden_games_count": 1,
                    "games": {
                        "$map": {
                            "input": "$games",
                            "as": "game",
                            "in": {
                                "game_id": {"$toString": "$$game._id"},
                                "title": "$$game.title",
                                "is_hidden": "$$game.is_hidden",
                                "analytics_count": {
                                    "$size": {
                                        "$filter": {
                                            "input": "$all_analytics",
                                            "as": "a",
                                            "cond": {
                                                "$or": [
                                                    {"$eq": ["$$a.gameId", {"$toString": "$$game._id"}]},
                                                    {"$eq": ["$$a.game_id", {"$toString": "$$game._id"}]}
                                                ]
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        ]).to_list(None)

        if not series_data:
            return None

        # Construir objetos SeriesData con juegos poblados
        result = []
        for serie_doc in series_data:
            games_list = serie_doc.get("games", [])
            top_game = games_list[0] if games_list else None

            serie_obj = SeriesData(
                series_id=serie_doc.get("serie_id"),
                is_active=serie_doc.get("is_active", True),
                is_published=serie_doc.get("is_published", False),
                publish_type=serie_doc.get("publish_type", "private"),
                created_at=serie_doc.get("created_at", datetime.utcnow()),
                games_count=serie_doc.get("games_count", 0),
                total_analytics=serie_doc.get("total_analytics", 0),
                top_game=GameInfoForSeries(
                    game_id=top_game.get("game_id") if top_game else "",
                    title=top_game.get("title") if top_game else "",
                    analytics_count=top_game.get("analytics_count", 0) if top_game else 0,
                    games_in_series=[
                        {
                            "game_id": g.get("game_id"),
                            "title": g.get("title"),
                            "analytics_count": g.get("analytics_count", 0)
                        }
                        for g in games_list
                    ]
                )
            )
            result.append(serie_obj)

        return result if result else None

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

        # Obtener información del team si el usuario tiene plan_type="team"
        team_members = None
        team_role = user_db.get("team_role")
        is_team_owner = user_db.get("is_team_owner", False)
        plan_type = user_db.get("plan_type", "individual")
        
        if plan_type == "team" and user_db.get("team_id"):
            try:
                team_db = await db["team"].find_one({"_id": ObjectId(user_db.get("team_id"))})
                if team_db and team_db.get("members"):
                    # Obtener información completa de los miembros
                    team_members = []
                    for member in team_db.get("members", []):
                        member_user = await db["user"].find_one({"_id": ObjectId(member.get("user_id"))})
                        if member_user:
                            team_members.append({
                                "user_id": str(member_user.get("_id")),
                                "username": member_user.get("username", ""),
                                "email": member_user.get("email", ""),
                                "role": member.get("role"),
                                "joined_at": member.get("joined_at")
                            })
            except Exception as e:
                print(f"Error getting team info: {str(e)}")
                # Continuar sin información del team

        # Construir perfil del usuario
        user_profile = UserProfileDash(
            user_id=str(user_db.get("_id")),
            username=user_db.get("username", ""),
            email=user_db.get("email", ""),
            is_active=user_db.get("is_active", False),
            plan_type=plan_type,
            team_role=team_role,
            is_team_owner=is_team_owner,
            team_members=team_members,
        )

        # OPTIMIZACIÓN: Obtener solo IDs de games con agregación (sin cargar documentos completos)
        user_id_str = str(user_db.get("_id"))
        games_id_agg = await db["game"].aggregate([
            {"$match": {"created_by": user_id_str}},
            {"$project": {"_id": 1}}
        ]).to_list(None)

        game_ids = [str(g.get("_id")) for g in games_id_agg]
        games_list = games_id_agg  # Reutilizar para _build_user_kpis

        # Ejecutar todas las operaciones en paralelo
        kpis_task = _build_user_kpis(user_db, games_list=games_list)
        timeseries_task = _build_user_timeseries(user_id_str, from_date, to_date, game_ids=game_ids)
        series_data_task = _get_user_series_with_analytics(user_id_str)

        # Aguardar todas las tareas en paralelo
        (kpis, timeseries, series_data) = await asyncio.gather(
            kpis_task,
            timeseries_task,
            series_data_task
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
            series=series_data,
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
            count_analytics=await db["analytics"].count_documents({}),
            charged_tokens=0.0,
            used_tokens=0.0,
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
        search: Optional[str] = None,
        is_preview: Optional[bool] = None,
) -> dict:
    """
    Obtiene un listado simplificado de usuarios: individual y owners de teams.

    **Usuarios mostrados:**
    - Usuarios con plan "individual"
    - Usuarios que son owners de teams (is_team_owner = true)

    **Usuarios excluidos:**
    - Miembros de teams que NO son owners (team members regulares)

    Información devuelta por usuario:
    - id: ID del usuario
    - nombre: Nombre de usuario (username)
    - correo: Correo electrónico
    - plan: Plan del usuario (individual o team)
    - rol_team: Rol del usuario en el team (owner, admin, creator, viewer)
    - es_dueño_team: Si el usuario es dueño del team
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
        search: Búsqueda parcial por nombre de usuario o email (case-insensitive)
        is_preview: Filtrar por estado de preview (True/False). Si es None, devuelve todos

    Returns:
        Dict con lista de usuarios simplificados y metadata de paginación

    Raises:
        HTTPException: Si hay error en la consulta
    """
    try:
        # OPTIMIZACIÓN: Una sola agregación en lugar de loops con queries
        # Obtener estadísticas de usuarios con games y analytics en una pasada

        # Construir pipeline de agregación
        match_stage = {}

        # Agregar filtro de búsqueda si existe
        if search:
            match_stage["$or"] = [
                {"username": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}}
            ]

        # Agregar filtro de is_preview si existe
        if is_preview is not None:
            match_stage["is_preview"] = is_preview

        # Construir el pipeline
        pipeline = []

        # Agregar match stage solo si hay filtros
        if match_stage:
            pipeline.append({"$match": match_stage})

        # Continuar con lookups y proyecciones
        pipeline.extend([
            {
                "$lookup": {
                    "from": "game",
                    "let": {"user_id": {"$toString": "$_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$created_by", "$$user_id"]}}}
                    ],
                    "as": "games"
                }
            },
            {
                "$lookup": {
                    "from": "analytics",
                    "let": {"game_ids": {"$map": {"input": "$games", "as": "g", "in": {"$toString": "$$g._id"}}}},
                    "pipeline": [
                        {"$match": {"$expr": {"$in": ["$gameId", "$$game_ids"]}}}
                    ],
                    "as": "analytics"
                }
            },
            {
                "$lookup": {
                    "from": "team",
                    "let": {"team_id": "$team_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", {"$toObjectId": "$$team_id"}]}}}
                    ],
                    "as": "team_info"
                }
            },
            {
                "$addFields": {
                    "user_id": {"$toString": "$_id"},
                    "games_created": {"$size": "$games"},
                    "views": {"$size": "$analytics"},
                    "team_owner_id": {
                        "$cond": [
                            {"$gt": [{"$size": "$team_info"}, 0]},
                            {"$arrayElemAt": ["$team_info.owner_id", 0]},
                            None
                        ]
                    },
                    "is_team_owner_calculated": {
                        "$cond": [
                            {"$eq": [{"$arrayElemAt": ["$team_info.owner_id", 0]}, {"$toString": "$_id"}]},
                            True,
                            False
                        ]
                    }
                }
            },
            {
                "$project": {
                    "user_id": 1,
                    "username": 1,
                    "email": 1,
                    "created_at": 1,
                    "stars": 1,
                    "games_created": 1,
                    "views": 1,
                    "is_preview": 1,
                    "plan_type": 1,
                    "team_role": 1,
                    "is_team_owner": "$is_team_owner_calculated"
                }
            },
            {
                "$match": {
                    "$or": [
                        {"plan_type": "individual"},
                        {"plan_type": {"$exists": False}},
                        {"plan_type": None},
                        {"is_team_owner": True}
                    ]
                }
            }
        ])

        users_agg = await db["user"].aggregate(pipeline).to_list(None)

        total_users = len(users_agg)

        # Construir lista de usuarios simplificados
        users_detailed = []
        for user in users_agg:
            games_created = user.get("games_created", 0)
            stars_used = games_created * 10

            user_detail = {
                "user_id": user.get("user_id"),
                "username": user.get("username", ""),
                "email": user.get("email", ""),
                "created_at": user.get("created_at", datetime.utcnow()),
                "stars": float(user.get("stars", 0)),
                "games_created": games_created,
                "stars_used": stars_used,
                "views": user.get("views", 0),
                "is_preview": user.get("is_preview", False),
                "plan_type": user.get("plan_type", "individual"),
                "team_role": user.get("team_role"),
                "is_team_owner": user.get("is_team_owner", False),
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
            "search": search,
            "is_preview": is_preview,
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
        users_creators = await db["game"].aggregate([
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
        series_by_month = await db["game"].aggregate([
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
        users_by_month = await db["game"].aggregate([
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

        # OPTIMIZACIÓN: Usar agregación única con $lookup en lugar de loops
        # Obtener series con analíticas vinculadas en una sola consulta
        series_with_analytics = await db["game"].aggregate([
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
                "$lookup": {
                    "from": "analytics",
                    "localField": "_id",
                    "foreignField": "gameId",
                    "as": "analytics"
                }
            },
            {
                "$addFields": {
                    "month": {
                        "$dateToString": {
                            "format": "%Y-%m",
                            "date": "$created_at"
                        }
                    },
                    "analytics_count": {"$size": "$analytics"},
                    "completed_analytics_count": {
                        "$size": {
                            "$filter": {
                                "input": "$analytics",
                                "as": "a",
                                "cond": {"$eq": ["$$a.completed", True]}
                            }
                        }
                    },
                    "has_completed_analytics": {
                        "$gt": [
                            {
                                "$size": {
                                    "$filter": {
                                        "input": "$analytics",
                                        "as": "a",
                                        "cond": {"$eq": ["$$a.completed", True]}
                                    }
                                }
                            },
                            0
                        ]
                    },
                    "has_any_analytics": {"$gt": ["$analytics_count", 0]}
                }
            }
        ]).to_list(None)

        # Agrupar por mes
        series_by_month = {}
        for game_doc in series_with_analytics:
            month = game_doc["month"]
            if month not in series_by_month:
                series_by_month[month] = {
                    "games": [],
                    "total_analytics": 0,
                    "total_completed_analytics": 0,
                    "completed_count": 0,
                    "partially_completed_count": 0,
                }

            series_by_month[month]["games"].append(game_doc)
            series_by_month[month]["total_analytics"] += game_doc["analytics_count"]
            series_by_month[month]["total_completed_analytics"] += game_doc["completed_analytics_count"]

            if game_doc["has_completed_analytics"]:
                series_by_month[month]["completed_count"] += 1
            elif game_doc["has_any_analytics"]:
                series_by_month[month]["partially_completed_count"] += 1

        # Procesar tokens en paralelo
        tokens_charged_agg_task = db["star_recharge"].aggregate([
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
            }
        ]).to_list(None)

        tokens_used_agg_task = db["record_daily"].aggregate([
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
                    "total": {"$sum": "$stars_used"}
                }
            }
        ]).to_list(None)

        # Ejecutar agregaciones de tokens en paralelo
        tokens_results = await asyncio.gather(
            tokens_charged_agg_task,
            tokens_used_agg_task,
        )

        tokens_charged_records = tokens_results[0]
        tokens_used_records = tokens_results[1]

        # Convertir a diccionarios
        tokens_charged_by_month = {item["_id"]: item["total"] for item in tokens_charged_records}
        tokens_used_by_month = {item["_id"]: item["total"] for item in tokens_used_records}

        # Calcular totales
        total_tokens_charged = sum(tokens_charged_by_month.values())
        total_tokens_used = sum(tokens_used_by_month.values())
        total_series_created = sum(len(data["games"]) for data in series_by_month.values())
        total_series_completed = sum(data["completed_count"] for data in series_by_month.values())
        total_series_partially_completed = sum(data["partially_completed_count"] for data in series_by_month.values())

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

        # Construir resultados por mes
        monthly_metrics_list = []
        for month in all_months:
            month_data = series_by_month.get(month, {})

            if not month_data or len(month_data.get("games", [])) == 0:
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

            # Calcular métricas del mes
            series_count = len(month_data["games"])
            completed_count = month_data["completed_count"]
            partially_completed_count = month_data["partially_completed_count"]
            total_analytics = month_data["total_analytics"]
            total_completed_analytics = month_data["total_completed_analytics"]

            completion_percentage = (completed_count / series_count * 100) if series_count > 0 else 0.0
            avg_games_played = (series_count / series_count) if series_count > 0 else 0.0

            monthly_metrics_list.append(MonthlySeriesMetrics(
                month=month,
                series_created=series_count,
                series_completed=completed_count,
                series_partially_completed=partially_completed_count,
                completion_percentage=round(completion_percentage, 2),
                avg_games_played_per_series=round(avg_games_played, 2),
                total_analytics=total_analytics,
                total_completed_analytics=total_completed_analytics,
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
    - plan_type: Plan del usuario (individual o team)
    - team_role: Rol del usuario en el team (si aplica)
    - is_team_owner: Si el usuario es dueño del team
    - created_at: Fecha de creación

    Returns:
        List[dict]: Lista de usuarios en lista de espera

    Raises:
        HTTPException: Si hay error en la consulta
    """
    try:
        # Usar agregación para obtener usuarios con información de team
        pipeline = [
            {"$match": {"is_preview": False}},
            {
                "$lookup": {
                    "from": "team",
                    "let": {"team_id": "$team_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", {"$toObjectId": "$$team_id"}]}}}
                    ],
                    "as": "team_info"
                }
            },
            {
                "$addFields": {
                    "is_team_owner_calculated": {
                        "$cond": [
                            {"$eq": [{"$arrayElemAt": ["$team_info.owner_id", 0]}, {"$toString": "$_id"}]},
                            True,
                            False
                        ]
                    }
                }
            },
            {
                "$project": {
                    "username": 1,
                    "email": 1,
                    "plan_type": 1,
                    "team_role": 1,
                    "is_team_owner": "$is_team_owner_calculated",
                    "created_at": 1
                }
            }
        ]

        users_waitlist = await db["user"].aggregate(pipeline).to_list(None)

        # Transformar datos para exportación
        result = []
        for user in users_waitlist:
            result.append({
                "username": user.get("username", ""),
                "email": user.get("email", ""),
                "plan_type": user.get("plan_type", "individual"),
                "team_role": user.get("team_role"),
                "is_team_owner": user.get("is_team_owner", False),
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


async def activate_user_service(user_id: str) -> dict:
    """
    Activa un usuario cambiando su estado de is_preview a True.

    Args:
        user_id: ID del usuario a activar

    Returns:
        Dict con información del usuario activado

    Raises:
        HTTPException: Si el usuario no existe o hay error en la actualización
    """
    try:
        # Validar que el user_id sea un ObjectId válido
        if not user_id or len(user_id) != 24:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de usuario inválido"
            )

        # Obtener usuario actual
        user = await db["user"].find_one({"_id": ObjectId(user_id)})

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )

        # Verificar si ya está activado
        if user.get("is_preview", False):
            return {
                "user_id": user_id,
                "username": user.get("username", ""),
                "email": user.get("email", ""),
                "is_preview": True,
                "message": "El usuario ya estaba activado",
                "activated_at": datetime.utcnow()
            }

        # Actualizar is_preview a True
        update_result = await db["user"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_preview": True, "activated_at": datetime.utcnow()}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo actualizar el usuario"
            )

        # Obtener usuario actualizado
        updated_user = await db["user"].find_one({"_id": ObjectId(user_id)})

        return {
            "user_id": user_id,
            "username": updated_user.get("username", ""),
            "email": updated_user.get("email", ""),
            "is_preview": updated_user.get("is_preview", False),
            "created_at": updated_user.get("created_at"),
            "activated_at": updated_user.get("activated_at"),
            "message": "Usuario activado exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in activate_user_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al activar usuario: {str(e)}"
        )


async def change_user_plan_type_service(user_id: str, new_plan_type: str) -> dict:
    """
    Cambia el tipo de plan del usuario entre 'individual' y 'team'.
    
    Cuando cambia de individual a team:
    - Crea un nuevo team con el nombre del usuario
    - Agrega al usuario como único miembro con rol 'owner'
    - Actualiza el plan_type del usuario a 'team'
    - Asigna el team_id al usuario
    
    Cuando cambia de team a individual:
    - Desactiva el team actual del usuario
    - Actualiza el plan_type del usuario a 'individual'
    - Limpia team_id, team_role e is_team_owner del usuario
    
    Args:
        user_id: ID del usuario
        new_plan_type: Tipo de plan deseado ('individual' o 'team')
    
    Returns:
        dict: Información actualizada del usuario
    
    Raises:
        HTTPException: Si hay error en la operación
    """
    try:
        # Validar que el nuevo plan sea válido
        if new_plan_type not in ["individual", "team"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El tipo de plan debe ser 'individual' o 'team'"
            )
        
        # Obtener usuario actual
        user_db = await db["user"].find_one({"_id": ObjectId(user_id)})
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )
        
        current_plan = user_db.get("plan_type", "individual")
        
        # Si ya tiene el mismo plan, no hacer nada
        if current_plan == new_plan_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario ya tiene el plan '{new_plan_type}'"
            )
        
        # ============================================
        # CASO 1: Cambio de individual a team
        # ============================================
        if current_plan == "individual" and new_plan_type == "team":
            from team.models import Team, TeamMember
            
            # Crear nuevo team con el nombre del usuario
            team_name = user_db.get("username", f"Team {user_id}")
            new_team = Team(
                name=team_name,
                description="",
                owner_id=user_id,
                members=[
                    TeamMember(
                        user_id=user_id,
                        role="owner"
                    )
                ],
                is_active=True,
                created_by=user_id,
                updated_by=user_id
            )
            
            # Insertar team en base de datos
            team_result = await db["team"].insert_one(new_team.dict())
            team_id = str(team_result.inserted_id)
            
            # Actualizar usuario con nuevo plan
            update_result = await db["user"].update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "plan_type": "team",
                        "team_id": team_id,
                        "team_role": "owner",
                        "is_team_owner": True,
                        "updated_at": datetime.utcnow(),
                        "updated_by": "system"
                    }
                }
            )
            
            if update_result.modified_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se pudo actualizar el usuario"
                )
            
            # Obtener usuario actualizado
            updated_user = await db["user"].find_one({"_id": ObjectId(user_id)})
            
            return {
                "user_id": str(updated_user.get("_id")),
                "username": updated_user.get("username", ""),
                "email": updated_user.get("email", ""),
                "plan_type": updated_user.get("plan_type"),
                "team_id": updated_user.get("team_id"),
                "team_role": updated_user.get("team_role"),
                "is_team_owner": updated_user.get("is_team_owner"),
                "created_at": updated_user.get("created_at"),
                "updated_at": updated_user.get("updated_at"),
                "message": f"Plan actualizado a 'team'. Team '{team_name}' creado exitosamente"
            }
        
        # ============================================
        # CASO 2: Cambio de team a individual
        # ============================================
        elif current_plan == "team" and new_plan_type == "individual":
            team_id = user_db.get("team_id")
            
            if not team_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Usuario con plan 'team' pero sin team_id asignado"
                )
            
            # Desactivar el team actual
            await db["team"].update_one(
                {"_id": ObjectId(team_id)},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow(),
                        "updated_by": "system"
                    }
                }
            )
            
            # Actualizar usuario a plan individual
            update_result = await db["user"].update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "plan_type": "individual",
                        "team_id": None,
                        "team_role": None,
                        "is_team_owner": False,
                        "updated_at": datetime.utcnow(),
                        "updated_by": "system"
                    }
                }
            )
            
            if update_result.modified_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se pudo actualizar el usuario"
                )
            
            # Obtener usuario actualizado
            updated_user = await db["user"].find_one({"_id": ObjectId(user_id)})
            
            return {
                "user_id": str(updated_user.get("_id")),
                "username": updated_user.get("username", ""),
                "email": updated_user.get("email", ""),
                "plan_type": updated_user.get("plan_type"),
                "team_id": updated_user.get("team_id"),
                "team_role": updated_user.get("team_role"),
                "is_team_owner": updated_user.get("is_team_owner"),
                "created_at": updated_user.get("created_at"),
                "updated_at": updated_user.get("updated_at"),
                "message": f"Plan actualizado a 'individual'. Team desactivado exitosamente"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in change_user_plan_type_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cambiar el tipo de plan: {str(e)}"
        )

