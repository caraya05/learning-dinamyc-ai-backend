from fastapi import APIRouter, HTTPException
from fastapi import Depends
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth_admin
from auth.utils import auth_schema
from core.database import db

from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/stats", tags=["Stats"])


def sum_arrays(*arrays):
    # Asumiendo que todos los arrays tienen la misma longitud
    long = len(arrays[0])
    result = [0] * long

    for array in arrays:
        for i in range(long):
            result[i] += array[i]

    return result


@router.get("/amount-created/", status_code=status.HTTP_200_OK)
async def amount_of_created(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    # Crear el filtro de fechas si las fechas de inicio y fin están presentes
    date_filter = {}
    if start_date is not None:
        date_filter["$gte"] = start_date
    if end_date is not None:
        date_filter["$lte"] = end_date

    # Aplicar el filtro de fechas a la consulta si está presente
    query = {"created_at": date_filter} if date_filter else {}

    amount_users = len(await db["user"].find(query).to_list(None))
    users_created_date = await db["user"].aggregate([
        {
            "$match": query
        },
        {
            "$project": {
                "created_at": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                }
            }
        },
        {
            "$group": {
                "_id": "$created_at",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {
                "_id": 1  # Ordenar por fecha en orden descendente
            }
        }
    ]).to_list(None)

    amount_locations = len(await db["location"].find(query).to_list(None))
    locations_created_date = await db["location"].aggregate([
        {
            "$match": query
        },
        {
            "$project": {
                "created_at": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                }
            }
        },
        {
            "$group": {
                "_id": "$created_at",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {
                "_id": 1  # Ordenar por fecha en orden descendente
            }
        }
    ]).to_list(None)
    locations_unique_created_by = await db["location"].aggregate([
        {
            "$match": query  # Asegúrate de que 'query' contenga tus criterios de filtrado específicos
        },
        {
            "$project": {
                "date": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "created_by": 1
            }
        },
        {
            "$group": {
                "_id": "$date",
                "unique_created_by": {"$addToSet": "$created_by"}
            }
        },
        {
            "$sort": {"_id": 1}  # Ordena por fecha en orden ascendente
        }
    ]).to_list(None)

    amount_characters = len(await db["character"].find(query).to_list(None))
    characters_created_date = await db["character"].aggregate([
        {
            "$match": query
        },
        {
            "$project": {
                "created_at": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                }
            }
        },
        {
            "$group": {
                "_id": "$created_at",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {
                "_id": 1  # Ordenar por fecha en orden descendente
            }
        }
    ]).to_list(None)
    characters_unique_created_by = await db["character"].aggregate([
        {
            "$match": query  # Asegúrate de que 'query' contenga tus criterios de filtrado específicos
        },
        {
            "$project": {
                "date": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "created_by": 1
            }
        },
        {
            "$group": {
                "_id": "$date",
                "unique_created_by": {"$addToSet": "$created_by"}
            }
        },
        {
            "$sort": {"_id": 1}  # Ordena por fecha en orden ascendente
        }
    ]).to_list(None)

    amount_weapons = len(await db["weapon"].find(query).to_list(None))
    weapons_created_date = await db["weapon"].aggregate([
        {
            "$match": query
        },
        {
            "$project": {
                "created_at": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                }
            }
        },
        {
            "$group": {
                "_id": "$created_at",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {
                "_id": 1  # Ordenar por fecha en orden descendente
            }
        }
    ]).to_list(None)

    amount_places = len(await db["place"].find(query).to_list(None))
    places_created_date = await db["place"].aggregate([
        {
            "$match": query
        },
        {
            "$project": {
                "created_at": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                }
            }
        },
        {
            "$group": {
                "_id": "$created_at",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {
                "_id": 1  # Ordenar por fecha en orden descendente
            }
        }
    ]).to_list(None)
    places_unique_created_by = await db["place"].aggregate([
        {
            "$match": query  # Asegúrate de que 'query' contenga tus criterios de filtrado específicos
        },
        {
            "$project": {
                "date": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "created_by": 1
            }
        },
        {
            "$group": {
                "_id": "$date",
                "unique_created_by": {"$addToSet": "$created_by"}
            }
        },
        {
            "$sort": {"_id": 1}  # Ordena por fecha en orden ascendente
        }
    ]).to_list(None)

    amount_games = len(await db["game"].find(query).to_list(None))
    games_created_date = await db["game"].aggregate([
        {
            "$match": query
        },
        {
            "$project": {
                "created_at": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                }
            }
        },
        {
            "$group": {
                "_id": "$created_at",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {
                "_id": 1  # Ordenar por fecha en orden descendente
            }
        }
    ]).to_list(None)
    games_unique_created_by = await db["game"].aggregate([
        {
            "$match": query  # Asegúrate de que 'query' contenga tus criterios de filtrado específicos
        },
        {
            "$project": {
                "date": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "created_by": 1
            }
        },
        {
            "$group": {
                "_id": "$date",
                "unique_created_by": {"$addToSet": "$created_by"}
            }
        },
        {
            "$sort": {"_id": 1}  # Ordena por fecha en orden ascendente
        }
    ]).to_list(None)

    amount_objects = len(await db["object"].find(query).to_list(None))
    objects_created_date = await db["object"].aggregate([
        {
            "$match": query
        },
        {
            "$project": {
                "created_at": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                }
            }
        },
        {
            "$group": {
                "_id": "$created_at",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {
                "_id": 1  # Ordenar por fecha en orden descendente
            }
        }
    ]).to_list(None)
    objects_unique_created_by = await db["object"].aggregate([
        {
            "$match": query  # Asegúrate de que 'query' contenga tus criterios de filtrado específicos
        },
        {
            "$project": {
                "date": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "created_by": 1
            }
        },
        {
            "$group": {
                "_id": "$date",
                "unique_created_by": {"$addToSet": "$created_by"}
            }
        },
        {
            "$sort": {"_id": 1}  # Ordena por fecha en orden ascendente
        }
    ]).to_list(None)

    total_data = locations_unique_created_by + characters_unique_created_by + places_unique_created_by + games_unique_created_by + objects_unique_created_by

    user_actives = {}
    for data in total_data:
        _id = data["_id"]
        unique_created_by = data["unique_created_by"]
        if _id not in user_actives:
            user_actives[_id] = {"_id": _id, "unique_created_by": set(unique_created_by)}
        else:
            user_actives[_id]["unique_created_by"].update(unique_created_by)

    # Convertir el diccionario a la estructura deseada
    result_final = list(user_actives.values())
    amount_users_active = 0
    for item in result_final:
        item["unique_created_by"] = list(item["unique_created_by"])
        item["count"] = len(item["unique_created_by"])
        amount_users_active += item["count"]
        del item["unique_created_by"]

    return {
        "amount_users": amount_users,
        "users_created_date": users_created_date,
        "amount_locations": amount_locations,
        "locations_created_date": locations_created_date,
        "amount_characters": amount_characters,
        "characters_created_date": characters_created_date,
        "amount_weapons": amount_weapons,
        "weapons_created_date": weapons_created_date,
        "amount_places": amount_places,
        "places_created_date": places_created_date,
        "amount_games": amount_games,
        "games_created_date": games_created_date,
        "amount_objects": amount_objects,
        "objects_created_date": objects_created_date,
        "amount_users_active": amount_users_active,
        "users_active_date": result_final
    }


@router.get("/amount-played/", status_code=status.HTTP_200_OK)
async def amount_of_played(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    try:
        # Crear el filtro de fechas si las fechas de inicio y fin están presentes
        date_filter = {}
        if start_date is not None:
            date_filter["$gte"] = start_date
        if end_date is not None:
            date_filter["$lte"] = end_date

        # Aplicar el filtro de fechas a la consulta si está presente
        query = {"created_at": date_filter} if date_filter else {}

        amount_played = len(await db["record_game"].find(query).to_list(None))
        games_played_date = await db["record_game"].aggregate([
            {
                "$match": query
            },
            {
                "$project": {
                    "created_at": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                    }
                }
            },
            {
                "$group": {
                    "_id": "$created_at",
                    "count": {"$sum": 1}
                }
            }
        ]).to_list(None)

        games_played = await db["record_game"].aggregate([
            {
                "$match": query
            },
            {
                "$group": {
                    "_id": "$game_id",
                    "count": {"$sum": 1}
                }
            }
        ]).to_list(None)

        return {
            "amount_played": amount_played,
            "games_played_date": games_played_date,
            "games_played": games_played
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/users/", status_code=status.HTTP_200_OK)
async def get_users(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    try:
        date_filter = {}
        if start_date is not None:
            date_filter["$gte"] = start_date
        if end_date is not None:
            date_filter["$lte"] = end_date
        query = {"created_at": date_filter} if date_filter else {}

        users = await db["user"].find().to_list(None)

        for user in users:
            user_id = str(user["_id"])
            user["_id"] = user_id
            user["games"] = await db["game"].count_documents({"created_by": user_id, **query}) or 0
            user["characters"] = await db["character"].count_documents({"created_by": user_id, **query}) or 0
            user["outdoors"] = await db["place"].count_documents({"created_by": user_id, **query}) or 0
            user["interiors"] = await db["location"].count_documents({"created_by": user_id, **query}) or 0

            del user["_id"]
            del user["photo"]
            del user["password"]
            del user["created_at"]
            del user["updated_at"]
            del user["created_by"]
            del user["updated_by"]
            del user["is_active"]
            del user["is_superuser"]
            del user["is_staff"]
            del user["uid"]
            del user["provider"]
            del user["number_of_creation_attempts"]
            del user["attempt_to_create"]

            # games_played = await db["record_game"].aggregate([
            #     {
            #         "$match": {"user_id": user_id, **query}
            #     },
            #     {
            #         "$group": {
            #             "_id": "$game_id",
            #             "count": {"$sum": 1}
            #         }
            #     }
            # ]).to_list(None) or []
            #
            # user["games_played"] = len(games_played)
        return {"stats": users}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
