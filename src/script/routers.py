from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status
from fastapi import BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from config import auth_scheme

from sqlalchemy.orm import Session

from script.schemas import SchemaListScript
from script.schemas import SchemaRetrieveScript
from script.schemas import SchemaRetrieveScriptComplete
from script.schemas import SchemaCreateScript
from script.schemas import SchemaPartialUpdateScript

from script.services import get_scripts_service, partial_update_script_service
from script.services import get_script_service
from script.services import create_script_service
from script.services import get_script_by_field
from script.services import delete_script_service

from scene.services import get_scenes_service

from location.services import get_locations_service

from character.services import get_characters_service

from game.services import get_game_service

from object.services import get_objects_service

from weapon.services import get_weapon_by_field

from prompt.services import get_prompt_by_field

from celery_worker import create_script_task

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


@router.get("/{script_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScriptComplete)
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

    locations_ = get_locations_service(db, game_id=script_db.game_id)

    objects_ = get_objects_service(db, game_id=script_db.game_id)

    characters_ = get_characters_service(db, game_id=script_db.game_id)

    scenes_ = get_scenes_service(db, script_id=script_id)

    script_db.locations = locations_.results if locations_.results and locations_ else []
    script_db.characters = characters_ if characters_ else []
    script_db.scenes = scenes_.results if scenes_.results and scenes_ else []
    script_db.objects = objects_ if objects_ else []

    return script_db


@router.post("/", status_code=status.HTTP_201_CREATED)
# ,response_model=SchemaRetrieveScript)
async def create_script(game_id: str,
                        background_tasks: BackgroundTasks,
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
    # response_script = get_script_locations_chapter_v2(game_db.history, "1",
    #                                                   prompt_script.description,
    #                                                   prompt_scene.description)
    # , prompt_image_c.description, prompt_image_l.description)

    # response = get_script_locations_chapter(game_db.synopsis, "1", prompt_script.description)

    # Create the script

    # print(response_script)

    # script_ = response_script["script"]

    script_generate: SchemaCreateScript = SchemaCreateScript(
        title="",
        description="",
        order=1,
        game_id=game_id,
    )
    try:
        script_db = create_script_service(db, schema=script_generate, user_id=current_user, status_script=0)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script not created",
        )

    print()

    create_script_task.delay(token=Authorize._token,
                             game_history=game_db.history,
                             prompt_script=prompt_script.description,
                             prompt_scene=prompt_scene.description,
                             game_id=game_id,
                             script_id=script_db.id,
                             current_user=current_user)

    # print("tasks_", tasks_.get())

    # print("script created")
    #
    # # Create the locations
    #
    # locations_ = response_script["characters_locations"]["locations"]
    #
    # for i in locations_:
    #     try:
    #         location_generate = SchemaCreateLocation(
    #             title=i["name"],
    #             description=i["description"],
    #             image="",
    #             game_id=game_id,
    #             zoom=0.0,
    #
    #         )
    #
    #         create_location_service(db, location_generate, user_id=current_user)
    #     except Exception as e:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="Location not created",
    #         )
    # print("location created")
    # # Create the characters
    #
    # character_ = response_script["characters_locations"]["characters"]
    #
    # for i in character_:
    #     try:
    #         character_generate = SchemaCreateCharacter(
    #             name=i["name"],
    #             genre=i["genre"],
    #             type=i["type"],
    #             description=i["description"],
    #             game_id=game_id,
    #             attempts=3)
    #
    #         create_character_service(db, character_generate, user_id=current_user)
    #     except Exception as e:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="Character not created",
    #         )
    # print("character created")
    #
    # # Create the scenes
    # scenes_ = response_script["scenes"]
    #
    # location_scene = ""
    # try:
    #     count = 1
    #     for i in scenes_:
    #         for j in locations_:
    #             # print("location", j["id"])
    #             # print("location 2", i["id_location"])
    #             if str(i["id_location"]) == str(j["id"]):
    #                 # print("location", j)
    #                 location_scene = get_location_by_field(db, "title", j["name"]).id
    #                 # print("location_scene", location_scene)
    #                 # break
    #         # location_scene = get_location_by_field(db, "title", i["location"])
    #
    #         characters_scene = []
    #         for j in i["characters"]:
    #             for k in character_:
    #                 # print("character", k["id"])
    #                 # print("character 2", j["id"])
    #                 if str(j["id"]) == str(k["id"]):
    #                     # print("character", k)
    #                     characters_scene.append(get_character_by_field(db, "name", k["name"]).id)
    #                     # print("characters_scene", characters_scene)
    #                     # break
    #             # characters_scene.append(get_character_by_field(db, "name", j["name"]).id)
    #
    #         scene_generate = SchemaCreateScene(
    #             title=i["title"],
    #             description=i["description"],
    #             order=count,
    #             script_id=script_db.id,
    #             dynamic=i["dynamic"],
    #             content=i["content"],
    #             dialogues=i["dialogues"],
    #             characters_id=characters_scene,
    #             location_id=location_scene,
    #         )
    #         count += 1
    #
    #         print("scene_generate " + str(count))
    #
    #         create_scene_service(db, scene_generate, user_id=current_user)
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Scene not created",
    #     )
    # print("all created")
    return script_db


@router.patch("/{script_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScript)
async def partial_update_script(script_id: str,
                                schema: SchemaPartialUpdateScript,
                                db: Session = Depends(get_db),
                                Authorize: AuthJWT = Depends(),
                                Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                                ):
    """
    This endpoint partially updates a script.

    It expects a script in the request body.
    If the script is successfully updated, it returns the script's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    script_db = partial_update_script_service(db, script_id=script_id, schema=schema)

    return script_db


@router.get("/check/{script_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScript)
def check_script(script_id: str,
                 db: Session = Depends(get_db),
                 Authorize: AuthJWT = Depends(),
                 Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                 ):
    """
    This endpoint checks a script.

    It returns a message indicating whether the script is valid or not.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Check the script
    script_db = get_script_by_field(db, "id", script_id)
    if (script_db.status == 1 and script_db.status_character == 1
            and script_db.status_location == 1 and script_db.status_scene == 1):
        return script_db
    elif (script_db.status == 2 or script_db.status_character == 2
          or script_db.status_location == 2 or script_db.status_scene == 2):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Script not valid",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script not finished",
        )


@router.delete("/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_script(script_id: str,
                  db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint deletes a script.

    It returns a message indicating whether the script was successfully deleted or not.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Delete the script
    try:
        delete_script_service(db, script_id=script_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script not deleted",
        )

    return {"message": "Script deleted"}
