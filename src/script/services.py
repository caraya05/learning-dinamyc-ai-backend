from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import asc
from fastapi import status

from script.models import Script

from script.schemas import SchemaRetrieveScript
from script.schemas import SchemaCreateScript
from script.schemas import SchemaPartialUpdateScript
from script.schemas import SchemaListScript


def get_script_by_field(db: Session, field: str, value: str):
    """
    Get a script by a field.
    """
    script = db.query(Script).filter(getattr(Script, field) == value).first()
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Script with {field} {value} not found")
    return script


def get_scripts_service(db: Session, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of scripts.
    """
    try:
        scripts = (db.query(Script).filter(Script.game_id == game_id).order_by(asc(Script.order))
                   .offset(skip).limit(limit).all())
        return SchemaListScript(results=scripts, count=len(scripts))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scripts not found.")


def get_script_service(db: Session, script_id: str):
    """
    Get a script.
    """
    script = get_script_by_field(db, "id", script_id)
    return script


def create_script_service(db: Session, schema: SchemaCreateScript, user_id: str, status_script: int = 0):
    """
    Create a script.
    """
    try:
        script = Script(**schema.dict())
        script.status = status_script
        script.status_character = status_script
        script.status_location = status_script
        script.status_scene = status_script
        script.created_by = user_id
        script.updated_by = user_id
        db.add(script)
        db.commit()
        db.refresh(script)
        return script
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def partial_update_script_service(db: Session, script_id: str, schema: SchemaPartialUpdateScript):
    """
    Partially update a script.
    """
    script = get_script_by_field(db, "id", script_id)
    script.status = schema.status if schema.status else script.status
    script.status_character = schema.status_character if schema.status_character else script.status_character
    script.status_location = schema.status_location if schema.status_location else script.status_location
    script.status_scene = schema.status_scene if schema.status_scene else script.status_scene
    db.commit()
    db.refresh(script)
    return script


def delete_script_service(db: Session, script_id: str):
    """
    Delete a script.
    """
    script = get_script_by_field(db, "id", script_id)
    db.delete(script)
    db.commit()
    return script