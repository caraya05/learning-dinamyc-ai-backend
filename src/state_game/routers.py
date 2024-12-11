from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema


from state_game.services import create_state_game, get_order_new_state_game
from state_game.services import get_states_game_by_game_id

from state_game.schemas import SchemaStateGameList
from state_game.schemas import SchemaStateGameCreate
from state_game.schemas import SchemaStateGameRetrieve

router = APIRouter(prefix="/state-game", tags=["State Game"])


@router.post("/", response_description="Add new state game", response_model=SchemaStateGameRetrieve, status_code=status.HTTP_201_CREATED)
async def add_state_game(state_game: SchemaStateGameCreate, user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)):
    order_new_state_game = await get_order_new_state_game(state_game.game_id)
    state_game = await create_state_game(state_game.game_id, order_new_state_game, str(user_db.get("_id")))
    return state_game


@router.get("/{game_id}", response_description="Get state game by game id", response_model=SchemaStateGameList, status_code=status.HTTP_200_OK)
async def get_state_game(game_id: str, user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)):
    state_game = await get_states_game_by_game_id(game_id)
    return SchemaStateGameList(results=state_game, count=len(state_game))