from datetime import datetime, timezone
from datetime import timedelta

import pytz
from bson import ObjectId
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi import Request
from fastapi import File
from fastapi import UploadFile

from fastapi.security import HTTPAuthorizationCredentials

from core.database import db

from auth.auth import auth
from auth.utils import auth_schema

from category.services import get_categories_active_service

from game.schemas import SchemaRetrieveGame
from game.schemas import SchemaChangeCharacter
from game.schemas import SchemaUpdateGameV2
from game.schemas import SchemaListGame


from game.services import GameService

from game.utils import number_players_have_played_game_util, last_date_played_game_util

from game.text_update_services_game import GameTextUpdateService
from game.text_update_schemas import (
    SchemaUpdateGameTitle,
    SchemaGameTitleResponse,
)

from game.image_update_services import GameImageUpdateService

# from celery_worker import generate_context_new_location


from celery_worker import identify_category_game_task
from task.services import create_task_service, update_task_service

router = APIRouter(prefix="/game", tags=["Game"])
router_community = APIRouter(prefix="/community", tags=["community"])

import logging

logger = logging.getLogger(__name__)


# INYECCIÓN DE DEPENDENCIAS EN TODOS LOS ENDPOINTS RELEVANTES
def get_game_service():
    return GameService()


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
async def get_games(
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        game_service: GameService = Depends(get_game_service)
) -> SchemaListGame:
    """
    Endpoint para obtener lista de juegos.
    """
    try:
        games_db, count = await game_service.get_games_service(skip=page, limit=10, user_id=user.get("_id"))
        for game in games_db:
            game["_id"] = str(game["_id"])
        return SchemaListGame(results=games_db, count=count, page=page, total_pages=count // 10 + 1)
    except Exception as e:
        logger.error(f"Error get games: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error get games",
        )


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: GameService = Depends(get_game_service)
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
        await service.delete_game_service(game_id)

        return {"message": "Game successfully deleted"}

    except Exception as e:
        print(f"Error deleting game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not deleted",
        )


@router.get("/like/{game_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGame)
async def like_game(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: GameService = Depends(get_game_service)
):
    """
    This endpoint likes a game.

    It returns the game's information.
    """

    try:
        return await service.update_likes_game_service(game_id, str(user_db.get("_id")))

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
        service: GameService = Depends(get_game_service)
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
                'created_at': datetime.now(timezone.utc),
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
        service: GameService = Depends(get_game_service)
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
        game_db = await service.create_game_v2_service(user_id=str(user_db.get("_id")))

        return game_db

    except Exception as e:
        print(f"Error creating game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not created",
        )


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
                    'published': str(user_db.get("_id")),
                    'published_version': version,
                    'is_published': True,
                    'published_at': datetime.utcnow(),
                    'is_active': False,
                }
            else:
                game_db["_id"] = str(game_db["_id"])
                published_game = {
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
                    'published': str(user_db.get("_id")),
                    'published_version': version,
                    'is_published': True,
                    'published_at': datetime.utcnow(),
                    'is_active': False,
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

    # if category not in [category_active["name"] for category_active in categories_active_db]:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    try:
        if category == 'Other':
            query = {'published': {'$exists': True}, 'category_id': None, "is_active": True}
        else:
            query = {'published': {'$exists': True}, 'category_id': category, "is_active": True}

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
                    {'_id': ObjectId(game['published'])}
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
        game_service=Depends(GameService)
):
    """
    This endpoint unpublishes a game.

    It returns the game's information.
    """

    try:
        if game_db := game_service.get_game_service(game_id):
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
        game_service = Depends(GameService)
):
    """
    This endpoint retrieves the version of a published game.

    It returns the game's information.
    """

    try:
        if game_db := game_service.get_game_service(game_id):
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
        game_service: GameService = Depends(get_game_service)
):
    """
    This endpoint changes the character of a game.

    It returns the game's information.
    """

    try:
        if game_db := await game_service.change_character_principal_game_service(
                data.game_id, data.character_id, str(user_db.get("_id"))
        ):
            return "Character changed"

    except Exception as e:
        print(f"Error changing character: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not changed",
        )


@router.get("/published/{game_id}", status_code=status.HTTP_200_OK)
async def get_published_game(
        game_id: str,
        service: GameService = Depends(get_game_service)
):
    """
    Obtiene un juego publicado por ID.
    No requiere autenticación. Solo retorna juegos publicados.

    Args:
        game_id: ID del juego publicado

    Returns:
        dict: Información del juego publicado

    Raises:
        HTTPException: Si el juego no se encuentra o no está publicado
    """
    if not ObjectId.is_valid(game_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid game ID",
        )

    try:
        published_game = await service.get_published_game_detail_service(game_id)
        if not published_game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Published game not found",
            )

        return published_game
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting published game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting published game",
        )


