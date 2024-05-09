from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from scene.schemas import SchemaListScene
from scene.schemas import SchemaRetrieveScene
from scene.schemas import SchemaCreateScene
from scene.schemas import SchemaRetrieveSceneComplete
from scene.schemas import SchemaPartialUpdateScene

from scene.services import get_scenes_service
from scene.services import get_scene_service
from scene.services import create_scene_service
from scene.services import partial_update_scene_service

router = APIRouter(prefix="/scene", tags=["Scene"])


# Dependency
def get_db(request: Request):
    return request.state.db


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
