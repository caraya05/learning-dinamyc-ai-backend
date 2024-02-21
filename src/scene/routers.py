from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme

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
def get_scenes(script_id: str,
               db: Session = Depends(get_db),
               Authorize: AuthJWT = Depends(),
               Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
               ):
    """
    This endpoint retrieves all scenes.

    It returns a list of scenes.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    scenes_db = get_scenes_service(db, skip=0, limit=100, script_id=script_id)

    return scenes_db


@router.get("/{scene_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveSceneComplete)
def get_scene(scene_id: str,
              db: Session = Depends(get_db),
              Authorize: AuthJWT = Depends(),
              Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
              ):
    """
    This endpoint retrieves a scene.

    It returns a scene.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    scene_db = get_scene_service(db, scene_id=scene_id)

    return scene_db


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveScene)
def create_scene(schema: SchemaCreateScene,
                 db: Session = Depends(get_db),
                 Authorize: AuthJWT = Depends(),
                 Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                 ):
    """
    This endpoint creates a scene.

    It expects a scene in the request body.
    If the scene is successfully created, it returns the scene's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    scene_db = create_scene_service(db, schema=schema,user_id=current_user)

    return scene_db

# @router.patch("/{scene_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScene)
# def partial_update_scene(scene_id: str,
#                          schema: SchemaPartialUpdateScene,
#                          db: Session = Depends(get_db),
#                          Authorize: AuthJWT = Depends(),
#                          Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
#                          ):
#     """
#     This endpoint partially updates a scene.
#
#     It expects a scene in the request body.
#     If the scene is successfully updated, it returns the scene's information.
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
#     scene_db = partial_update_scene_service(db, scene_id=scene_id, schema=schema)
#
#     return SchemaRetrieveScene(**scene_db.dict())
