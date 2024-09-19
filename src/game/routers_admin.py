from bson import ObjectId
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Depends
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

from auth.auth import auth_admin
from auth.routers import token
from auth.utils import auth_schema
from core.database import db

from datetime import datetime
from typing import Optional

from game.services import get_game_v2_service
from sound.services import get_sound_service

router = APIRouter(prefix="/game-pending", tags=["Game Pending"])


@router.get("/", status_code=status.HTTP_200_OK)
async def get_pending_games(
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    games_db = await db["published_game"].find().sort({"created_at": -1}).to_list(None)
    for game in games_db:
        game["_id"] = str(game["_id"])
        game["game"] = await get_game_v2_service(game["game_id"])
        game["game"]["_id"] = str(game["game"]["_id"])
        user_game = game.get("created_by") if "created_by" in game else game.get("updated_by")
        user_db = await db["user"].find_one({"_id": ObjectId(user_game)})
        game["user"] = user_db["email"]
        if game.get("reviewer"):
            user_db = await db["user"].find_one({"_id": ObjectId(game["reviewer"])})
            game["reviewer"] = user_db["email"]
    return games_db


@router.get("/{game_id}", status_code=status.HTTP_200_OK)
async def get_pending_game(
        game_id: str,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    game_db = await db["published_game"].find_one({"_id": ObjectId(game_id)})
    if game_db is None:
        raise HTTPException(status_code=404, detail="Game not found")
    game_db["_id"] = str(game_db["_id"])
    user_db = await db["user"].find_one({"_id": ObjectId(game_db["created_by"])})
    game_db["user"] = user_db["email"]
    game_db["game"] = await get_game_v2_service(game_db["game_id"])
    game_db["game"]["_id"] = str(game_db["game"]["_id"])

    # game_db["game"]["locations"][0]["characters"] *= 10
    # game_db["game"]["locations"] *= 10
    # game_db["game"]["characters"] *= 10

    for location in game_db["game"]["locations"]:
        sound_db = await get_sound_service(location["sound_id"])
        location["sound"] = sound_db.get("file")
    return game_db


@router.get("/publish/{game_id}", status_code=status.HTTP_200_OK)
async def publish_game(
        game_id: str,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    published_game_db = await db["published_game"].find_one({"_id": ObjectId(game_id)})
    if game_db := await get_game_v2_service(published_game_db["game_id"]):
        game_db["_id"] = str(game_db["_id"])
        published_game_db["game"] = game_db
        published_game_db["updated_at"] = datetime.utcnow()
        published_game_db["updated_by"] = str(user_db["_id"])
        published_game_db["status"] = 2

        if not published_game_db["reviewed_at"]:
            published_game_db["reviewed_at"] = datetime.utcnow()
            published_game_db["reviewed_by"] = str(user_db["_id"])
        try:
            await db["published_game"].update_one({"_id": published_game_db["_id"]}, {"$set": published_game_db})
            return {"detail": "Game published"}
        except Exception as e:
            raise HTTPException(status_code=400, detail="Error publishing game")
    else:
        raise HTTPException(status_code=404, detail="Game not found")


class SchemaUpdateGamePublish(BaseModel):
    category: Optional[str]
    return_note: Optional[str]
    reviewer: Optional[str]


@router.patch("/reject/{game_id}", status_code=status.HTTP_200_OK)
async def reject_game(
        game_id: str,
        data: SchemaUpdateGamePublish,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    published_game_db = await db["published_game"].find_one({"_id": ObjectId(game_id)})
    published_game_db["reviewed_at"] = datetime.utcnow()
    published_game_db["reviewed_by"] = str(user_db["_id"])
    published_game_db["status"] = 3
    published_game_db["return_note"] = data.return_note
    try:
        await db["published_game"].update_one({"_id": published_game_db["_id"]}, {"$set": published_game_db})
        return {"detail": "Game rejected"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error rejecting game")


@router.patch("/review/{game_id}", status_code=status.HTTP_200_OK)
async def reviewer_game(
        game_id: str,
        data: SchemaUpdateGamePublish,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    published_game_db = await db["published_game"].find_one({"_id": ObjectId(game_id)})
    published_game_db["reviewed_at"] = datetime.utcnow()
    published_game_db["reviewed_by"] = data.reviewer
    # published_game_db["status"] = "reviewed"
    published_game_db["reviewer"] = data.reviewer
    try:
        await db["published_game"].update_one({"_id": published_game_db["_id"]}, {"$set": published_game_db})
        return {"detail": "Game reviewed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error reviewing game")


@router.patch("/update/{game_id}", status_code=status.HTTP_200_OK)
async def update_game(
        game_id: str,
        data: SchemaUpdateGamePublish,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    published_game_db = await db["published_game"].find_one({"_id": ObjectId(game_id)})
    published_game_db["updated_at"] = datetime.utcnow()
    published_game_db["updated_by"] = str(user_db["_id"])
    game_db = await db["game"].find_one({"_id": ObjectId(published_game_db["game_id"])})
    game_db["category_id"] = data.category
    try:
        await db["game"].update_one({"_id": ObjectId(game_db["_id"])}, {"$set": game_db})
        await db["published_game"].update_one({"_id": published_game_db["_id"]}, {"$set": published_game_db})
        return {"detail": "Game updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error updating game")
