from datetime import datetime

from bson import ObjectId

from core.database import db
from location.schemas_admin import SchemaUpdateLocation


async def get_locations_service_admin():
    locations_db = await db["location"].find().to_list(None)
    for i in range(len(locations_db)):
        locations_db[i]["_id"] = str(locations_db[i]["_id"])
    return locations_db


async def get_location_service_admin(location_id: str):
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})
    if location_db is None:
        return None
    location_db["_id"] = str(location_db["_id"])
    return location_db


async def update_location_service_admin(location_id: str, location: SchemaUpdateLocation, user_id:str):
    if location_db := await get_location_service_admin(location_id):
        for key, value in location.dict().items():
            location_db[key] = value
        location_db["updated_by"] = user_id
        location_db["updated_at"] = datetime.utcnow()