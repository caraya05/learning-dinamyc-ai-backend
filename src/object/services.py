from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from object.models import Object

from object.schemas import SchemaRetrieveObject
from object.schemas import SchemaCreateObject
from object.schemas import SchemaPartialUpdateObject
from object.schemas import SchemaListObject

from utils import upload_image


def get_object_by_field(db: Session, field: str, value: str):
    """
    Get a object by a field.
    """
    object = db.query(Object).filter(getattr(Object, field) == value).first()
    if not object:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Object with {field} {value} not found")
    return object


def get_objects_service(db: Session, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of objects.
    """
    objects = db.query(Object).filter(Object.game_id == game_id).offset(skip).limit(limit).all()
    return objects


def create_object_service(db: Session, object: SchemaCreateObject, user_id: str):
    """
    Create a new object.
    """
    db_object = Object(**object.dict())
    if object.image:
        db_object.image = upload_image(object.image, f"{object.game_id}/object/{object.name}.jpg")
    db_object.created_by = user_id
    db_object.updated_by = user_id
    db.add(db_object)
    db.commit()
    db.refresh(db_object)
    return db_object


def retrieve_object_service(db: Session, object_id: str):
    """
    Retrieve a object.
    """
    object = get_object_by_field(db, "id", object_id)
    return object


def partial_update_object_service(db: Session, object_id: str, object: SchemaPartialUpdateObject):
    """
    Partial update a object.
    """
    db_object = get_object_by_field(db, "id", object_id)
    for field, value in object.dict().items():
        setattr(db_object, field, value) if value else None
    db.commit()
    db.refresh(db_object)
    return db_object


def delete_object_service(db: Session, object_id: str):
    """
    Delete a object.
    """
    db_object = get_object_by_field(db, "id", object_id)
    db.delete(db_object)
    db.commit()
    return db_object
