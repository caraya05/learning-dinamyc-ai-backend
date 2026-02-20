from datetime import datetime

from bson import ObjectId

from core.database import db
from game.schemas_admin import SchemaUpdateGame
from utils import upload_image
import requests
from io import BytesIO
from PIL import Image
from uuid import uuid4


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
            if value is not None:
                game_db[key] = value
                if key == "image":
                    response = requests.get(value)
                    original_image = Image.open(BytesIO(response.content))
                    original_width, original_height = original_image.size
                    new_width = 512
                    ratio = new_width / original_width
                    new_height = int(original_height * ratio)
                    game_db["image_minimalist"] = upload_image(
                        url_image=value,
                        file_name=f"covers/{uuid4()}_minimalist.jpg",
                        size=(new_width, new_height),

                    )
        game_db["updated_by"] = user_id
        game_db["updated_at"] = datetime.utcnow()
        del game_db["_id"]
        await db["game"].update_one({"_id": ObjectId(game_id)}, {"$set": game_db})
        return game_db
