from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from uuid import uuid4
from category.services import get_categories_service

from game.schemas import SchemaCreateGame
from game.schemas import SchemaPartialUpdateGame

from game.models import Game
from game.utils import get_history
from game.utils import get_category_game_ai
from game.utils import get_synopsis

from utils import upload_image

from core.database import db


async def get_game_service(game_id: str):
    try:
        if game_db := await db['game'].find_one({'_id': ObjectId(game_id)}):
            return game_db
    except Exception as e:
        print(f"Error getting game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def get_games_service(skip: int = 0, limit: int = 100, user_id: str = None, games_id: list[str] = None):
    if user_id:
        games_query = {'created_by': user_id}
    elif games_id:
        games_query = {'_id': {'$in': games_id}}
    else:
        games_query = {}
    games_db = await db['game'].find(games_query).skip(skip).limit(limit).to_list(None)
    count_games = await db['game'].count_documents({})
    return games_db, count_games


async def create_game_service(game: SchemaCreateGame, user_id: str):
    history = await get_history(story_line=game.story_line)
    synopsys = await get_synopsis(history=history)
    categories_db, count = await get_categories_service(skip=0, limit=100)
    category = await get_category_game_ai(history=synopsys['summary'], categories=categories_db)
    # characters_principals = get_characters_principals(db=db, history=history)

    try:
        game_db = Game(
            story_line=game.story_line,
            history=history,
            synopsis=synopsys['synopsis_generate'],
            title=synopsys['title'],
            prompt_image=synopsys['prompt_image'],
            summary=synopsys['summary'],
            updated_by=user_id,
            created_by=user_id,
            characters_id=[],
            locations_id=[],
            response_error="",
            image="",
            image_background="",
            attempts=3,
            category_id=category,
        )
        if game_created := await db['game'].insert_one(game_db.dict()):
            return await db['game'].find_one({'_id': game_created.inserted_id})
    except Exception as e:
        print(f"Error creating game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not created",
        )


async def update_partial_game_service(game_id: str, game_update: SchemaPartialUpdateGame, user_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        image = upload_image(
            url_image=game_update.image, file_name=f"covers/{uuid4()}.jpg", size=(512, 896)
        )

        game_db["image"] = image
        game_db["updated_by"] = user_id

        await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
        return await db['game'].find_one({'_id': ObjectId(game_id)})

    except Exception as e:
        print(f"Error updating partial game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="has reached the maximum number of generation attempts",
        )


async def subtract_attempts_game_service(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        if game_db["attempts"] > 0:
            game_db["attempts"] = game_db["attempts"] - 1
            game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})

            if game_updated.modified_count:
                return True

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attempts not subtracted",
        )

    except Exception as e:
        print(f"Error subtract attempts game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error in subtract attempts game service",
        )


async def delete_game_service(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        await db['game'].delete_one({'_id': ObjectId(game_id)})
        return True

    except Exception as e:
        print(f"Error deleting game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not deleted",
        )


async def update_image_background_game_service(game_id: str, image: str, identifier: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        game_db["image_background"] = upload_image(
            url_image=image,
            file_name=f"{game_id}/background/background-{identifier}.jpg",
            size=(996, 612),
        )

        game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})

        if game_updated.modified_count:
            return await db['game'].find_one({'_id': ObjectId(game_id)})

    except Exception as e:
        print(f"Error updating image background game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error updating image background game service",
        )


async def get_my_games_service(user_id: str, skip: int = 0, limit: int = 100):
    try:
        games_db = await db['game'].find({'created_by': user_id}).skip(skip).limit(limit).to_list(None)
        count_games = await db['game'].count_documents({'created_by': user_id})
        return games_db, count_games
    except Exception as e:
        print(f"Error getting my games service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Games not found",
        )


async def update_error_message_game_service(game_id: str, error_message: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db:
            if game_db.get('error_message'):
                game_db["error_message"] = f"{game_db.get('error_message')} - {error_message}"
            else:
                game_db["error_message"] = error_message
            game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
            if game_updated.modified_count:
                return await db['game'].find_one({'_id': ObjectId(game_id)})
    except Exception as e:
        print(f"Error updating error message game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )
