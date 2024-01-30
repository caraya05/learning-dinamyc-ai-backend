import json

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme
from game.schemas import SchemaListGame, SchemaRetrieveGame, SchemaCreateGame, SchemaPartialUpdateGame
from game.services import get_games_service, get_game_service, create_game_service, update_partial_game_service
from gpt_ai.utils import generate_image_dalle
from gpt_ai.utils import generate_gpt4_
from prompt.services import get_prompt_by_field

router = APIRouter(prefix="/game", tags=["Game"])


# Dependency
def get_db(request: Request):
    return request.state.db


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListGame)
async def get_games(db: Session = Depends(get_db),
                    Authorize: AuthJWT = Depends(),
                    Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
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

    games_db = get_games_service(db, skip=0, limit=100)

    return SchemaListGame(results=games_db, count=len(games_db))


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

    game_db = create_game_service(db=db, game=game, user_id=current_user['sub'])

    return game_db


@router.get("/generate-cover/{game_id}", status_code=status.HTTP_200_OK)
def cover_generate(
        game_id: str,
        count: int = 4,
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

    game_db = get_game_service(db, game_id, current_user['sub'])

    prompt_db_cover = get_prompt_by_field(db, 'category', 'cover')

    prompt_middle = "si hay algo que no te gusta, puedes cambiarlo"

    prompt = (f"{prompt_db_cover.description}\n"
              f"personajes: {game_db.characters}\n"
              f"ubicacion: {game_db.location}\n"
              f"historia: {game_db.story_line}\n"
              f"{prompt_middle}\n"

              )

    print(prompt)

    json_schema = {

        "new": "string (new prompt with adjustments)",
    }

    prompt_review = [
        {
            "role": "system",
            "content": f"Eres un revisor de la portada del juego, "
                       f"si hay algo que no te gusta, puedes cambiarlo"
                       f"evalua la portada del juego en dado caso de que halla algo que infrinja las siguientes reglas,"
                       f"To maximize innovation and creativity, we believe you should have the flexibility to use our services as you see fit, so long as you comply with the law and don’t harm yourself or others. When using any OpenAI service, like ChatGPT, labs.openai.com, and the OpenAI API, these rules apply:"
                       f"Comply with applicable laws – for example, don’t compromise the privacy of others,  engage in regulated activity without complying with applicable regulations, or promote or engage in any illegal activity, including the exploitation or harm of children and the development or distribution of illegal substances, goods, or services."
                       f"Don’t use our service to harm yourself or others – for example, don’t use our services to promote suicide or self-harm, develop or use weapons, injure others or destroy property, or engage in unauthorized activities that violate the security of any service or system. "
                       f"Don’t repurpose or distribute output from our services to harm others – for example, don’t share output from our services to defraud, scam, spam, mislead, bully, harass, defame, discriminate based on protected attributes, sexualize children, or promote violence, hatred or the suffering of others."
                       f"Respect our safeguards - don’t circumvent safeguards or safety mitigations in our services unless supported by OpenAI (e.g., domain experts in our Red Teaming Network) or related to research conducted in accordance with our Sharing & Publication Policy. We report apparent child sexual abuse material (CSAM) to the National Center for Missing and Exploited Children."
                       f"cambialo. y responde en formato JSON con el esquema '{json_schema}'",
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]

    new_cover = generate_gpt4_(content_prompt=prompt_review)

    new_cover = json.loads(new_cover)

    print(new_cover)

    images = []
    for _ in range(count):
        try:
            image_generated = generate_image_dalle(prompt=new_cover["new"] + " no genera textos y letreros", quality="hd", size="1024x1792")
            images.append(image_generated)
        except Exception as e:
            pass
            # raise HTTPException(
            #     status_code=status.HTTP_400_BAD_REQUEST,
            #     detail="Image not generated",
            # )

    return {"images": images}


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
