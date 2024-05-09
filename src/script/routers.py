from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status
from fastapi import BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from script.schemas import SchemaListScript
from script.schemas import SchemaRetrieveScript
from script.schemas import SchemaRetrieveScriptComplete
from script.schemas import SchemaCreateScript
from script.schemas import SchemaPartialUpdateScript

from script.services import get_scripts_service
from script.services import get_script_by_id_service
from script.services import create_chapter_service
from script.services import partial_update_script_service
# from script.services import delete_script_service

# from scene.services import get_scenes_service
# from scene.services import delete_scene_service

# from location.services import get_locations_service
# from location.services import delete_location_service

# from character.services import get_characters_service
# from character.services import delete_character_service

from game.services import get_game_service
from game.services import update_error_message_game_service

# from object.services import get_objects_service
# from object.services import delete_object_service

# from weapon.services import delete_weapon_service
# from weapon.services import get_weapons_service

from prompt.services import get_prompt_by_category_service

from celery_worker import create_script_task

from configuration.services import get_configurations_service

from user.services import deduct_stars_service

router = APIRouter(prefix="/script", tags=["Script"])


# @router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListScript)
# def get_scripts(
#     game_id: str,
#     db: Session = Depends(get_db),
#     Authorize: AuthJWT = Depends(),
#     Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
# ):
#     """
#     This endpoint retrieves all scripts.
#
#     It returns a list of scripts.
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
#     scripts_db = get_scripts_service(db, skip=0, limit=100, game_id=game_id)
#
#     return scripts_db


