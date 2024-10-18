from bson import ObjectId

from core.database import db


async def get_games_service_admin(skip: int = 0, limit: int = 100):
    games_db = await db["game"].find().to_list(None)
    for i in range(len(games_db)):
        # if games_db[i]["characters_id"]:
        #     for j in range(len(games_db[i]["characters_id"])):
        #         await db["character"].update_one({"_id": ObjectId(games_db[i]["characters_id"][j])},
        #                                          {"$set": {"game_id": str(games_db[i]["_id"])}})
        games_db[i]["_id"] = str(games_db[i]["_id"])
    return games_db
