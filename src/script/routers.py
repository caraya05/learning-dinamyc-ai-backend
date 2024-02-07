from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from config import auth_scheme

from sqlalchemy.orm import Session

from character.schemas import SchemaCreateCharacter

from character.services import get_character_by_field
from character.services import create_character_service

from location.schemas import SchemaCreateLocation

from location.services import get_location_by_field
from location.services import create_location_service

from scene.schemas import SchemaCreateScene

from scene.services import create_scene_service

from script.schemas import SchemaListScript
from script.schemas import SchemaRetrieveScript
from script.schemas import SchemaCreateScript

from script.services import get_scripts_service
from script.services import get_script_service
from script.services import create_script_service

from script.utils import get_script_locations_chapter_v2

from game.services import get_game_service

from prompt.services import get_prompt_by_field

router = APIRouter(prefix="/script", tags=["Script"])


# Dependency
def get_db(request: Request):
    return request.state.db


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListScript)
def get_scripts(game_id: str,
                db: Session = Depends(get_db),
                Authorize: AuthJWT = Depends(),
                Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                ):
    """
    This endpoint retrieves all scripts.

    It returns a list of scripts.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    scripts_db = get_scripts_service(db, skip=0, limit=100, game_id=game_id)

    return scripts_db


@router.get("/{script_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScript)
def get_script(script_id: str,
               db: Session = Depends(get_db),
               Authorize: AuthJWT = Depends(),
               Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
               ):
    """
    This endpoint retrieves a script.

    It returns a script.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    script_db = get_script_service(db, script_id=script_id)

    return script_db


@router.post("/", status_code=status.HTTP_201_CREATED)
# ,response_model=SchemaRetrieveScript)
def create_script(game_id: str,
                  db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint creates a script.

    It expects a script in the request body.
    If the script is successfully created, it returns the script's information.

    Args:
        game_id (str): The ID of the game for which the script is being created.
        db (Session): The database session.
        Authorize (AuthJWT): The authorization object.
        Token (HTTPAuthorizationCredentials): The authorization credentials.

    Returns:
        SchemaRetrieveScript: The created script's information.

    Raises:
        HTTPException: If the token is invalid or if there is an error while creating the script.
    """

    # Check if the token is valid
    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Get the game information
    game_db = get_game_service(db, game_id=game_id)

    # Get the script prompt
    prompt_script = get_prompt_by_field(db, "category", "script")
    prompt_scene = get_prompt_by_field(db, "category", "scene")
    # prompt_image_l = get_prompt_by_field(db, "category", "location_image")
    # prompt_image_c = get_prompt_by_field(db, "category", "character_image")

    # Get the script locations and chapters
    response_script = get_script_locations_chapter_v2(game_db.synopsis, "1",
                                                      prompt_script.description,
                                                      prompt_scene.description)
    # , prompt_image_c.description, prompt_image_l.description)

    # response = get_script_locations_chapter(game_db.synopsis, "1", prompt_script.description)

    # Create the script

    print(response_script)

    script_ = response_script["script"]

    script_generate: SchemaCreateScript = SchemaCreateScript(
        title=script_["title"],
        description=script_["description"],
        order=int(script_["number"]),
        game_id=game_id,
    )
    try:
        script_db = create_script_service(db, schema=script_generate, user_id=current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script not created",
        )

    print("script created")

    # Create the locations

    locations_ = response_script["characters_locations"]["locations"]

    for i in locations_:
        try:
            location_generate = SchemaCreateLocation(
                title=i["name"],
                description=i["description"],
                image="",
                game_id=game_id,
                zoom=0.0,

            )

            create_location_service(db, location_generate, user_id=current_user)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Location not created",
            )
    print("location created")
    # Create the characters

    character_ = response_script["characters_locations"]["characters"]

    for i in character_:
        try:
            character_generate = SchemaCreateCharacter(
                name=i["name"],
                genre=i["genre"],
                type=i["type"],
                description=i["description"],
                game_id=game_id,
                attempts=3)

            create_character_service(db, character_generate, user_id=current_user)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Character not created",
            )
    print("character created")

    # Create the scenes
    scenes_ = response_script["scenes"]

    location_scene = ""
    try:
        for i in scenes_:
            for j in locations_:
                if i["id_location"] == j["id"]:
                    location_scene = get_location_by_field(db, "title", j["name"]).id
                    break
            # location_scene = get_location_by_field(db, "title", i["location"])

            characters_scene = []
            for j in i["characters"]:
                for k in character_:
                    if j["id"] == k["id"]:
                        characters_scene.append(get_character_by_field(db, "name", k["name"]).id)
                        break
                # characters_scene.append(get_character_by_field(db, "name", j["name"]).id)

            scene_generate = SchemaCreateScene(
                title=i["title"],
                description=i["description"],
                order=int(i["number"]),
                script_id=script_db.id,
                dynamic=i["dynamic"],
                content=i["content"],
                dialogues=i["dialogues"],
                characters_id=characters_scene,
                location_id=location_scene,
            )

            create_scene_service(db, scene_generate, user_id=current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scene not created",
        )
    print("scene created")
    return script_db

# @router.patch("/{script_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScript)
# async def partial_update_script(script_id: str,
#                                 schema: SchemaPartialUpdateScript,
#                                 db: Session = Depends(get_db),
#                                 Authorize: AuthJWT = Depends(),
#                                 Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
#                                 ):
#     """
#     This endpoint partially updates a script.
#
#     It expects a script in the request body.
#     If the script is successfully updated, it returns the script's information.
#     """
#
#     try:
#         Authorize.jwt_required()
#         current_user = Authorize.get_jwt_subject()
#
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid token",
#         )
#
#     script_db = partial_update_script_service(db, script_id=script_id, schema=schema)
#
#     return SchemaRetrieveScript(**script_db)
