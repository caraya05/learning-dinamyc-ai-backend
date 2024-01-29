from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from game_progress.models import GameProgress

from game_progress.schemas import SchemaCreateGameProgress
from game_progress.schemas import SchemaRetrieveGameProgress
from game_progress.schemas import SchemaListGameProgress
from game_progress.schemas import SchemaPartialUpdateGameProgress


def get_game_progress_by_field(db: Session, field: str, value: str):
    """
    Get a game_progress by a field.
    """
    game_progress = db.query(GameProgress).filter(getattr(GameProgress, field) == value).first()
    if not game_progress:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"GameProgress with {field} {value} not found")
    return game_progress


def get_game_progresses_service(db: Session, skip: int = 0, limit: int = 100):
    """
    Get a list of game_progresses.
    """
    game_progresses = db.query(GameProgress).offset(skip).limit(limit).all()
    return SchemaListGameProgress(results=game_progresses, count=len(game_progresses))


def get_game_progress_service(db: Session, game_progress_id: str):
    """
    Get a game_progress.
    """
    game_progress = get_game_progress_by_field(db, "id", game_progress_id)
    return SchemaRetrieveGameProgress.from_orm(game_progress)


def create_game_progress_service(db: Session, schema: SchemaCreateGameProgress):
    """
    Create a game_progress.
    """
    game_progress = GameProgress(**schema.dict())
    db.add(game_progress)
    db.commit()
    db.refresh(game_progress)
    return SchemaRetrieveGameProgress.from_orm(game_progress)


def partial_update_game_progress_service(db: Session, game_progress_id: str, schema: SchemaPartialUpdateGameProgress):
    """
    Partially update a game_progress.
    """
    game_progress = get_game_progress_by_field(db, "id", game_progress_id)
    for field, value in schema:
        setattr(game_progress, field, value)
    db.commit()
    db.refresh(game_progress)
    return SchemaRetrieveGameProgress.from_orm(game_progress)

