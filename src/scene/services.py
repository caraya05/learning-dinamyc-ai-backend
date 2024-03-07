from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import asc
from starlette import status

from scene.models import Scene

from scene.schemas import SchemaRetrieveScene
from scene.schemas import SchemaCreateScene
from scene.schemas import SchemaPartialUpdateScene
from scene.schemas import SchemaListScene
from utils import upload_image


def get_scene_by_field(db: Session, field: str, value: str):
    """
    Get a scene by a field.
    """
    scene = db.query(Scene).filter(getattr(Scene, field) == value).first()
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene with {field} {value} not found")
    return scene


def get_scenes_service(db: Session, script_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of scenes.
    """
    scenes = (db.query(Scene).filter(Scene.script_id == script_id).order_by(asc(Scene.order))
              .offset(skip).limit(limit).all())

    return SchemaListScene(results=scenes, count=len(scenes))


def get_scene_service(db: Session, scene_id: str):
    """
    Get a scene.
    """
    scene = get_scene_by_field(db, "id", scene_id)
    return scene


def create_scene_service(db: Session, schema: SchemaCreateScene, user_id: str):
    """
    Create a scene.
    """
    scene = Scene(**schema.dict())
    if schema.start_image:
        scene.start_image = upload_image(url_image=schema.start_image,
                                         file_name=f"{scene.game_id}/scene/{scene.order}_start.jpg",
                                         size=(812, 812))

    scene.created_by = user_id
    scene.updated_by = user_id
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene


def partial_update_scene_service(db: Session, scene_id: str, schema: SchemaPartialUpdateScene):
    """
    Partially update a scene.
    """
    scene = get_scene_by_field(db, "id", scene_id)
    for field, value in schema:
        setattr(scene, field, value)
    db.commit()
    db.refresh(scene)
    return scene


def get_last_scene_service(db: Session, script_id: str, number: int = 4):
    """
    Get the last scene.
    """
    try:
        scene = (db.query(Scene).filter(Scene.script_id == script_id, Scene.order == number).first())
        print(scene)
        return scene
    except AttributeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene not found")
