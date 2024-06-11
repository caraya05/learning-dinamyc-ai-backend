from datetime import datetime
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from category.services import get_categories_active_service
from character.services import get_character_leading_role_service

from configuration.services import get_configurations_service
from core.database import db

from game.schemas import SchemaRetrieveGame
from game.schemas import SchemaListGame
from game.schemas import SchemaCreateGame
from game.schemas import SchemaPartialUpdateGame

from game.services import get_game_service
from game.services import get_games_service
from game.services import create_game_service
from game.services import subtract_attempts_game_service
from game.services import update_partial_game_service
from game.services import delete_game_service
from game.services import update_likes_game_service

from auth.auth import auth

from auth.utils import auth_schema
from prompt.services import get_prompt_by_category_service

# from script.services import get_scripts_service

# from scene.services import get_last_scene_service

# from character.services import get_character_leading_role_service

# from location.services import get_location_service


from gpt_ai.utils import generate_image_dalle
from utils import upload_image

router = APIRouter(prefix="/game", tags=["Game"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
async def get_games(
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        count: int = 10,
):
    """
    This endpoint retrieves all games.

    It returns a list of games.
    """

    try:
        games_db, count_pages = await get_games_service(skip=page, limit=count)

        for game in games_db:
            game["_id"] = str(game["_id"])

        return SchemaListGame(results=games_db, count=len(games_db), page=page, total_pages=count_pages // count + 1)

    except Exception as e:
        print(f"Error getting games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Games not found",
        )


@router.get("/{game_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGame)
async def get_game(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a game.

    It expects the game's id in the request path.
    If the game is successfully retrieved, it returns the game's information.
    If the game does not exist, it raises an HTTPException with status code 404.

    Parameters:
    game_id (str): The game's id to be retrieved.
    db (Session): Database session for executing queries.

    Returns:
    SchemaRetrieveGame: The retrieved game's information.

    Raises:
    HTTPException: If the game does not exist, an HTTPException is raised with status code 404.
    """

    try:
        return await get_game_service(game_id)
    except Exception as e:
        print(f"Error getting game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not found",
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveGame)
async def create_game(
        game: SchemaCreateGame,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a new game.

    It expects the game's information in the request body. If the game is successfully created, it returns the game's information.
    If the game already exists, it raises an HTTPException with status code 400.

    Parameters:
    game (SchemaRetrieveGame): The game's information to be created.
    db (Session): Database session for executing queries.

    Returns:
    SchemaRetrieveGame: The created game's information.

    Raises:
    HTTPException: If the game already exists, an HTTPException is raised with status code 400.
    """

    try:
        if user_db.get("stars") <= 0:
            raise Exception("You don't have enough stars to create a game")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You don't have enough stars to create a game",
        )

    try:

        game_db = await create_game_service(game=game, user_id=str(user_db.get("_id")))

        return game_db

    except Exception as e:
        print(f"Error creating game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not created",
        )


@router.get("/generate-cover/{game_id}", status_code=status.HTTP_200_OK)
async def cover_generate(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint generates a cover for a game.
    """
    try:

        game_db = await get_game_service(game_id)

        if game_db.get("attempts") == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attempts exhausted",
            )

        prompt_db_cover = await get_prompt_by_category_service('cover')

        character_leading_role = await get_character_leading_role_service(game_id)

        if not character_leading_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="characters have not been created",
            )

        prompt_content = prompt_db_cover.get("description").replace('x_history', game_db.get("synopsis"))

        prompt_content = prompt_content.replace('x_character', f"{character_leading_role.get('description')}")

        image_generated = generate_image_dalle(prompt=prompt_content, quality="hd", size="1024x1792")

        try:
            await subtract_attempts_game_service(game_id)
        except Exception as e:
            print(f"Error subtracting attempts: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image not generated or attempts exhausted",
            )
        return {"images": image_generated}
    except Exception as e:
        print(f"Error generating cover: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cover not generated",
        )


@router.patch("/{game_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGame)
async def partial_update_game(
        game_id: str,
        game: SchemaPartialUpdateGame,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint updates a game.

    It expects the game's information in the request body. If the game is successfully updated, it returns the game's information.
    If the game does not exist, it raises an HTTPException with status code 404.

    Parameters:
    game_id (str): The game's id to be updated.
    game (SchemaRetrieveGame): The game's information to be updated.
    db (Session): Database session for executing queries.

    Returns:
    SchemaRetrieveGame: The updated game's information.∫

    Raises:
    HTTPException: If the game does not exist, an HTTPException is raised with status code 404.
    """

    try:
        game_db = await update_partial_game_service(game_id, game, str(user_db.get("_id")))
        return game_db

    except Exception as e:
        print(f"Error updating game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not updated",
        )


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint deletes a game.

    It expects the game's id in the request path. If the game is successfully deleted, it returns a message.
    If the game does not exist, it raises an HTTPException with status code 404.

    Parameters:
    game_id (str): The game's id to be deleted.
    db (Session): Database session for executing queries.

    Returns:
    str: A message indicating the game was successfully deleted.

    Raises:
    HTTPException: If the game does not exist, an HTTPException is raised with status code 404.
    """

    try:
        await delete_game_service(game_id)

        return {"message": "Game successfully deleted"}

    except Exception as e:
        print(f"Error deleting game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not deleted",
        )


@router.get("/generate-background/{game_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGame)
async def background_generate(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint generates a background for a game.
    """
    try:

        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        character_leading_role = await db['character'].find_one({'game_id': game_id, 'type': 'leading role'})
        script_db = await db['chapter'].find({'game_id': game_id}).to_list(None)
        scenes_db = await db['scene'].find({'script_id': str(script_db[0]['_id'])}).sort('number', -1).to_list(None)
        location_db = await db['location'].find_one({'_id': ObjectId(scenes_db[3]['location_id'])})
        prompt_db_background = await db['prompt'].find_one({'category': 'image_background'})
        prompt_content = prompt_db_background['description'].replace('x_escena', f" {scenes_db[3]['content']}")
        prompt_content = prompt_content.replace(
            'x_personaje', f"{character_leading_role['name']} {character_leading_role['description']}"
        )
        prompt_content = prompt_content + f" ocurre en la siguiente ubicacion {location_db['description']}"
        image_generated = generate_image_dalle(prompt=prompt_content, quality="hd", size="1792x1024")
        try:
            game_db["image_background"] = upload_image(
                url_image=image_generated,
                file_name=f"background/{uuid4()}.jpg",
                size=(1218, 686),
            )
            game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
            if game_updated.modified_count:
                return await db['game'].find_one({'_id': ObjectId(game_id)})
        except Exception as e:
            print(f"Error AI  generating background: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="not generated",
            )
    except Exception as e:
        print(f"Error generating background: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Background not generated",
        )


@router.get("/my-games/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
async def my_games(
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        count: int = 10,
):
    """
    This endpoint retrieves all games created by the user.

    It returns a list of games.
    """

    try:
        games_db, count_pages = await get_games_service(skip=page, limit=count, user_id=str(user.get("_id")))

        for game in games_db:
            game["_id"] = str(game["_id"])

        return SchemaListGame(results=games_db, count=len(games_db), page=page, total_pages=count_pages)

    except Exception as e:
        print(f"Error getting my games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Games not found",
        )


@router.get("/featured/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
async def features_games(
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all featured games.

    It returns a list of games.
    """

    try:
        games_featured_db = await get_configurations_service()

        if not games_featured_db["featured_games"]:
            return SchemaListGame(results=[], count=0, page=0, total_pages=0)

        games_db, count_pages = await get_games_service(
            skip=1, limit=1000, games_id=(games_featured_db["featured_games"])
        )

        for game in games_db:
            game["_id"] = str(game["_id"])

        return SchemaListGame(results=games_db, count=len(games_db), page=0, total_pages=count_pages)

    except Exception as e:
        print(f"Error getting featured games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Games not found",
        )


@router.get("/popular/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
async def popular_games(
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all popular games.

    It returns a list of games.
    """

    try:
        games_featured_db = await get_configurations_service()

        if not games_featured_db["popular_games"]:
            return SchemaListGame(results=[], count=0, page=0, total_pages=0)

        games_db, count_pages = await get_games_service(skip=1, limit=1000,
                                                        games_id=(games_featured_db["popular_games"]))

        for game in games_db:
            game["_id"] = str(game["_id"])

        return SchemaListGame(results=games_db, count=len(games_db), page=0, total_pages=count_pages)

    except Exception as e:
        print(f"Error getting popular games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Games not found",
        )


@router.get("/categories/", status_code=status.HTTP_200_OK)
async def categories_games(
        category: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        count: int = 10,
):
    """
    This endpoint retrieves all games by category.

    It returns a list of games.
    """

    try:
        games_featured_db = await get_configurations_service()
        if not games_featured_db["games_by_category"]:
            return SchemaListGame(results=[], count=0, page=0, total_pages=0)

        categories_active_db, counts_categories = await get_categories_active_service(0, 100)

        if category not in [category_active["name"] for category_active in categories_active_db]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        games_ids = next(
            (
                games_["games"]
                for games_ in games_featured_db["games_by_category"]
                if games_["name"] == category
            ),
            [],
        )
        games_list, count_pages = await get_games_service(skip=page, limit=count, games_id=games_ids)

        for game in games_list:
            game["_id"] = str(game["_id"])

        return {
            "results": games_list,
            "count": len(games_list),
            "page": page,
            "total_pages": count_pages,
        }

    except Exception as e:
        print(f"Error getting categories games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Games not found",
        )


@router.get("/like/{game_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGame)
async def like_game(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint likes a game.

    It returns the game's information.
    """

    try:
        return await update_likes_game_service(game_id, str(user_db.get("_id")))

    except Exception as e:
        print(f"Error liking game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not liked",
        )


@router.get("/play/{game_id}", status_code=status.HTTP_200_OK)
async def play_game(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint plays a game.

    It returns the game's information.
    """

    try:
        record_game = await db['record_game'].create_one({
            'game_id': game_id,
            'user_id': str(user_db.get("_id")),
            'created_at': datetime.utcnow()
        })
        return "Game played"
    except Exception as e:
        print(f"Error playing game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not played",
        )
