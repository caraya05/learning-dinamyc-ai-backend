import json
import ast

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from category.services import get_categories_active_service
from config import auth_scheme
from configuration.services import get_configuration_service

from game.schemas import SchemaRetrieveGame
from game.schemas import SchemaListGame
from game.schemas import SchemaCreateGame
from game.schemas import SchemaPartialUpdateGame

from game.services import get_games_service
from game.services import update_image_background_game_service
from game.services import create_game_service
from game.services import get_game_service
from game.services import subtract_attempts_game_service
from game.services import update_partial_game_service
from game.services import delete_game_service

from script.services import get_scripts_service

from scene.services import get_last_scene_service

from character.services import get_character_leading_role_service

from location.services import get_location_service

from user.services import get_current_user_service

from gpt_ai.utils import generate_image_dalle
from gpt_ai.utils import generate_gpt4_

import ast

from prompt.services import get_prompt_by_field

router = APIRouter(prefix="/game", tags=["Game"])


# Dependency
def get_db(request: Request):
    return request.state.db


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
async def get_games(db: Session = Depends(get_db),
                    Authorize: AuthJWT = Depends(),
                    Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                    page: int = 1,
                    count: int = 10,
                    ):
    """
    This endpoint retrieves all games.

    It returns a list of games.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    games_db, count_pages = get_games_service(db, skip=page, limit=count)

    return SchemaListGame(results=games_db, count=len(games_db), page=page, total_pages=count_pages)


@router.get("/{game_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGame)
def get_game(game_id: str,
             db: Session = Depends(get_db),
             Authorize: AuthJWT = Depends(),
             Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
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
        Authorize.jwt_required()
        current_user = Authorize.get_raw_jwt()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    game_db = get_game_service(db, game_id, current_user['sub'])

    return game_db


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveGame)
def create_game(game: SchemaCreateGame,
                db: Session = Depends(get_db),
                Authorize: AuthJWT = Depends(),
                Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
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
        Authorize.jwt_required()
        current_user = Authorize.get_raw_jwt()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_db = get_current_user_service(db, Authorize.get_raw_jwt())

    if user_db.stars <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You don't have enough stars to create a game",
        )

    game_db = create_game_service(db=db, game=game, user_id=current_user['sub'])

    return game_db


@router.get("/generate-cover/{game_id}", status_code=status.HTTP_200_OK)
def cover_generate(
        game_id: str,
        db: Session = Depends(get_db),
        Authorize: AuthJWT = Depends(),
        Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """
    This endpoint generates a cover for a game.
    """
    try:
        Authorize.jwt_required()
        current_user = Authorize.get_raw_jwt()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    game_db = get_game_service(db, game_id)

    if game_db.attempts == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attempts exhausted",
        )

    prompt_db_cover = get_prompt_by_field(db, 'category', 'cover')

    character_leading_role = get_character_leading_role_service(db, game_db.id)

    if not character_leading_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="characters have not been created",
        )

    prompt_content = prompt_db_cover.description.replace('x_history', game_db.synopsis)

    prompt_content = prompt_content.replace('x_character',
                                            f"{character_leading_role.description}")

    image_generated = generate_image_dalle(prompt=prompt_content,
                                           quality="hd",
                                           size="1024x1792")

    try:
        subtract_attempts_game_service(db, game_id)
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image not generated or attempts exhausted",
        )
    return {"images": image_generated}


@router.patch("/{game_id}", status_code=status.HTTP_200_OK)
def partial_update_game(game_id: str,
                        game: SchemaPartialUpdateGame,
                        db: Session = Depends(get_db),
                        Authorize: AuthJWT = Depends(),
                        Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
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
        Authorize.jwt_required()
        current_user = Authorize.get_raw_jwt()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    game_db = update_partial_game_service(db, game_id, game, current_user['sub'])

    return game_db


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(game_id: str,
                db: Session = Depends(get_db),
                Authorize: AuthJWT = Depends(),
                Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
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
        Authorize.jwt_required()
        current_user = Authorize.get_raw_jwt()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    delete_game_service(db, game_id)

    return {"message": "Game successfully deleted"}


@router.get("/generate-background/{game_id}", status_code=status.HTTP_200_OK)
def background_generate(
        game_id: str,
        db: Session = Depends(get_db),
        Authorize: AuthJWT = Depends(),
        Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """
    This endpoint generates a background for a game.
    """
    try:
        Authorize.jwt_required()
        current_user = Authorize.get_raw_jwt()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    game_db = get_game_service(db, game_id)

    character_leading_role = get_character_leading_role_service(db, game_db.id)

    script_db = get_scripts_service(db=db, game_id=game_db.id).results[0]

    # print("script_db", script_db.id, script_db.title, script_db.description)

    scenes_db = get_last_scene_service(db=db, script_id=script_db.id, number=4)

    location_db = get_location_service(db, scenes_db.location_id)

    prompt_db_background = get_prompt_by_field(db, 'category', 'image_background')

    # print("prompt_db_background", prompt_db_background.description)

    # print("scenes_db", scenes_db)

    prompt_content = prompt_db_background.description.replace('x_escena', f" {scenes_db.content}")

    prompt_content = prompt_content.replace('x_personaje',
                                            f"{character_leading_role.name} {character_leading_role.description}")

    prompt_content = prompt_content + f" ocurre en la siguiente ubicacion {location_db.description}"

    image_generated = generate_image_dalle(prompt=prompt_content,
                                           quality="hd",
                                           size="1792x1024")

    try:
        return update_image_background_game_service(db, game_id, image_generated, "1")
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="not generated",
        )


@router.get("/my-games/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
def my_games(db: Session = Depends(get_db),
             Authorize: AuthJWT = Depends(),
             Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
             page: int = 1,
             count: int = 10,
             ):
    """
    This endpoint retrieves all games created by the user.

    It returns a list of games.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_raw_jwt()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    games_db, count_pages = get_games_service(db, skip=page, limit=count, user_id=current_user['sub'])

    return SchemaListGame(results=games_db, count=len(games_db), page=page, total_pages=count_pages)


