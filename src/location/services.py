from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from location.models import Location

from location.schemas import SchemaRetrieveLocation
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation
from location.schemas import SchemaListLocation

from utils import upload_image


def get_location_by_field(db: Session, field: str, value: str):
    """
    Get a location by a field.
    """
    location = db.query(Location).filter(getattr(Location, field) == value).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location with {field} {value} not found")
    return location


def get_locations_service(db: Session, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of locations.
    """
    locations = db.query(Location).filter(Location.game_id == game_id).offset(skip).limit(limit).all()

    # prompt_db_image_location = get_prompt_by_field(db, "category", "location_image")

    # for location in locations:
    #     if not location.image:
            # content = [
            #     {
            #         "role": "system",
            #         "content": f"response con el siguiente JSON {json_response} "
            #     },
            #     {
            #         "role": "user",
            #         "content": [
            #             {
            #                 "type": "text",
            #                 "text": "Describe en 5 renglones una pared de ESCENARIO  , y en otros 5 renglones el piso adjunto a esta pared de ESCENARIO"
            #             },
            #             {
            #                 "type": "text",
            #                 "text": f"Escenario: {location.title} - {location.description}"
            #             }
            #         ]
            #     }
            # ]
            #
            # description = generate_gpt4_(content_prompt=content,
            #                              max_tokens=4096)
            #
            # description = json.loads(description)

            # content_prompt = f"{prompt_db_image_location.description} {location.description}"
            #
            # image_generate = generate_image_dalle(prompt=content_prompt,
            #                                       size="1024x1024")
            #
            # image_name = location.title.replace(" ", "_")
            #
            # location.image = upload_image(url_image=image_generate,
            #                               file_name=f"{location.game_id}/locations/{image_name}.jpg")
            #
            # db.commit()
            # db.refresh(location)

    return SchemaListLocation(results=locations, count=len(locations))


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

    image_name = location.title.replace(" ", "_")

    image_name = image_name.replace("'", "")

    location.image = upload_image(url_image=schema.image,
                                  file_name=f"{location.game_id}/locations/{image_name}.jpg")

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
