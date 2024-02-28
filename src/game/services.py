
from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from game.schemas import SchemaCreateGame
from game.schemas import SchemaPartialUpdateGame

from game.models import Game
from game.utils import get_history
from game.utils import get_synopsis

from utils import upload_image

from sqlalchemy import desc

def get_game_by_field(db: Session, field: str, value: str):
    return db.query(Game).filter(getattr(Game, field) == value).first()


def get_game_service(db: Session, game_id: str, user_id: str = None):
    game_db = get_game_by_field(db, 'id', game_id)
    if not game_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )
    # if game_db.user_id != user_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Unauthorized",
    #     )
    return game_db


def get_games_service(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Game).order_by(desc(Game.created_at)).offset(skip).limit(limit).all()


def create_game_service(db: Session, game: SchemaCreateGame, user_id: str):
    history = get_history(db=db, story_line=game.story_line)
    synopsys = get_synopsis(db=db, history=history)
    # characters_principals = get_characters_principals(db=db, history=history)

    try:
        db_game = Game(story_line=game.story_line,
                       history=str(history),
                       synopsis=synopsys['synopsis_generate'],
                       title=synopsys['title'],
                       prompt_image=synopsys['prompt_image'],
                       summary=synopsys['summary'],
                       user_id=user_id,
                       updated_by=user_id,
                       created_by=user_id,
                       image="",
                       image_background="",
                       attempts=3
                       )
        db.add(db_game)
        db.commit()
        db.refresh(db_game)

        return db_game

    except Exception as e:
        print(e)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not created",
        )


def update_partial_game_service(db: Session,
                                game_id: str,
                                game_update: SchemaPartialUpdateGame,
                                user_id: str
                                ):
    game_db = get_game_by_field(db, 'id', game_id)

    try:
        game_db.image = upload_image(url_image=game_update.image, file_name=f"{game_id}/covers/cover.jpg")
        game_db.updated_by = user_id
        db.commit()
        db.refresh(game_db)
        return game_db
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="has reached the maximum number of generation attempts",
        )


def subtract_attempts_game_service(db: Session, game_id: str):
    game_db = get_game_by_field(db, 'id', game_id)
    if game_db.attempts > 0:
        game_db.attempts = game_db.attempts - 1
        db.commit()
        db.refresh(game_db)
        return True
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Attempts not subtracted",
    )


def delete_game_service(db: Session, game_id: str):
    game_db = get_game_by_field(db, 'id', game_id)
    if not game_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )
    try:
        db.delete(game_db)
        db.commit()
        return True
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not deleted",
        )


def update_image_background_game_service(db: Session, game_id: str, image: str, identifier: str):
    game_db = get_game_by_field(db, 'id', game_id)
    if game_db:
        game_db.image_background = upload_image(url_image=image,
                                                file_name=f"{game_id}/background/background-{identifier}.jpg")

        db.commit()
        db.refresh(game_db)
        return game_db
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Game not found",
    )
