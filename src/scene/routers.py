from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from scene.schemas import SchemaListScene
from scene.schemas import SchemaCreateScene
from scene.schemas import SchemaRetrieveSceneComplete
from scene.schemas import SchemaPartialUpdateScene

from scene.services import get_scenes_service
from scene.services import get_scene_service
from scene.services import create_scene_service
from scene.services import partial_update_scene_service

router = APIRouter(prefix="/scene", tags=["Scene"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListScene)
async def get_scenes(
        script_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all scenes.

    It returns a list of scenes.
    """

    try:
        scenes_db, counts = await get_scenes_service(skip=0, limit=100, script_id=script_id)
        for i in scenes_db:
            i["_id"] = str(i["_id"])
        return SchemaListScene(results=scenes_db, count=counts)

    except Exception as e:
        print(f"Error in get scenes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenes not found.",
        )


@router.get(
    "/{scene_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveSceneComplete
)
async def get_scene(
        scene_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a scene.

    It returns a scene.
    """

    try:
        scene_db = await get_scene_service(scene_id=scene_id)
        return scene_db

    except Exception as e:
        print(f"Error in get scene: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene not found.",
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveSceneComplete)
async def create_scene(
        schema: SchemaCreateScene,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a scene.

    It expects a scene in the request body.
    If the scene is successfully created, it returns the scene's information.
    """

    try:
        scene_db = await create_scene_service(schema=schema, user_id=str(user_db.get("_id")))
        return scene_db

    except Exception as e:
        print(f"Error in create scene: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scene not created.",
        )


@router.patch("/{scene_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveSceneComplete)
def partial_update_scene(scene_id: str,
                         schema: SchemaPartialUpdateScene,
                         user_db: dict = Depends(auth),
                         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
                         ):
    """
    This endpoint partially updates a scene.

    It expects a scene in the request body.
    If the scene is successfully updated, it returns the scene's information.
    """

    try:
        scene_db = partial_update_scene_service(scene_id=scene_id, schema=schema)

        return scene_db

    except Exception as e:
        print(f"Error in partial update scene: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scene not updated.",
        )


# @router.get("/generate-scene-initial/{game_id}", status_code=status.HTTP_200_OK)
# async def generate_scene_initial(
#         game_id: str,
#         user_db: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     """
#     This endpoint generates the initial scene for a game.
#
#     It returns the initial scene.
#     """
#
#     text_initial, image_initial = await generate_scene_cero(game_id)
#
#     return {
#         "scene_cero": text_initial,
#         "scene_cero_image": image_initial,
#     }
#
#
# @router.get("/generate-scene-final/{game_id}", status_code=status.HTTP_200_OK)
# async def generate_scene_finall(
#         game_id: str,
#         user_db: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     """
#     This endpoint generates the final scene for a game.
#
#     It returns the final scene.
#     """
#
#     # game_db = await db["game"].find_one({"_id": ObjectId(game_id)})
#     # characters_db = await db["character"].find({"game_id": game_id}).to_list(None)
#     #
#     # prompt_finish_chapter = ("Genera una escena final del primer capitulo, en la cual ocurra un evento que "
#     #                          "genere expectativa  al jugador para comienzo del segundo capitulo, en no más de 50 palabras. (En inglés)")
#     #
#     # schema_text_finish_chapter = {"description": "string (description of the finish chapter)"}
#     #
#     # prompt_content = [
#     #     {
#     #         "role": "system",
#     #         "content": f"responde el prompt con la siguiente estructura JSON: {schema_text_finish_chapter}",
#     #     },
#     #     {
#     #         "role": "user",
#     #         "content": [
#     #             {"type": "text", "text": prompt_finish_chapter},
#     #             {
#     #                 "type": "text",
#     #                 # "text": f"escena final: {scenes_db[4]['description']} \n"
#     #                 #         f"historia: {game_db['history']} \n",
#     #                 "text":
#     #                     f"historia: {game_db['history']} \n",
#     #             },
#     #         ],
#     #     },
#     # ]
#     #
#     # response_text_finish_chapter = generate_gpt4_(
#     #     content_prompt=prompt_content, type_text="finish chapter", max_tokens=4096
#     # )
#     #
#     # response_text_finish_chapter = json.loads(response_text_finish_chapter)
#     #
#     # json_finish_chapter = {"description_image": "string (description of the finish chapter)"}
#     #
#     # prompt_content_finish_chapter = [
#     #     {
#     #         "role": "system",
#     #         "content": f"responde el prompt con la siguiente estructura JSON: {json_finish_chapter}",
#     #     },
#     #     # {
#     #     #     "role": "system",
#     #     #     "content": f"No ir en contra de estas politicas al momento de generar el texto: \n"
#     #     #                f"Sea responsable y ético al usar OpenAI. Siga las leyes, evite dañarse a sí mismo o a otros, y use los resultados para el bien. No comparta resultados para dañar a otros y respete las medidas de seguridad implementadas. De esta manera, podemos asegurarnos de que OpenAI se use para crear un impacto positivo en el mundo.",
#     #     # },
#     #     {
#     #         "role": "user",
#     #         "content": [
#     #             {"type": "text", "text": f"Personajes: {characters_db}"},
#     #             {"type": "text", "text": f"historia: {game_db['history']}"},
#     #             {"type": "text", "text": f"contexto final: {response_text_finish_chapter['description']}"},
#     #             {
#     #                 "type": "text",
#     #                 "text": "con esta información, escribe un texto para generacion de una imagen que describa"
#     #                         " la escena de final de juego. \n",
#     #             },
#     #         ],
#     #     },
#     # ]
#     #
#     # response_finish_chapter = generate_gpt4_(
#     #     content_prompt=prompt_content_finish_chapter, type_text="finish chapter", max_tokens=4096
#     # )
#     #
#     # response_finish_chapter = json.loads(response_finish_chapter)
#     #
#     # image_finish_chapter = generate_image_dalle(
#     #     prompt=response_finish_chapter["description_image"] + ", en arte voxel",
#     #     quality="hd",
#     #     size="1024x1792",
#     # )
#
#     text_initial, image_initial = await generate_scene_final(game_id)
#
#     return {
#         "finish_chapter": text_initial,
#         "finish_chapter_image": image_initial,
#     }
