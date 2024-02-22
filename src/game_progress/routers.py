from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme

from game_progress.schemas import SchemaListGameProgress
from game_progress.schemas import SchemaRetrieveGameProgress
from game_progress.schemas import SchemaCreateGameProgress
from game_progress.schemas import SchemaPartialUpdateGameProgress

from game_progress.services import get_game_progresses_service
from game_progress.services import get_game_progress_service
from game_progress.services import create_game_progress_service
from game_progress.services import partial_update_game_progress_service

router = APIRouter(prefix="/game_progress", tags=["Game Progress"])


# Dependency
def get_db(request: Request):
    return request.state.db


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListGameProgress)
def get_game_progresses(db: Session = Depends(get_db),
                        Authorize: AuthJWT = Depends(),
                        Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                        ):
    """
    This endpoint retrieves all game_progresses.

    It returns a list of game_progresses.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    game_progresses_db = get_game_progresses_service(db, skip=0, limit=100,user_id=current_user)

    return game_progresses_db


@router.get("/{game_progress_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGameProgress)
def get_game_progress(game_progress_id: str,
                      db: Session = Depends(get_db),
                      Authorize: AuthJWT = Depends(),
                      Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                      ):
    """
    This endpoint retrieves a single game_progress.

    It returns a game_progress.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    game_progress_db = get_game_progress_service(db, game_progress_id=game_progress_id)

    return game_progress_db


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveGameProgress)
def create_game_progress(game_progress: SchemaCreateGameProgress,
                         db: Session = Depends(get_db),
                         Authorize: AuthJWT = Depends(),
                         Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                         ):
    """
    This endpoint creates a game_progress.

    It returns a game_progress.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    game_progress_db = create_game_progress_service(db, schema=game_progress,user_id=current_user)

    return game_progress_db


@router.patch("/{game_progress_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveGameProgress)
def partial_update_game_progress(game_progress_id: str,
                                 game_progress: SchemaPartialUpdateGameProgress,
                                 db: Session = Depends(get_db),
                                 Authorize: AuthJWT = Depends(),
                                 Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                                 ):
    """
    This endpoint updates a game_progress.

    It returns a game_progress.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    game_progress_db = partial_update_game_progress_service(db, game_progress_id=game_progress_id, schema=game_progress)

    return game_progress_db
