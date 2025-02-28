from datetime import datetime

from bson import ObjectId

from core.database import db
from game.schemas_admin import SchemaUpdateGame


async def get_games_service_admin(skip: int = 0, limit: int = 100):
    games_db = await db["game"].find().to_list(None)
    for i in range(len(games_db)):
        # if games_db[i]["characters_id"]:
        #     for j in range(len(games_db[i]["characters_id"])):
        #         await db["character"].update_one({"_id": ObjectId(games_db[i]["characters_id"][j])},
        #                                          {"$set": {"game_id": str(games_db[i]["_id"])}})
        # if games_db[i]["locations_id"]:
        #     for j in range(len(games_db[i]["locations_id"])):
        #         await db["location"].update_one({"_id": ObjectId(games_db[i]["locations_id"][j])},
        #                                         {"$set": {"game_id": str(games_db[i]["_id"])}})
        games_db[i]["_id"] = str(games_db[i]["_id"])
    return games_db


async def get_game_service_admin(game_id: str):
    game_db = await db["game"].find_one({"_id": ObjectId(game_id)})
    if game_db is None:
        return None
    game_db["_id"] = str(game_db["_id"])
    return game_db


async def update_game_service_admin(game_id: str, game: SchemaUpdateGame, user_id: str):
    if game_db := await get_game_service_admin(game_id):
        for key, value in game.dict().items():
            game_db[key] = value
        game_db["updated_by"] = user_id
        game_db["updated_at"] = datetime.utcnow()
