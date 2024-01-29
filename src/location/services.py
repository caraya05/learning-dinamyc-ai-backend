from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from location.models import Location

from location.schemas import SchemaRetrieveLocation
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation
from location.schemas import SchemaListLocation


def get_location_by_field(db: Session, field: str, value: str):
    """
    Get a location by a field.
    """
    location = db.query(Location).filter(getattr(Location, field) == value).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location with {field} {value} not found")
    return location


def get_locations_service(db: Session, skip: int = 0, limit: int = 100):
    """
    Get a list of locations.
    """
    locations = db.query(Location).offset(skip).limit(limit).all()
    return SchemaListLocation(results=locations, count=len(locations))


def get_location_service(db: Session, location_id: str):
    """
    Get a location.
    """
    location = get_location_by_field(db, "id", location_id)
    return SchemaRetrieveLocation.from_orm(location)


def create_location_service(db: Session, schema: SchemaCreateLocation, user_id: str, game_id: str):
    """
    Create a location.
    """
    try:
        location = Location(**schema.dict())
        location.user_id = user_id
        location.game_id = game_id
        location.created_by = user_id
        location.updated_by = user_id
        db.add(location)
        db.commit()
        db.refresh(location)
        return SchemaRetrieveLocation.from_orm(location)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location not created")


def partial_update_location_service(db: Session, location_id: str, schema: SchemaPartialUpdateLocation):
    """
    Partially update a location.
    """
    location = get_location_by_field(db, "id", location_id)
    for field, value in schema:
        setattr(location, field, value)
    db.commit()
    db.refresh(location)
    return SchemaRetrieveLocation.from_orm(location)