@router.get("/{game_id}", response_model=SchemaRetrieveGame)
async def get_game(
        game_id: str,
        publish: bool = False,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        game_service = Depends(get_game_service)
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
        game_db = await game_service.get_game(game_id)
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
        game_service: GameService = Depends(get_game_service)
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
        game_db = await game_service.get_game_by_code_access_service(access_code)
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
        service: GameService = Depends(get_game_service)
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
        game_db = await service.update_game_v2_service(game_id, data, str(user_db.get("_id")))
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
        game_service: GameService = Depends(get_game_service)
):
    """
    This endpoint retrieves all games created by the user.

    It returns a list of games.
    """

    try:
        games_db, count_pages = await game_service.get_my_games_v2_service(
            skip=page, limit=count, user_id=str(user.get("_id"))
        )

        if most_played:
            games_db = sorted(games_db, key=lambda x: x["plays"], reverse=True)

        if recent:
            games_db = await game_service.get_games_played_recent_service(user_id=str(user.get("_id")))
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


@router.post("/clone/{game_id}", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveGame)
async def clone_game(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        game_service: GameService = Depends(get_game_service)
):
    """
    Este endpoint clona un juego completo con todos sus elementos asociados.

    Clona el juego especificado creando una copia completa que incluye:
    - El juego principal con nuevos metadatos
    - Todas las ubicaciones (locations) asociadas
    - Todos los personajes (characters) asociados
    - Todos los objetos/items asociados

    Se crean nuevos IDs para todos los elementos y se actualizan las referencias
    cruzadas entre ellos. El juego clonado pertenecerá al usuario autenticado.

    Parameters:
    game_id (str): El ID del juego a clonar
    user_db (dict): Usuario autenticado obtenido del token
    Token (HTTPAuthorizationCredentials): Token de autorización

    Returns:
    SchemaRetrieveGame: La información del juego clonado

    Raises:
    HTTPException: Si el juego no existe o hay errores en la clonación
    """
    try:
        # Verificar si el usuario tiene suficientes estrellas para clonar
        if user_db.get("stars", 0) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tienes suficientes estrellas para clonar un juego",
            )

        # Llamar al servicio de clonación
        cloned_game = await game_service.clone_game_service(game_id, str(user_db.get("_id")))

        # Convertir ObjectId a string para la respuesta
        cloned_game["_id"] = str(cloned_game["_id"])

        return cloned_game

    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        print(f"Error cloning game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al clonar el juego",
        )


# ============ GAME TEXT UPDATE ENDPOINTS ============

def get_game_text_service():
    """Inyección de dependencias para el servicio de actualización de textos de juego"""
    return GameTextUpdateService()


@router.patch(
    "/{game_id}/title/",
    status_code=status.HTTP_200_OK,
    response_model=SchemaGameTitleResponse,
    tags=["Game"]
)
async def update_game_title_endpoint(
    game_id: str,
    request: SchemaUpdateGameTitle,
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: GameTextUpdateService = Depends(get_game_text_service)
):
    """Actualiza el título de un juego"""
    try:
        if not request.title or not request.title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Validation Error", "message": "Title cannot be empty", "code": "VALIDATION_ERROR"}
            )

        user_id = str(user.get("_id"))
        result = await service.update_game_title(game_id, request.title, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


# ============ GAME IMAGE UPDATE ENDPOINTS ============

def get_game_image_service():
    """Inyección de dependencias para el servicio de imágenes de juegos"""
    return GameImageUpdateService()


@router.patch(
    "/{game_id}/cover/",
    status_code=status.HTTP_200_OK,
    tags=["Game"]
)
async def update_game_cover(
    game_id: str,
    image: UploadFile = File(..., description="Cover image (1920x1080px, max 5MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: GameImageUpdateService = Depends(get_game_image_service)
):
    """Actualiza la portada (cover) de un juego"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_game_cover(game_id, image, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{game_id}/background/",
    status_code=status.HTTP_200_OK,
    tags=["Game"]
)
async def update_game_background(
    game_id: str,
    image: UploadFile = File(..., description="Background image (1920x1080px, max 5MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: GameImageUpdateService = Depends(get_game_image_service)
):
    """Actualiza el fondo (background) de un juego"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_game_background(game_id, image, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})


@router.patch(
    "/{game_id}/minimalist/",
    status_code=status.HTTP_200_OK,
    tags=["Game"]
)
async def update_game_minimalist(
    game_id: str,
    image: UploadFile = File(..., description="Minimalist icon (512x512px, max 2MB)"),
    user: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: GameImageUpdateService = Depends(get_game_image_service)
):
    """Actualiza el ícono minimalista de un juego"""
    try:
        user_id = str(user.get("_id"))
        result = await service.update_game_minimalist(game_id, image, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not Found", "message": error_msg, "code": "RESOURCE_NOT_FOUND"})
        elif "permission" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden", "message": error_msg, "code": "PERMISSION_DENIED"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal Server Error", "code": "INTERNAL_ERROR"})

