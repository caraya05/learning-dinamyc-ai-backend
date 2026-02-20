from typing import List, Tuple, Optional
from datetime import datetime, timezone

from core.database import db


async def create_analytic_service(analytic_data: dict) -> dict:
    """Inserta un registro de analítica en la colección `analytics`.
    Se espera analytic_data contenga los campos requeridos y el `user_id`.
    """
    analytic_data["created_at"] = datetime.now(timezone.utc)
    result = await db["analytics"].insert_one(analytic_data)
    analytic = await db["analytics"].find_one({"_id": result.inserted_id})
    # Normaliza _id a string
    analytic["_id"] = str(analytic["_id"])
    return analytic


async def get_analytics_by_user_service(user_id: str, skip: int = 0, limit: int = 100) -> Tuple[List[dict], int]:
    query = {"user_id": str(user_id)}
    cursor = db["analytics"].find(query).skip(skip).limit(limit).sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    count = await db["analytics"].count_documents(query)
    return results, count


async def get_analytics_by_game_service(game_id: str, skip: int = 0, limit: int = 100) -> Tuple[List[dict], int]:
    query = {"gameId": str(game_id)}
    cursor = db["analytics"].find(query).skip(skip).limit(limit).sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    count = await db["analytics"].count_documents(query)
    return results, count


async def query_analytics_service(
    user_id: Optional[str] = None,
    game_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    progress: Optional[int] = None,
    completed: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
):
    query = {}
    if user_id:
        query["user_id"] = str(user_id)
    if game_id:
        query["gameId"] = str(game_id)
    if date_from or date_to:
        query["created_at"] = {}
        if date_from:
            query["created_at"]["$gte"] = date_from
        if date_to:
            query["created_at"]["$lte"] = date_to
    if progress is not None:
        query["progress"] = progress
    if completed is not None:
        query["completed"] = completed

    cursor = db["analytics"].find(query).skip(skip).limit(limit).sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    count = await db["analytics"].count_documents(query)
    return results, count


__all__ = [
    "create_analytic_service",
    "get_analytics_by_user_service",
    "get_analytics_by_game_service",
    "query_analytics_service",
]

