from datetime import datetime
from fastapi import HTTPException
from fastapi import status

from core.database import db

from state_game.models import StateGame


async def create_state_game(game_id: str, order: int, created_by: str) -> dict:
    state_game = StateGame(
        game_id=game_id,
        order=order,
        created_at=datetime.utcnow(),
        created_by=created_by,
        updated_at=datetime.utcnow(),
        updated_by=created_by
    ).dict()

    result = await db["state_game"].insert_one(state_game)
    state_game["_id"] = str(result.inserted_id)

    return state_game


async def get_state_game_by_game_id(game_id: str) -> dict:
    state_game = await db["state_game"].find_one({"game_id": game_id})
    if state_game:
        state_game["_id"] = str(state_game["_id"])
        return state_game

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="StateGame not found"
    )