# @router.get(
#     "/{script_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScriptComplete
# )
# def get_script(
#     script_id: str,
#     db: Session = Depends(get_db),
#     Authorize: AuthJWT = Depends(),
#     Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
# ):
#     """
#     This endpoint retrieves a script.
#
#     It returns a script.
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
#     script_db = get_script_service(db, script_id=script_id)
#
#     locations_ = get_locations_service(db, game_id=script_db.game_id)
#
#     objects_ = get_objects_service(db, game_id=script_db.game_id)
#
#     characters_ = get_characters_service(db, game_id=script_db.game_id)
#
#     scenes_ = get_scenes_service(db, script_id=script_id)
#
#     script_db.locations = locations_.results if locations_.results and locations_ else []
#     script_db.characters = characters_ if characters_ else []
#     script_db.scenes = scenes_.results if scenes_.results and scenes_ else []
#     script_db.objects = objects_ if objects_ else []
#
#     return script_db


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveScript)
async def create_script(
        game_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a script.

    It expects a script in the request body.
    If the script is successfully created, it returns the script's information.

    Args:
        game_id (str): The ID of the game for which the script is being created.
        db (Session): The core session.
        Authorize (AuthJWT): The authorization object.
        Token (HTTPAuthorizationCredentials): The authorization credentials.

    Returns:
        SchemaRetrieveScript: The created script's information.

    Raises:
        HTTPException: If the token is invalid or if there is an error while creating the script.
    """

    # Check if the token is valid
    try:
        # configuration_db = get_configuration_service(db)
        # deduct_stars_service(db, user_id=current_user, stars=configuration_db.sta
        # Get the game information
        game_db = await get_game_service(game_id=game_id)

        # Get the script prompt
        prompt_script = await get_prompt_by_category_service("script")
        prompt_scene = await get_prompt_by_category_service("scene")
        prompt_character_locations = await get_prompt_by_category_service("characters_principal")
        prompt_imagen_scene_cero = await get_prompt_by_category_service("imagen_scene_cero")
        prompt_text_introduction_scene_cero = await get_prompt_by_category_service("text_introduction_scene_cero")
        prompt_finish_chapter = await get_prompt_by_category_service("finish_chapter")
        prompt_text_finish_chapter = await get_prompt_by_category_service("text_finish_chapter")
        prompt_image_game_over = await get_prompt_by_category_service("image_game_over")

        script_generate: SchemaCreateScript = SchemaCreateScript(
            title="",
            description="",
            order=1,
            game_id=game_id,
        )
        try:
            chapter_db = await create_chapter_service(schema=script_generate,
                                                      user_id=str(user_db.get("_id")),
                                                      status_script=0)
        except Exception as e:
            print(f"Error creating script: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Script not created",
            )

        create_script_task.delay(
            game_id=game_id,
            token=Token.credentials,
            game_history=str(game_db.get("history")),
            prompt_script=prompt_script.get("description"),
            prompt_script_system=prompt_script.get("prompt_system"),
            prompt_scene=prompt_scene.get("description"),
            prompt_scene_system=prompt_scene.get("prompt_system"),
            script_id=str(chapter_db.get("_id")),
            prompt_imagen_scene_cero=prompt_imagen_scene_cero.get("description"),
            prompt_text_introduction_scene_cero=prompt_text_introduction_scene_cero.get("description"),
            prompt_character_locations=prompt_character_locations.get("description"),
            prompt_character_locations_system=prompt_character_locations.get("prompt_system"),
            prompt_finish_chapter=prompt_finish_chapter.get("description"),
            prompt_text_finish_chapter=prompt_text_finish_chapter.get("description"),
            prompt_image_game_over=prompt_image_game_over.get("description"),
        )

        return chapter_db
    except Exception as e:
        print(f"Error creating script: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script not created",
        )


@router.patch("/{script_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScript)
async def partial_update_script(
        script_id: str,
        schema: SchemaPartialUpdateScript,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint partially updates a script.

    It expects a script in the request body.
    If the script is successfully updated, it returns the script's information.
    """

    try:

        script_db = await partial_update_script_service(script_id=script_id, schema=schema)
        message_error = ""
        if schema.status == 2:
            message_error = "Error in the history"

        if schema.status_character == 2:
            message_error = "Error in the characters"

        if schema.status_location == 2:
            message_error = "Error in the locations"

        if schema.status_scene == 2:
            message_error = "Error in the scenes"

        if message_error:
            await update_error_message_game_service(script_db.get("game_id"), message_error)

        print(f"Script updated: {script_db}")
        return script_db

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@router.get(
    "/check/{script_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScript
)
async def check_script(
        script_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint checks a script.

    It returns a message indicating whether the script is valid or not.
    """
    script_db = await get_script_by_id_service(script_id)
    if (
            script_db['status'] == 1
            and script_db['status_character'] == 1
            and script_db['status_location'] == 1
            and script_db['status_scene'] == 1
    ):
        return script_db
    elif (
            script_db['status'] == 2
            and script_db['status_character'] == 2
            and script_db['status_location'] == 2
            and script_db['status_scene'] == 2
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Script not valid",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script not finished",
        )

# @router.delete("/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_script(
#         script_id: str,
#         db: Session = Depends(get_db),
#         Authorize: AuthJWT = Depends(),
#         Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
# ):
#     """
#     This endpoint deletes a script.
#
#     It returns a message indicating whether the script was successfully deleted or not.
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
#     # Delete the script
#     try:
#         script_db = get_script_service(db, script_id=script_id)
#
#         characters_db = get_characters_service(db, game_id=script_db.game_id)
#         if characters_db:
#             for character_ in characters_db:
#                 delete_character_service(db, character_id=character_.id)
#
#         locations_db = get_locations_service(db, game_id=script_db.game_id)
#         if locations_db.results:
#             for location_ in locations_db.results:
#                 delete_location_service(db, location_id=location_.id)
#
#         scenes_db = get_scenes_service(db, script_id=script_id)
#         if scenes_db.results:
#             for scene_ in scenes_db.results:
#                 delete_scene_service(db, scene_id=scene_.id)
#
#         objects_db = get_objects_service(db, game_id=script_db.game_id)
#         if objects_db:
#             for object_ in objects_db:
#                 delete_object_service(db, object_id=object_.id)
#
#         weapons_db = get_weapons_service(db, game_id=script_db.game_id)
#         if weapons_db:
#             for weapon_ in weapons_db:
#                 delete_weapon_service(db, weapon_id=weapon_.id)
#
#         delete_script_service(db, script_id=script_id)
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Script not deleted",
#         )
#
#     return {"message": "Script deleted"}
