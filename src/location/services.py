from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from location.models import Location

from location.schemas import SchemaRetrieveLocation
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation
from location.schemas import SchemaListLocation

from scene.services import get_scenes_service

from script.services import get_script_by_field

from utils import upload_image


def get_location_by_field(db: Session, field: str, value: str, game_id: str = None):
    """
    Get a location by a field.
    """
    if game_id:
        location = db.query(Location).filter(getattr(Location, field) == value, Location.game_id == game_id).first()
    else:
        location = db.query(Location).filter(getattr(Location, field) == value).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location with {field} {value} not found")
    return location


def get_locations_service(db: Session, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of locations.
    """
    locations = db.query(Location).filter(Location.game_id == game_id).offset(skip).limit(limit).all()

    script_db = get_script_by_field(db, "game_id", game_id)

    scenes_db = get_scenes_service(db, script_id=script_db.id)

    locations_order = []

    for scene in scenes_db.results:
        for location in locations:
            if location.id == scene.location_id and location not in locations_order:
                locations_order.append(location)

    for location in locations:
        if location not in locations_order:
            locations_order.append(location)

    return SchemaListLocation(results=locations_order, count=len(locations))


def get_location_service(db: Session, location_id: str):
    """
    Get a location.
    """
    location = get_location_by_field(db, "id", location_id)
    return SchemaRetrieveLocation.from_orm(location)


def create_location_service(db: Session, schema: SchemaCreateLocation, user_id: str):
    """
    Create a location.
    """
    try:
        location = Location(**schema.dict())
        location.attempts = 3
        location.user_id = user_id
        location.created_by = user_id
        location.updated_by = user_id
        db.add(location)
        db.commit()
        db.refresh(location)
        return location
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location not created")


def partial_update_location_service(db: Session, location_id: str, schema: SchemaPartialUpdateLocation):
    """
    Partially update a location.
    """
    location = get_location_by_field(db, "id", location_id)

    if schema.image:

        image_name = location.title.replace(" ", "_")

        image_name = image_name.replace("'", "")

        location.image = upload_image(url_image=schema.image,
                                      file_name=f"{location.game_id}/locations/{image_name}.jpg",
                                      size=(812, 812))
    if schema.config:
        location.config = schema.config

    db.commit()
    db.refresh(location)
    return SchemaRetrieveLocation.from_orm(location)


def update_attempts_location_service(db: Session, location_id: str):
    """
    Update the attempts of a location.
    """
    location = get_location_by_field(db, "id", location_id)
    location.attempts = location.attempts - 1
    db.commit()
    db.refresh(location)
    return location
