from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status
import asyncio
import time
import logging

from game_progress.models import GameProgress

from game_progress.schemas import SchemaCreateGameProgress
from game_progress.schemas import SchemaRetrieveGameProgress
from game_progress.schemas import SchemaListGameProgress
from game_progress.schemas import SchemaPartialUpdateGameProgress

logger = logging.getLogger(__name__)


def get_game_progress_by_field(db: Session, field: str, value: str):
    """
    Get a game_progress by a field.
    """
    game_progress = db.query(GameProgress).filter(getattr(GameProgress, field) == value).first()
    if not game_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GameProgress with {field} {value} not found",
        )
    return game_progress


def get_game_progresses_service(
    db: Session, skip: int = 0, limit: int = 100, user_id: str = None, game_id: str = None
):
    """
    Get a list of game_progresses.
    """
    game_progresses = db.query(GameProgress)
    if game_id:
        game_progresses = game_progresses.filter(GameProgress.game_id == game_id)
    game_progresses = (
        game_progresses.filter(GameProgress.user_id == user_id).offset(skip).limit(limit).all()
    )
    return SchemaListGameProgress(results=game_progresses, count=len(game_progresses))


def get_game_progress_service(db: Session, game_progress_id: str):
    """
    Get a game_progress.
    """
    game_progress = get_game_progress_by_field(db, "id", game_progress_id)
    return game_progress


def create_game_progress_service(db: Session, schema: SchemaCreateGameProgress, user_id: str):
    """
    Create a game_progress.
    """
    try:
        game_progress = GameProgress(**schema.dict())
        game_progress.user_id = user_id
        game_progress.created_by = user_id
        game_progress.updated_by = user_id
        db.add(game_progress)
        db.commit()
        db.refresh(game_progress)
        return game_progress
    except Exception as e:
        logger.error(f"Error creating game progress: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error creating game progress"
        )


def partial_update_game_progress_service(
    db: Session, game_progress_id: str, schema: SchemaPartialUpdateGameProgress
):
    """
    Partially update a game_progress with 10-second delay.
    """

    game_progress = get_game_progress_by_field(db, "id", game_progress_id)
    try:
        for field, value in schema:
            if value is not None:
                setattr(game_progress, field, value)
        db.commit()
        db.refresh(game_progress)
        # Delay de 10 segundos después del update
        time.sleep(10)
        return game_progress
    except Exception as e:
        logger.error(f"Error updating game_progress {game_progress_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating game_progress {game_progress_id}",
        )
