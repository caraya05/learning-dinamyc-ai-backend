from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

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


def get_scripts_service(db: Session, skip: int = 0, limit: int = 100):
    """
    Get a list of scripts.
    """
    scripts = db.query(Script).offset(skip).limit(limit).all()
    return SchemaListScript(results=scripts, count=len(scripts))


def get_script_service(db: Session, script_id: str):
    """
    Get a script.
    """
    script = get_script_by_field(db, "id", script_id)
    return SchemaRetrieveScript.from_orm(script)


def create_script_service(db: Session, schema: SchemaCreateScript):
    """
    Create a script.
    """
    script = Script(**schema.dict())
    db.add(script)
    db.commit()
    db.refresh(script)
    return SchemaRetrieveScript.from_orm(script)


def partial_update_script_service(db: Session, script_id: str, schema: SchemaPartialUpdateScript):
    """
    Partially update a script.
    """
    script = get_script_by_field(db, "id", script_id)
    for field, value in schema:
        setattr(script, field, value)
    db.commit()
    db.refresh(script)
    return SchemaRetrieveScript.from_orm(script)