@router.get("/featured/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
def features_games(db: Session = Depends(get_db),
                   Authorize: AuthJWT = Depends(),
                   Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                   ):
    """
    This endpoint retrieves all featured games.

    It returns a list of games.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_raw_jwt()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    games_featured_db = get_configuration_service(db)

    games_db, count_pages = get_games_service(db, skip=0, limit=1000, games_id=(games_featured_db.featured_games))

    return SchemaListGame(results=games_db, count=len(games_db), page=0, total_pages=count_pages)


@router.get("/popular/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
def popular_games(db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint retrieves all popular games.

    It returns a list of games.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_raw_jwt()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    games_featured_db = get_configuration_service(db)

    games_db, count_pages = get_games_service(db, skip=0, limit=1000, games_id=(games_featured_db.popular_games))

    return SchemaListGame(results=games_db, count=len(games_db), page=0, total_pages=count_pages)


@router.get("/categories/", status_code=status.HTTP_200_OK)
def categories_games(category: str,
                     db: Session = Depends(get_db),
                     Authorize: AuthJWT = Depends(),
                     Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                     page: int = 1,
                     count: int = 10,
                     ):
    """
    This endpoint retrieves all games by category.

    It returns a list of games.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_raw_jwt()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    games_featured_db = get_configuration_service(db)
    categories_active_db = get_categories_active_service(db)

    if category not in [category_active.name for category_active in categories_active_db.results]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    games_ids = next(
        (games_["games"] for games_ in games_featured_db.games_by_category if games_["name"] == category), [])
    games_list, count_pages = get_games_service(db, skip=page, limit=count, games_id=games_ids)

    return {"results": games_list, "count": len(games_list), "page": page, "total_pages": count_pages}
