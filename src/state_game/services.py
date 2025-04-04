from datetime import datetime

from bson import ObjectId
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
        updated_by=created_by,
    ).dict()

    result = await db["state_game"].insert_one(state_game)
    state_game["_id"] = str(result.inserted_id)

    # all_state_game_elements = await db["state_glic"].find({"data.game_id": game_id, "order": 1 }).to_list(length=1000)
    #
    # if len(all_state_game_elements) > 0:
    #     for i in range(len(all_state_game_elements)):
    #         state_game_element = all_state_game_elements[i]
    #         state_game_element["state"] = str(result.inserted_id)
    #         state_game_element["order"] = order
    #         state_game_element["updated_at"] = datetime.utcnow()
    #         state_game_element["updated_by"] = created_by
    #         await db["state_game"].insert_one(state_game_element)

    return state_game


async def get_state_game_by_game_id(game_id: str) -> dict:
    state_game = await db["state_game"].find_one({"game_id": game_id, "order": 1})
    if state_game:
        state_game["_id"] = str(state_game["_id"])
        return state_game

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StateGame not found")


async def get_state_game_by_element_id(element_id: str) -> dict:
    state_game = await db["state_game"].find_one({"element_id": element_id, "order": 1})
    if state_game:
        state_game["_id"] = str(state_game["_id"])
        return state_game
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StateGame not found")


async def get_state_game_by_id(state_game_id: str) -> dict:
    state_game = await db["state_game"].find_one({"_id": ObjectId(state_game_id)})
    if state_game:
        state_game["_id"] = str(state_game["_id"])
        return state_game

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StateGame not found")


async def get_states_game_by_game_id(game_id: str) -> list:
    states_game = await db["state_game"].find({"game_id": game_id}).to_list(length=1000)
    for state_game in states_game:
        state_game["_id"] = str(state_game["_id"])
        location_state_game = await db["event"].find_one(
            {"state_game_end": state_game["_id"]}, sort=[("created_at", -1)]
        )
        if location_state_game:
            state_game["location_id"] = location_state_game["location_state_game_end"]
        else:
            state_game["location_id"] = None
    return states_game


async def get_order_new_state_game(game_id: str) -> int:
    state_game = await db["state_game"].find_one({"game_id": game_id}, sort=[("order", -1)])
    if state_game:
        return state_game["order"] + 1
    return 1
