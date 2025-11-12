from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime

from auth.auth import auth
from auth.utils import auth_schema

from analytics.schemas import AnalyticCreate, AnalyticDB, AnalyticList
from analytics.services import (
    create_analytic_service,
    get_analytics_by_user_service,
    get_analytics_by_game_service,
    query_analytics_service,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post("/", response_model=AnalyticDB, status_code=status.HTTP_201_CREATED)
async def create_analytic(
    payload: AnalyticCreate,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        analytic = payload.dict()
        analytic["user_id"] = str(user_db.get("_id"))
        created = await create_analytic_service(analytic)
        # Normalize response
        return AnalyticDB(**{k: v for k, v in created.items() if k in AnalyticDB.__fields__})
    except Exception as e:
        print(f"Error create analytic: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/user/{user_id}", response_model=AnalyticList)
async def get_by_user(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        results, count = await get_analytics_by_user_service(user_id, skip=skip, limit=limit)
        return AnalyticList(results=[AnalyticDB(**r) for r in results], count=count)
    except Exception as e:
        print(f"Error get analytics by user: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/game/{game_id}", response_model=AnalyticList)
async def get_by_game(
    game_id: str,
    skip: int = 0,
    limit: int = 100,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        results, count = await get_analytics_by_game_service(game_id, skip=skip, limit=limit)
        return AnalyticList(results=[AnalyticDB(**r) for r in results], count=count)
    except Exception as e:
        print(f"Error get analytics by game: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/query", response_model=AnalyticList)
async def query_analytics(
    user_id: Optional[str] = None,
    game_id: Optional[str] = None,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    progress: Optional[int] = Query(None, ge=1, le=3),
    completed: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        results, count = await query_analytics_service(
            user_id=user_id,
            game_id=game_id,
            date_from=date_from,
            date_to=date_to,
            progress=progress,
            completed=completed,
            skip=skip,
            limit=limit,
        )
        return AnalyticList(results=[AnalyticDB(**r) for r in results], count=count)
    except Exception as e:
        print(f"Error query analytics: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

