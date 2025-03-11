from datetime import datetime
from datetime import timedelta

import pytz
from bson import ObjectId
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from core.database import db

from auth.auth import auth
from auth.utils import auth_schema

from category.services import get_categories_active_service

from game.schemas import SchemaRetrieveGame
from game.schemas import SchemaChangeCharacter
from game.schemas import SchemaUpdateGameV2
from game.schemas import SchemaListGame

from game.services import (
    get_game_service,
    get_game_by_code_access_service,
    get_games_played_recent_service,
)
from game.services import create_game_v2_service
from game.services import change_character_principal_game_service
from game.services import get_game_v2_service
from game.services import update_game_v2_service
from game.services import get_my_games_v2_service
from game.services import get_games_service
from game.services import delete_game_service
from game.services import update_likes_game_service


from game.utils import number_players_have_played_game_util, last_date_played_game_util

# from celery_worker import generate_context_new_location


from celery_worker import identify_category_game_task
from task.services import create_task_service, update_task_service

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
            game["plays"] = await number_players_have_played_game_util(str(game["_id"]))

        return SchemaListGame(
            results=games_db, count=len(games_db), page=page, total_pages=count_pages // count + 1
        )

    except Exception as e:
        print(f"Error getting games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Games not found",
        )


# @router.get("/generate-cover/{game_id}", status_code=status.HTTP_200_OK)
# async def cover_generate(
#         game_id: str,
#         user_db: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     """
#     This endpoint generates a cover for a game.
#     """
#     try:
#         game_db = await get_game_service(game_id)
#         if game_db.get("attempts") == 0:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Attempts exhausted",
#             )
#         prompt_db_cover = await get_prompt_by_category_service('cover')
#         character_leading_role = await get_character_leading_role_service(game_id)
#         if not character_leading_role:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="characters have not been created",
#             )
#         prompt_content = prompt_db_cover.get("description").replace('x_history', game_db.get("synopsis"))
#         prompt_content = prompt_content.replace('x_character', f"{character_leading_role.get('description')}")
#         image_generated = generate_image_dalle(prompt=prompt_content, quality="hd", size="1024x1792")
#         try:
#             await subtract_attempts_game_service(game_id)
#         except Exception as e:
#             print(f"Error subtracting attempts: {str(e)}")
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Image not generated or attempts exhausted",
#             )
#         return {"images": image_generated}
#     except Exception as e:
#         print(f"Error generating cover: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Cover not generated",
#         )


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


# @router.get("/generate-background/{game_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGame)
# async def background_generate(
#         game_id: str,
#         user_db: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     """
#     This endpoint generates a background for a game.
#     """
#     try:
#
#         game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
#         character_leading_role = await db['character'].find_one({'game_id': game_id, 'type': 'leading role'})
#         script_db = await db['chapter'].find({'game_id': game_id}).to_list(None)
#         scenes_db = await db['scene'].find({'script_id': str(script_db[0]['_id'])}).sort('number', -1).to_list(None)
#         location_db = await db['location'].find_one({'_id': ObjectId(scenes_db[3]['location_id'])})
#         prompt_db_background = await db['prompt'].find_one({'category': 'image_background'})
#         prompt_content = prompt_db_background['description'].replace('x_escena', f" {scenes_db[3]['content']}")
#         prompt_content = prompt_content.replace(
#             'x_personaje', f"{character_leading_role['name']} {character_leading_role['description']}"
#         )
#         prompt_content = prompt_content + f" ocurre en la siguiente ubicacion {location_db['description']}"
#         image_generated = generate_image_dalle(prompt=prompt_content, quality="hd", size="1792x1024")
#         try:
#             game_db["image_background"] = upload_image(
#                 url_image=image_generated,
#                 file_name=f"background/{uuid4()}.jpg",
#                 size=(1218, 686),
#             )
#             game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
#             if game_updated.modified_count:
#                 return await db['game'].find_one({'_id': ObjectId(game_id)})
#         except Exception as e:
#             print(f"Error AI  generating background: {str(e)}")
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="not generated",
#             )
#     except Exception as e:
#         print(f"Error generating background: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Background not generated",
#         )


