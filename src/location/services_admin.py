import traceback
from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core.database import db
from location.schemas_admin import SchemaUpdateLocation
from utils import update_nested_dict


async def get_locations_service_admin():
    pipeline = [
        {"$match": {"created_at": {"$gte": datetime(2025, 1, 1)}}},
        {"$sort": {"created_at": -1}},
        {
            "$lookup": {
                "from": "state_glic",
                "let": {"location_id": {"$toString": "$_id"}},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$element_id", "$$location_id"]},
                                    {"$eq": ["$type_element", "location"]},
                                ]
                            }
                        }
                    },
                    {"$addFields": {"_id": {"$toString": "$_id"}}},
                    {"$limit": 1},
                ],
                "as": "data",
            }
        },
        {"$unwind": {"path": "$data", "preserveNullAndEmptyArrays": True}},
    ]

    locations_db = await db["location"].aggregate(pipeline).to_list(None)
    for location in locations_db:
        location["_id"] = str(location["_id"])
        if "data" in location and location["data"]:
            location["data"]["_id"] = str(location["data"]["_id"])
    return locations_db


async def get_location_service_admin(location_id: str):
    try:
        pipeline = [
            {"$match": {"_id": ObjectId(location_id)}},
            {
                "$lookup": {
                    "from": "state_glic",
                    "let": {"location_id": {"$toString": "$_id"}},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$element_id", "$$location_id"]},
                                        {"$eq": ["$type_element", "location"]},
                                    ]
                                }
                            }
                        },
                        {"$addFields": {"_id": {"$toString": "$_id"}}},
                    ],
                    "as": "data",
                }
            },
        ]

        location_db = await db["location"].aggregate(pipeline).to_list(None)
        if not location_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found",
            )

        location_db = location_db[0]
        location_db["_id"] = str(location_db["_id"])

        for location in location_db["data"]:
            try:
                audio_db = await db["sound"].find_one({"_id": location["data"]["sound_id"]})
                if audio_db:
                    location["data"]["audio"] = audio_db["file"]
                else:
                    location["data"]["audio"] = None
            except Exception as e:
                print(f"Error in get location service: {str(e)}")
                location["data"]["audio"] = None
        return location_db
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in get location service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )


async def update_location_service_admin(
    location_id: str, location: SchemaUpdateLocation, user_id: str
):
    try:
        location_db = await db["location"].find_one({"_id": ObjectId(location_id)})
        if not location_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found",
            )

        location = location.dict()
        state = location["state"]
        del location["state"]
        element_state_db = await db["state_glic"].find_one(
            {"element_id": location_id, "type_element": "location", "state": state}
        )
        location_db["updated_at"] = datetime.utcnow()
        location_db["updated_by"] = user_id
        await db["location"].update_one({"_id": ObjectId(location_id)}, {"$set": location})

        data_updated = update_nested_dict(element_state_db["data"], location)
        await db["state_glic"].update_one(
            {"_id": element_state_db["_id"]}, {"$set": {"data": data_updated}}
        )

        return True
    except Exception as e:
        print(f"Error in update location service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location not updated",
        )
