from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException, status
from core.database import db
from utils import update_nested_dict
from object.schemas import SchemaCreateItemAdmin

async def get_object_service_admin(object_id: str):
    try:
        pipeline = [
            {"$match": {"_id": ObjectId(object_id)}},
            {
                "$lookup": {
                    "from": "state_glic",
                    "let": {"obj_id": {"$toString": "$_id"}},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$element_id", "$$obj_id"]},
                                        {"$eq": ["$type_element", "item"]}
                                    ]
                                }
                            }
                        },
                        {"$addFields": {"_id": {"$toString": "$_id"}}},
                    ],
                    "as": "data"
                }
            }
        ]
        object_db = await db["item"].aggregate(pipeline).to_list(None)
        if not object_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Object not found"
            )
        object_db = object_db[0]
        object_db["_id"] = str(object_db["_id"])
        for obj in object_db["data"]:
            obj["data"]["created_at"] = object_db["created_at"]
            obj["data"]["updated_at"] = object_db["updated_at"]
            obj["data"]["created_by"] = object_db["created_by"]
            obj["data"]["updated_by"] = object_db["updated_by"]
        return object_db
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error al obtener el objeto"
        )


async def get_objects_service_admin(skip: int = 1, limit: int = 100):
    pipeline = [
        {"$sort": {"created_at": -1}},
        {"$skip": skip - 1},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "state_glic",
                "let": {"obj_id": {"$toString": "$_id"}},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$element_id", "$$obj_id"]},
                                    {"$eq": ["$type_element", "item"]}
                                ]
                            }
                        }
                    },
                    {"$addFields": {"_id": {"$toString": "$_id"}}},
                    {"$limit": 1},
                ],
                "as": "data"
            }
        },
        {"$unwind": {"path": "$data", "preserveNullAndEmptyArrays": True}},
    ]
    objects_db = await db["item"].aggregate(pipeline).to_list(None)
    for obj in objects_db:
        obj["_id"] = str(obj["_id"])
        if "data" in obj and obj["data"]:
            obj["data"]["_id"] = str(obj["data"]["_id"])
    return objects_db


async def create_object_service_admin(object_data: dict, user_id: str):
    try:
        object_data["created_by"] = user_id
        object_data["updated_by"] = user_id
        result = await db["item"].insert_one(object_data)
        new_object = await get_object_service_admin(str(result.inserted_id))
        return new_object
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo crear el objeto"
        )


async def update_object_service_admin(
                object_id: str, object_data: SchemaCreateItemAdmin, user_id: str
        ):
            try:
                # Buscar el objeto existente
                object_db = await db["item"].find_one({"_id": ObjectId(object_id)})
                if not object_db:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Objeto no encontrado",
                    )

                # Extraer y eliminar el estado del objeto
                object_data = object_data.dict()
                state = object_data["state"]
                del object_data["state"]

                # Buscar el estado relacionado en la colección state_glic
                element_state_db = await db["state_glic"].find_one(
                    {"element_id": object_id, "type_element": "item", "state": state}
                )

                # Actualizar los datos del objeto
                object_db["updated_by"] = user_id
                object_db["updated_at"] = datetime.utcnow()
                await db["item"].update_one(
                    {"_id": ObjectId(object_id)},
                    {"$set": object_db},
                )

                # Actualizar los datos del estado relacionado
                data_updated = update_nested_dict(element_state_db["data"], object_data)
                await db["state_glic"].update_one(
                    {"_id": element_state_db["_id"]},
                    {"$set": {"data": data_updated}},
                )

                return True
            except Exception as e:
                print(f"Error in update object service: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se pudo actualizar el objeto",
                )