# @router.get("/categories/", status_code=status.HTTP_200_OK)
# async def categories_games(
#         category: str,
#         user_db: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
#         page: int = 1,
#         count: int = 10,
# ):
#     """
#     This endpoint retrieves all games by category.
#
#     It returns a list of games.
#     """
#
#     try:
#         games_featured_db = await get_configurations_service()
#         if not games_featured_db["games_by_category"]:
#             return SchemaListGame(results=[], count=0, page=0, total_pages=0)
#
#         categories_active_db, counts_categories = await get_categories_active_service(0, 100)
#
#         if category not in [category_active["name"] for category_active in categories_active_db]:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
#
#         games_ids = next(
#             (
#                 games_["games"]
#                 for games_ in games_featured_db["games_by_category"]
#                 if games_["name"] == category
#             ),
#             [],
#         )
#         games_list, count_pages = await get_games_service(skip=page, limit=count, games_id=games_ids)
#
#         for game in games_list:
#             game["_id"] = str(game["_id"])
#
#         return {
#             "results": games_list,
#             "count": len(games_list),
#             "page": page,
#             "total_pages": count_pages,
#         }
#
#     except Exception as e:
#         print(f"Error getting categories games: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Games not found",
#         )


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
        record_game = await db['record_game'].insert_one(
            {
                'game_id': game_id,
                'user_id': str(user_db.get("_id")),
                'created_at': datetime.utcnow(),
            }
        )
        return {'detail': 'Game played'}
    except Exception as e:
        print(f"Error playing game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not played",
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveGame)
async def create_game(
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

        game_db = await create_game_v2_service(user_id=str(user_db.get("_id")))

        return game_db

    except Exception as e:
        print(f"Error creating game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not created",
        )


#


# @router.post("/add-character", status_code=status.HTTP_200_OK)
# async def add_character_game(
#         data: SchemaAddCharacter,
#         user_db: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),@router.post("/add-item", status_code=status.HTTP_200_OK)
# # async def add_item_game(
# #         data: SchemaAddItem,
# #         user_db: dict = Depends(auth),
# #         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# # ):
# #     """
# #     This endpoint adds an item to a game.
# #
# #     It returns the game's information.
# #     """
# #
# #     try:
# #         return await add_items_game_service(data.game_id, data.item_id)
# #
# #     except Exception as e:
# #         print(f"Error adding item game: {str(e)}")
# #         raise HTTPException(
# #             status_code=status.HTTP_400_BAD_REQUEST,
# #             detail="Item not added",
# #         )
# ):
#     """
#     This endpoint adds a character to a game.
#
#     It returns the game's information.
#     """
#
#     try:
#         location_db = await db['character_location'].find_one({'character_id': data.character_id})
#         if not location_db:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Location not found",
#             )
#         if character_game := await add_characters_game_service(
#                 game_id=data.game_id,
#                 characters_id=data.character_id,
#                 location_id=location_db['location_id'],
#                 user_id=str(user_db.get("_id")),
#         ):
#             return "Character added"
#
#
# except HTTPException as e:
#     print(f"Error adding character game: {e.detail}")
#     raise HTTPException(
#         status_code=e.status_code,
#         detail=e.detail,
#     )


# @router.post("/add-location", status_code=status.HTTP_200_OK)
# async def add_location_game(
#         data: SchemaAddLocation,
#         user_db: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     """
#     This endpoint adds a location to a game.
#
#     It returns the game's information.
#     """
#
#     try:
#         if location_game := await add_locations_game_service(data.game_id, data.location_id):
#             # generate_context_new_location.delay(data.game_id, data.location_id)
#             return "Location added"
#
#     except Exception as e:
#         print(f"Error adding location game: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Location not added",
#         )


# @router.get("/publish/{game_id}", status_code=status.HTTP_200_OK)
# async def publish_game(
#     game_id: str,
#     user_db: dict = Depends(auth),
#     Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     """
#     This endpoint publishes a game.
#
#     It returns the game's information.
#     """
#
#     game_db = await get_game_v2_service(game_id)
#
#     if not game_db.get("published", None):
#         task_db = await create_task_service(
#             _task_id="",
#             _user_id=str(user_db.get("_id")),
#             _task_data={},
#             _element_id=game_id,
#             _element_type="game",
#             _process="identify_category",
#         )
#
#         task_celery = identify_category_game_task.delay(
#             _game_id=game_id, _task_id=str(task_db["_id"]), _user_id=str(user_db.get("_id"))
#         )
#
#         await update_task_service(
#             _id=str(task_db["_id"]),
#             _task_id=task_celery.id,
#         )
#
#     try:
#         if game_db := await get_game_v2_service(game_id):
#
#             game_db["_id"] = str(game_db["_id"])
#             count_versions = await db['published_game'].count_documents({'game_id': game_id})
#             if count_versions:
#                 version = count_versions + 1
#             else:
#                 version = 1
#             game_db["version"] = version
#             if "published" in game_db:
#                 del game_db["published"]
#             if "published_version" in game_db:
#                 del game_db["published_version"]
#             if "published_at" in game_db:
#                 del game_db["published_at"]
#             # Current time in UTC
#             now_utc = datetime.now(pytz.timezone('UTC'))
#             now_bog = now_utc.astimezone(pytz.timezone('America/Bogota'))
#             now_bog_minus_5 = now_bog - timedelta(hours=5)
#
#             if not game_db.get("published", None):
#                 published_game = {
#                     "published": True,
#                     "created_at": now_bog_minus_5,
#                     "created_by": str(user_db.get("_id")),
#                     "updated_at": now_bog_minus_5,
#                     "updated_by": str(user_db.get("_id")),
#                     "status": 1,
#                     "game_id": game_id,
#                     "game": None,
#                     "version": version,
#                     "return_note": None,
#                     "reviewed": False,
#                     "reviewer": None,
#                     "reviewed_at": None,
#                     "reviewed_by": None,
#                 }
#             else:
#                 game_db["_id"] = str(game_db["_id"])
#                 published_game = {
#                     "published": True,
#                     "created_at": now_bog_minus_5,
#                     "created_by": str(user_db.get("_id")),
#                     "updated_at": now_bog_minus_5,
#                     "updated_by": str(user_db.get("_id")),
#                     "status": 2,
#                     "game_id": game_id,
#                     "game": game_db,
#                     "version": version,
#                     "return_note": None,
#                     "reviewed": True,
#                     "reviewer": str(user_db.get("_id")),
#                     "reviewed_at": now_bog_minus_5,
#                     "reviewed_by": str(user_db.get("_id")),
#                 }
#
#             if published_game_db := await db['published_game'].insert_one(published_game):
#                 await db['game'].update_one(
#                     {'_id': ObjectId(game_id)},
#                     {
#                         '$set': {
#                             'published': str(published_game_db.inserted_id),
#                             'published_version': version,
#                             'is_published': True,
#                             'published_at': datetime.utcnow(),
#                         },
#                     },
#                 )
#                 return "Game published"
#
#     except Exception as e:
#         print(f"Error publishing game: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Game not published",
#         )


@router.get("/publish/{game_id}", status_code=status.HTTP_200_OK)
async def publish_game(
    game_id: str,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint publishes a game.

    It returns the game's information.
    """

    try:
        if game_db := await db['game'].find_one({'_id': ObjectId(game_id)}):

            game_db["_id"] = str(game_db["_id"])
            count_versions = await db['published_game'].count_documents({'game_id': game_id})
            if count_versions:
                version = count_versions + 1
            else:
                version = 1
            game_db["version"] = version
            if "published" in game_db:
                del game_db["published"]
            if "published_version" in game_db:
                del game_db["published_version"]
            if "published_at" in game_db:
                del game_db["published_at"]
            # Current time in UTC
            now_utc = datetime.now(pytz.timezone('UTC'))
            now_bog = now_utc.astimezone(pytz.timezone('America/Bogota'))
            now_bog_minus_5 = now_bog - timedelta(hours=5)

            if not game_db.get("published", None):
                published_game = {
                    "published": True,
                    "created_at": now_bog_minus_5,
                    "created_by": str(user_db.get("_id")),
                    "updated_at": now_bog_minus_5,
                    "updated_by": str(user_db.get("_id")),
                    "status": 1,
                    "game_id": game_id,
                    "game": None,
                    "version": version,
                    "return_note": None,
                    "reviewed": False,
                    "reviewer": None,
                    "reviewed_at": None,
                    "reviewed_by": None,
                }
            else:
                game_db["_id"] = str(game_db["_id"])
                published_game = {
                    "published": True,
                    "created_at": now_bog_minus_5,
                    "created_by": str(user_db.get("_id")),
                    "updated_at": now_bog_minus_5,
                    "updated_by": str(user_db.get("_id")),
                    "status": 2,
                    "game_id": game_id,
                    "version": version,
                    "return_note": None,
                    "reviewed": True,
                    "reviewer": str(user_db.get("_id")),
                    "reviewed_at": now_bog_minus_5,
                    "reviewed_by": str(user_db.get("_id")),
                }

            if published_game_db := await db['published_game'].insert_one(published_game):
                await db['game'].update_one(
                    {'_id': ObjectId(game_id)},
                    {
                        '$set': {
                            'published': str(published_game_db.inserted_id),
                            'published_version': version,
                            'is_published': True,
                            'published_at': datetime.utcnow(),
                        },
                    },
                )
                return "Game published"

    except Exception as e:
        print(f"Error publishing game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not published",
        )


@router.get("/publish/", status_code=status.HTTP_200_OK)
async def publish_games(
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint publishes all games.

    It returns a message.
    """

    try:
        published_games = await db['game'].find({'published': {'$exists': True}}).to_list(None)
        games_published = []
        for game in published_games:
            if games_published_db := await db['published_game'].find_one(
                {'_id': ObjectId(game['published'])}
            ):
                # print(games_published_db)
                games_published.append(games_published_db["game"])
        return games_published

    except Exception as e:
        print(f"Error publishing games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Games not published",
        )


@router.get("/publish/categories/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
async def publish_games(
    category: str,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
    page: int = 1,
    count: int = 10,
):
    """
    This endpoint publishes all games.

    It returns a message.
    """
    categories_active_db, counts_categories = await get_categories_active_service(0, 100)

    if category not in [category_active["name"] for category_active in categories_active_db]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    try:
        if category == 'Other':
            query = {'published': {'$exists': True}, 'category_id': None}
        else:
            query = {'published': {'$exists': True}, 'category_id': category}

        published_games = (
            await db['game'].find(query).skip((page - 1) * count).limit(count).to_list(None)
        )
        count_published_games = await db['game'].count_documents(query)

        if not published_games:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Games not published",
            )
        games_published = []
        for game in published_games:
            if games_published_db := await db['published_game'].find_one(
                {'_id': ObjectId(game['published']), 'status': 2}
            ):
                game["_id"] = str(game["_id"])
                game["status"] = games_published_db["status"]
                games_published.append(game)
        return SchemaListGame(
            results=games_published,
            count=len(games_published),
            page=page,
            total_pages=count_published_games // count + 1,
        )

    except Exception as e:
        print(f"Error publishing games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Games not published",
        )


@router.get("/unpublish/{game_id}", status_code=status.HTTP_200_OK)
async def unpublish_game(
    game_id: str,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint unpublishes a game.

    It returns the game's information.
    """

    try:
        if game_db := get_game_service(game_id):
            await db['game'].update_one(
                {'_id': ObjectId(game_id), 'published': {'$exists': True}},
                {
                    '$unset': {
                        'published': "",
                        'published_version': "",
                        'is_published': "",
                        'published_at': "",
                    }
                },
            )
            await db['published_game'].find_one_and_delete({'game_id': game_id})
            return "Game unpublished"

    except Exception as e:
        print(f"Error unpublishing game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not unpublished",
        )


@router.get("/version-published/{game_id}", status_code=status.HTTP_200_OK)
async def version_published_game(
    game_id: str,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves the version of a published game.

    It returns the game's information.
    """

    try:
        if game_db := get_game_service(game_id):
            published_game = await db['published_game'].find_one({'game_id': game_id})

            return published_game

    except Exception as e:
        print(f"Error getting version published game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Version not found",
        )


@router.post("/character-principal/", status_code=status.HTTP_200_OK)
async def change_character(
    data: SchemaChangeCharacter,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint changes the character of a game.

    It returns the game's information.
    """

    try:
        if game_db := await change_character_principal_game_service(
            data.game_id, data.character_id, str(user_db.get("_id"))
        ):
            return "Character changed"

    except Exception as e:
        print(f"Error changing character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not changed",
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
        game_db = await get_game_service(game_id)
        game_pending = await db['published_game'].find_one({'game_id': game_id})
        if game_pending:
            game_db["status"] = game_pending["status"]
            game_db["reject_note"] = game_pending["return_note"]
        else:
            game_db["status"] = 0
            game_db["reject_note"] = None

        return game_db

    except Exception as e:
        print(f"Error getting game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not found",
        )


@router.get(
    "/access-code/{access_code}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGame
)
async def get_game(
    access_code: str,
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
        game_db = await get_game_by_code_access_service(access_code)
        game_pending = await db['published_game'].find_one({'game_id': str(game_db["_id"])})
        if game_pending:
            game_db["status"] = game_pending["status"]
            game_db["reject_note"] = game_pending["return_note"]
        else:
            game_db["status"] = 0
            game_db["reject_note"] = None

        return game_db

    except Exception as e:
        print(f"Error getting game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not found",
        )


@router.post("/update/{game_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGame)
async def update_game(
    game_id: str,
    data: SchemaUpdateGameV2,
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
        game_db = await update_game_v2_service(game_id, data, str(user_db.get("_id")))
        return game_db

    except Exception as e:
        print(f"Error updating game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not updated",
        )


@router.get("/my-games/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
async def my_games(
    user: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
    page: int = 1,
    count: int = 10,
    most_played: bool = False,
    recent: bool = False,
):
    """
    This endpoint retrieves all games created by the user.

    It returns a list of games.
    """

    try:
        games_db, count_pages = await get_my_games_v2_service(
            skip=page, limit=count, user_id=str(user.get("_id"))
        )

        for game in games_db:
            game["_id"] = str(game["_id"])
            game["plays"] = await number_players_have_played_game_util(str(game["_id"]))
            # game["last_date_played"] = await last_date_played_game_util(str(game["_id"]))
            game_published = await db['published_game'].find_one({'game_id': str(game["_id"])})
            if not game_published:
                game["status"] = 0
                game["reject_note"] = None
            else:
                game["status"] = game_published["status"]
                game["reject_note"] = game_published["return_note"]

        if most_played:
            games_db = sorted(games_db, key=lambda x: x["plays"], reverse=True)

        if recent:
            games_db = await get_games_played_recent_service(user_id=str(user.get("_id")))
            for game in games_db:
                game["_id"] = str(game["_id"])
                game["plays"] = await number_players_have_played_game_util(str(game["_id"]))
                game_published = await db['published_game'].find_one({'game_id': str(game["_id"])})
                if not game_published:
                    game["status"] = 0
                    game["reject_note"] = None
                else:
                    game["status"] = game_published["status"]
                    game["reject_note"] = game_published["return_note"]
            count_pages = 1

        return SchemaListGame(
            results=games_db, count=len(games_db), page=page, total_pages=count_pages // count + 1
        )

    except Exception as e:
        print(f"Error getting my games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Games not found",
        )


@router.get("/my-games-in-progress/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
async def my_games_in_progress(
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
        games_db = await (
            db['game']
            .find({'published': {'$exists': False}})
            .sort({'created_at': -1})
            .skip((page - 1) * count)
            .limit(count)
            .to_list(None)
        )
        count_games = await db['game'].count_documents(
            {'created_by': str(user.get("_id")), 'published': {'$exists': False}}
        )

        for game in games_db:
            game["_id"] = str(game["_id"])

        return SchemaListGame(
            results=games_db, count=len(games_db), page=page, total_pages=count_games
        )

    except Exception as e:
        print(f"Error getting my games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Games not found",
        )
