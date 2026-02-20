import logging
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from core.database import db
from series.models import Series
from series.schemas import SchemaCreateSeries, SchemaUpdateSeries
from utils import delete_asset_from_url


class SeriesService:
    def __init__(self, db_instance=None):
        self.db = db_instance or db
        self.logger = logging.getLogger(__name__)

    async def create_series_service(self, series: SchemaCreateSeries, user_id: str) -> dict:
        """
        Create a new series in the database.

        Args:
            series: SchemaCreateSeries object with series data
            user_id: ID of the user creating the series

        Returns:
            dict: The created series document from the database
        """
        try:
            series_db = Series(
                title=series.title,
                description=series.description,
                image=series.image,
                category_id=series.category_id,
                main_character=series.main_character,
                rating=series.rating,
                games_id=[],
                hidden_games=[],
                created_by=user_id,
                updated_by=user_id,
            )

            result = await self.db["series"].insert_one(series_db.dict())

            series_created = await self.db["series"].find_one({"_id": result.inserted_id})

            return series_created
        except Exception as e:
            self.logger.error(f"Error creating series: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating series",
            )

    async def get_series_service(self, series_id: str) -> dict | None:
        """
        Get a series by ID.

        Args:
            series_id: ID of the series to retrieve

        Returns:
            dict: Series document or None if not found
        """
        try:
            if not ObjectId.is_valid(series_id):
                return None

            series_db = await self.db["series"].find_one({"_id": ObjectId(series_id)})
            return series_db
        except Exception as e:
            self.logger.error(f"Error getting series: {str(e)}")
            return None

    async def update_series_service(self, series_id: str, series_update: SchemaUpdateSeries, user_id: str) -> dict:
        """
        Update a series.

        Args:
            series_id: ID of the series to update
            series_update: SchemaUpdateSeries object with fields to update
            user_id: ID of the user updating the series

        Returns:
            dict: The updated series document
        """
        try:
            if not ObjectId.is_valid(series_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid series ID",
                )

            series_db = await self.db["series"].find_one({"_id": ObjectId(series_id)})

            if not series_db:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Series not found",
                )

            update_data = series_update.dict(exclude_unset=True)
            update_data["updated_by"] = user_id
            update_data["updated_at"] = datetime.utcnow()

            await self.db["series"].update_one(
                {"_id": ObjectId(series_id)},
                {"$set": update_data}
            )

            series_updated = await self.db["series"].find_one({"_id": ObjectId(series_id)})
            return series_updated
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error updating series: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error updating series",
            )

    async def add_game_to_series_service(self, series_id: str, game_id: str) -> dict:
        """
        Add a game ID to a series' games_id list.

        Args:
            series_id: ID of the series
            game_id: ID of the game to add

        Returns:
            dict: The updated series document
        """
        try:
            if not ObjectId.is_valid(series_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid series ID",
                )

            series_db = await self.db["series"].find_one({"_id": ObjectId(series_id)})

            if not series_db:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Series not found",
                )

            # Add game_id if not already in the list
            if game_id not in series_db.get("games_id", []):
                await self.db["series"].update_one(
                    {"_id": ObjectId(series_id)},
                    {
                        "$push": {"games_id": game_id},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )

            series_updated = await self.db["series"].find_one({"_id": ObjectId(series_id)})
            return series_updated
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error adding game to series: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error adding game to series",
            )

    async def get_series_by_id_service(self, series_id: str) -> dict | None:
        """
        Get a series by ID (alias for get_series_service).

        Args:
            series_id: ID of the series to retrieve

        Returns:
            dict: Series document or None if not found
        """
        return await self.get_series_service(series_id)

    async def get_all_series_service(self, skip: int = 0, limit: int = 10, active_only: bool = True) -> tuple[list, int]:
        """
        Get all series with pagination.

        Args:
            skip: Number of documents to skip
            limit: Number of documents to return
            active_only: Whether to return only active series

        Returns:
            tuple: (list of series, total count)
        """
        try:
            query = {"is_active": True} if active_only else {}

            total = await self.db["series"].count_documents(query)

            series_list = await self.db["series"].find(query).skip(skip).limit(limit).to_list(None)

            return series_list, total
        except Exception as e:
            self.logger.error(f"Error getting all series: {str(e)}")
            return [], 0

    async def get_series_by_user_service(self, user_id: str, skip: int = 0, limit: int = 10) -> tuple[list, int]:
        """
        Get all series created by a specific user with pagination.
        Series are sorted by creation date in descending order (newest first).

        Args:
            user_id: ID of the user
            skip: Number of documents to skip
            limit: Number of documents to return

        Returns:
            tuple: (list of series, total count)
        """
        try:
            query = {"created_by": user_id, "is_active": True}

            total = await self.db["series"].count_documents(query)

            series_list = await self.db["series"].find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(None)

            return series_list, total
        except Exception as e:
            self.logger.error(f"Error getting series by user: {str(e)}")
            return [], 0

    async def get_series_with_games_service(self, series_id: str) -> dict | None:
        """
        Get a series with all its associated games and their game_provisional data.
        Only returns games that have valid game_provisional.

        Args:
            series_id: ID of the series

        Returns:
            dict: Series document with games field containing game information and game_provisional
        """
        try:
            if not ObjectId.is_valid(series_id):
                return None

            series_db = await self.db["series"].find_one({"_id": ObjectId(series_id)})

            if not series_db:
                return None

            # Obtener los juegos de la serie
            games_ids = series_db.get("games_id", [])
            games = []
            hidden_games = set(series_db.get("hidden_games", []))

            if games_ids:
                db_games = await self.db["game"].find({
                    "_id": {"$in": [ObjectId(gid) if ObjectId.is_valid(gid) else gid for gid in games_ids]},
                    "is_active": True
                }).sort([("order", 1)]).to_list(None)

                # Para cada juego, obtener su game_provisional
                for game in db_games:
                    game_id = str(game.get("_id", ""))
                    provisional_id = game.get("provisional_id")

                    # Obtener el game_provisional
                    game_provisional = None
                    if provisional_id:
                        game_provisional = await self.db["game_provisional"].find_one({
                            "_id": ObjectId(provisional_id) if ObjectId.is_valid(provisional_id) else provisional_id
                        })

                    # Solo agregar el juego si tiene game_provisional válido
                    if game_provisional:
                        game_data = {
                            "_id": game_id,
                            "title": game.get("title"),
                            "history": game.get("history"),
                            "image": game.get("image"),
                            "category_id": game.get("category_id"),
                            "order": game.get("order", 1),
                            "provisional_id": str(provisional_id) if provisional_id else None,
                            "is_hidden": game_id in hidden_games,
                            "game_provisional": {
                                "_id": str(game_provisional.get("_id", "")),
                                "title": game_provisional.get("title"),
                                "script": game_provisional.get("script"),
                                "category": game_provisional.get("category"),
                                "image": game_provisional.get("image"),
                                "state": game_provisional.get("state"),
                                "progress": game_provisional.get("progress"),
                                "type_template": game_provisional.get("type_template")
                            }
                        }
                        games.append(game_data)

            # Convertir series_db a diccionario si es necesario
            if hasattr(series_db, 'dict'):
                series_response = series_db.dict()
            else:
                series_response = dict(series_db)

            # Agregar información de juegos a la serie
            series_response["_id"] = str(series_response.get("_id", ""))
            series_response["games"] = games

            user_db = await self.db["user"].find_one({"_id": ObjectId(series_response.get("created_by"))})
            if user_db:
                series_response["created_by"] = user_db.get("username")

            return series_response
        except Exception as e:
            self.logger.error(f"Error getting series with games: {str(e)}")
            return None

    async def publish_series_service(self, series_id: str, publish_type: str, user_id: str, requested_is_published: bool | None = None) -> dict:
        """
        Publish or unpublish a series. publish_type controls is_published/is_link flags.

        Args:
            series_id: ID of the series to publish/unpublish
            publish_type: Type of publish action ("public", "private", "link")
            user_id: ID of the user publishing the series
            requested_is_published: Optional explicit publish status

        Returns:
            dict: The updated series document
        """
        try:
            if not ObjectId.is_valid(series_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid series ID",
                )

            series_db = await self.db["series"].find_one({"_id": ObjectId(series_id)})

            if not series_db:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Series not found",
                )

            effective_is_published = publish_type != "private"
            is_link = publish_type == "link"

            # Optionally warn about mismatched legacy flag
            if requested_is_published is not None and requested_is_published != effective_is_published:
                self.logger.warning("publish_type overrides is_published: %s -> %s", requested_is_published, effective_is_published)

            await self.db["series"].update_one(
                {"_id": ObjectId(series_id)},
                {
                    "$set": {
                        "is_published": effective_is_published,
                        "is_link": is_link,
                        "publish_type": publish_type,
                        "updated_by": user_id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            series_updated = await self.db["series"].find_one({"_id": ObjectId(series_id)})

            return series_updated
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error publishing series: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error publishing series",
            )

    async def get_published_series_service(self, skip: int = 0, limit: int = 10, category_id: str = None, search_name: str = None) -> tuple[list, int]:
        """
        Get all published series with pagination including games and game_provisional data.
        Uses MongoDB aggregation for efficiency.
        Supports filtering by category and searching by series name.
        No authentication required.

        Args:
            skip: Number of documents to skip
            limit: Number of documents to return
            category_id: (optional) Filter series by category ID
            search_name: (optional) Search series by name (case-insensitive)

        Returns:
            tuple: (list of published series with games, total count)
        """
        try:
            # Construir el match stage con filtros opcionales
            match_stage = {
                "is_published": True,
                "is_active": True,
                "$or": [
                    {"is_link": False},
                    {"is_link": {"$exists": False}},
                    {"is_link": None}
                ]
            }

            if category_id:
                match_stage["category_id"] = category_id

            if search_name:
                # Búsqueda case-insensitive por nombre
                match_stage["title"] = {"$regex": search_name, "$options": "i"}

            # Pipeline de agregación
            pipeline = [
                {
                    "$match": match_stage
                },
                {
                    "$sort": {"created_at": -1}
                },
                {
                    "$lookup": {
                        "from": "game",
                        "let": {"games_ids": {
                            "$map": {
                                "input": "$games_id",
                                "as": "id",
                                "in": {"$toObjectId": "$$id"}
                            }
                        }},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$in": ["$_id", "$$games_ids"]},
                                        ]
                                    }
                                }
                            },
                            {"$sort": {"order": 1}},
                            {
                                "$project": {
                                    "_id": {"$toString": "$_id"},
                                    "title": 1,
                                    "history": 1,
                                    "image": 1,
                                    "category_id": 1,
                                    "order": 1,
                                    "provisional_id": {"$toString": "$provisional_id"},
                                    "views": {"$ifNull": ["$views", 0]}
                                }
                            }
                        ],
                        "as": "games"
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "title": 1,
                        "description": 1,
                        "image": 1,
                        "category_id": 1,
                        "main_character": 1,
                        "played_count": {"$ifNull": ["$played_count", 0]},
                        "views": {
                            "total": {
                                "$sum": "$games.views"
                            },
                            "most_viewed_game": {
                                "$max": "$games.views"
                            }
                        },
                        "rating": {"$ifNull": ["$rating", 0.0]},
                        "publish_type": {"$ifNull": ["$publish_type", "private"]},
                        "is_published": {"$ifNull": ["$is_published", False]},
                        "is_link": {"$ifNull": ["$is_link", False]},
                        "games": 1
                    }
                },
                {
                    "$facet": {
                        "metadata": [{"$count": "total"}],
                        "data": [
                            {"$skip": skip},
                            {"$limit": limit}
                        ]
                    }
                }
            ]

            result = await self.db["series"].aggregate(pipeline).to_list(None)

            if not result or not result[0].get("data"):
                return [], 0

            total = result[0]["metadata"][0]["total"] if result[0]["metadata"] else 0
            series_list = result[0]["data"]

            # Convertir _id a string para cada serie
            for series in series_list:
                if "_id" in series and hasattr(series["_id"], "__str__"):
                    series["_id"] = str(series["_id"])

            return series_list, total

        except Exception as e:
            self.logger.error(f"Error getting published series: {str(e)}")
            return [], 0

    async def get_published_series_detail_service(self, series_id: str) -> dict | None:
        """
        Get a published series with all its associated games and their game_provisional data.
        No authentication required. Only returns published series.

        Args:
            series_id: ID of the series

        Returns:
            dict: Published series document with games field or None if not found or not published
        """
        try:
            if not ObjectId.is_valid(series_id):
                return None

            series_db = await self.db["series"].find_one({
                "_id": ObjectId(series_id),
                "is_published": True,
                "is_active": True
            })

            if not series_db:
                return None

            # Obtener los juegos de la serie excluyendo los ocultos
            games_ids = series_db.get("games_id", [])
            hidden_games = set(series_db.get("hidden_games", []))
            games = []

            if games_ids:
                db_games = await self.db["game"].find({
                    "_id": {"$in": [ObjectId(gid) if ObjectId.is_valid(gid) else gid for gid in games_ids]},
                    "is_active": True
                }).sort([("order", 1)]).to_list(None)

                # Para cada juego, obtener su game_provisional
                for game in db_games:
                    game_id = str(game.get("_id", ""))

                    # Saltar juegos marcados como ocultos en la relación serie-juego
                    if game_id in hidden_games:
                        continue

                    provisional_id = game.get("provisional_id")

                    # Obtener el game_provisional
                    game_provisional = None
                    if provisional_id:
                        game_provisional = await self.db["game_provisional"].find_one({
                            "_id": ObjectId(provisional_id) if ObjectId.is_valid(provisional_id) else provisional_id
                        })

                    # Solo agregar el juego si tiene game_provisional válido
                    if game_provisional:
                        game_data = {
                            "_id": game_id,
                            "title": game.get("title"),
                            "history": game.get("history"),
                            "image": game.get("image"),
                            "category_id": game.get("category_id"),
                            "order": game.get("order", 1),
                            "provisional_id": str(provisional_id) if provisional_id else None,
                            "game_provisional": {
                                "_id": str(game_provisional.get("_id", "")),
                                "title": game_provisional.get("title"),
                                "script": game_provisional.get("script"),
                                "category": game_provisional.get("category"),
                                "image": game_provisional.get("image"),
                                "state": game_provisional.get("state"),
                                "progress": game_provisional.get("progress"),
                                "type_template": game_provisional.get("type_template")
                            }
                        }
                        games.append(game_data)

            # Convertir series_db a diccionario si es necesario
            if hasattr(series_db, 'dict'):
                series_response = series_db.dict()
            else:
                series_response = dict(series_db)

            # Agregar información de juegos a la serie
            series_response["_id"] = str(series_response.get("_id", ""))
            series_response["games"] = games

            user_db = await self.db["user"].find_one({"_id": ObjectId(series_response.get("created_by"))})
            if user_db:
                series_response["created_by"] = user_db.get("username")

            return series_response
        except Exception as e:
            self.logger.error(f"Error getting published series detail: {str(e)}")
            return None

    async def get_user_series_with_games_service(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 10,
        search_series_name: str = None,
        game_category: str = None,
        template_type: str = None
    ) -> dict | None:
        """
        Get all series created by a user with all their games and game_provisional data.
        Supports pagination and filtering by series name, game category, and template type.

        Args:
            user_id: ID of the user
            page: Page number (1-based)
            limit: Number of series per page
            search_series_name: Optional filter by series name (case-insensitive)
            game_category: Optional filter by game category
            template_type: Optional filter by game_provisional template type

        Returns:
            dict: User series data with games and game_provisional information for each game
        """
        try:
            # Construir query base
            query = {
                "created_by": user_id,
                "is_active": True
            }

            # Agregar filtro de nombre de serie si existe
            if search_series_name:
                query["title"] = {"$regex": search_series_name, "$options": "i"}

            # Obtener todas las series que coinciden (sin paginación inicialmente)
            # Ordenadas por fecha de creación descendente (más recientes primero)
            all_series = await self.db["series"].find(query).sort("created_at", -1).to_list(None)

            if not all_series:
                return {
                    "user_id": user_id,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": 0,
                        "total_pages": 0
                    },
                    "series": []
                }

            # Procesar cada serie y filtrar solo las que tengan juegos
            result_series = []

            for series in all_series:
                series_data = {
                    "_id": str(series.get("_id", "")),
                    "title": series.get("title"),
                    "description": series.get("description"),
                    "image": series.get("image"),
                    "category_id": series.get("category_id"),
                    "main_character": series.get("main_character"),
                    "games": []
                }

                # Obtener los juegos de la serie
                games_ids = series.get("games_id", [])

                if games_ids:
                    games_query = {
                        "_id": {"$in": [ObjectId(gid) if ObjectId.is_valid(gid) else gid for gid in games_ids]},
                        "is_active": True
                    }

                    # Agregar filtro de categoría de juego si existe
                    if game_category:
                        games_query["category_id"] = game_category

                    games = await self.db["game"].find(games_query).sort([("order", 1)]).to_list(None)

                    # Para cada juego, obtener su game_provisional
                    for game in games:
                        game_id = str(game.get("_id", ""))
                        provisional_id = game.get("provisional_id")

                        # Obtener el game_provisional
                        game_provisional = None
                        if provisional_id:
                            game_provisional = await self.db["game_provisional"].find_one({
                                "_id": ObjectId(provisional_id) if ObjectId.is_valid(provisional_id) else provisional_id
                            })

                        # Si hay filtro de template_type, verificar si coincide
                        if template_type:
                            # Si no existe game_provisional o no coincide el template, saltar este juego
                            if not game_provisional or game_provisional.get("type_template", "").lower() != template_type.lower():
                                continue

                        # Solo agregar el juego si tiene game_provisional válido
                        if game_provisional:
                            game_data = {
                                "_id": str(game.get("_id", "")),
                                "title": game.get("title"),
                                "history": game.get("history"),
                                "image": game.get("image"),
                                "category_id": game.get("category_id"),
                                "order": game.get("order", 1),
                                "provisional_id": str(provisional_id) if provisional_id else None,
                                "game_provisional": {
                                    "_id": str(game_provisional.get("_id", "")),
                                    "title": game_provisional.get("title"),
                                    "script": game_provisional.get("script"),
                                    "category": game_provisional.get("category"),
                                    "image": game_provisional.get("image"),
                                    "state": game_provisional.get("state"),
                                    "progress": game_provisional.get("progress"),
                                    "type_template": game_provisional.get("type_template")
                                }
                            }

                            series_data["games"].append(game_data)

                # Solo agregar la serie si tiene juegos después de aplicar filtros
                if series_data["games"]:
                    result_series.append(series_data)

            # Aplicar paginación al resultado final
            total_series = len(result_series)
            skip = (page - 1) * limit
            paginated_series = result_series[skip:skip + limit]

            # Calcular total de páginas
            total_pages = (total_series + limit - 1) // limit

            return {
                "user_id": user_id,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_series,
                    "total_pages": total_pages
                },
                "series": paginated_series
            }

        except Exception as e:
            self.logger.error(f"Error getting user series with games: {str(e)}")
            return {
                "user_id": user_id,
                "pagination": {
                    "page": 1,
                    "limit": limit,
                    "total": 0,
                    "total_pages": 0
                },
                "series": []
            }

    async def reorder_games_service(self, series_id: str, games_order: list[str], user_id: str) -> dict:
        try:
            if not ObjectId.is_valid(series_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid series ID")

            series_db = await self.db["series"].find_one({"_id": ObjectId(series_id)})
            if not series_db:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")

            current_games = series_db.get("games_id", [])
            if len(current_games) != len(games_order):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="games_order length mismatch")

            if set(current_games) != set(games_order):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="games_order must include all series games")

            order_map = {gid: idx + 1 for idx, gid in enumerate(games_order)}

            # Actualizar orden de cada juego
            for gid, order_value in order_map.items():
                if ObjectId.is_valid(gid):
                    await self.db["game"].update_one({"_id": ObjectId(gid)}, {"$set": {"order": order_value, "updated_at": datetime.utcnow(), "updated_by": user_id}})
                else:
                    await self.db["game"].update_one({"_id": gid}, {"$set": {"order": order_value, "updated_at": datetime.utcnow(), "updated_by": user_id}})

            # Persistir el orden normalizado en la serie
            await self.db["series"].update_one(
                {"_id": ObjectId(series_id)},
                {"$set": {"games_id": games_order, "updated_at": datetime.utcnow(), "updated_by": user_id}}
            )

            return await self.get_series_with_games_service(series_id)
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error reordering games: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error reordering games")

    async def update_game_visibility_service(self, series_id: str, game_id: str, is_hidden: bool, user_id: str) -> dict:
        try:
            if not ObjectId.is_valid(series_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid series ID")

            series_db = await self.db["series"].find_one({"_id": ObjectId(series_id)})
            if not series_db:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")

            if game_id not in series_db.get("games_id", []):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not in series")

            hidden_games = set(series_db.get("hidden_games", []))
            if is_hidden:
                hidden_games.add(game_id)
            else:
                hidden_games.discard(game_id)

            await self.db["series"].update_one(
                {"_id": ObjectId(series_id)},
                {"$set": {"hidden_games": list(hidden_games), "updated_at": datetime.utcnow(), "updated_by": user_id}}
            )

            return await self.get_series_with_games_service(series_id)
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error updating game visibility: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error updating game visibility")

    async def remove_game_from_series_service(self, series_id: str, game_id: str, user_id: str) -> dict:
        try:
            if not ObjectId.is_valid(series_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid series ID")

            series_db = await self.db["series"].find_one({"_id": ObjectId(series_id)})
            if not series_db:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")

            games = series_db.get("games_id", [])
            if game_id not in games:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not in series")

            # Eliminar relaciones dependientes del juego
            await self._delete_game_with_relations(game_id)

            # Recompactar orden y lista de juegos de la serie
            remaining_games = [gid for gid in games if gid != game_id]
            await self.db["series"].update_one(
                {"_id": ObjectId(series_id)},
                {"$set": {"games_id": remaining_games, "hidden_games": [g for g in series_db.get("hidden_games", []) if g != game_id], "updated_at": datetime.utcnow(), "updated_by": user_id}}
            )

            # Reordenar los juegos restantes
            for idx, gid in enumerate(remaining_games):
                if ObjectId.is_valid(gid):
                    await self.db["game"].update_one({"_id": ObjectId(gid)}, {"$set": {"order": idx + 1, "updated_at": datetime.utcnow(), "updated_by": user_id}})
                else:
                    await self.db["game"].update_one({"_id": gid}, {"$set": {"order": idx + 1, "updated_at": datetime.utcnow(), "updated_by": user_id}})

            return await self.get_series_with_games_service(series_id)
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error removing game from series: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error removing game from series")

    async def delete_series_hard_service(self, series_id: str, user_id: str) -> dict:
        try:
            if not ObjectId.is_valid(series_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid series ID")

            series_db = await self.db["series"].find_one({"_id": ObjectId(series_id)})
            if not series_db:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")

            games = series_db.get("games_id", [])
            deletion_summary = {
                "series_deleted": 0,
                "games": 0,
                "game_provisional": 0,
                "state_glic": 0,
                "character": 0,
                "location": 0,
                "state_game": 0,
                "event": 0,
                "assets": 0,
            }

            # Borrar assets de la serie (normal + variantes minificadas si existen)
            for key in ("image", "image_min", "image_minified", "image_thumbnail", "image_small"):
                if delete_asset_from_url(series_db.get(key)):
                    deletion_summary["assets"] += 1

            for gid in games:
                cascade_counts = await self._delete_game_with_relations(gid)
                deletion_summary["games"] += cascade_counts.get("game", 0)
                deletion_summary["game_provisional"] += cascade_counts.get("game_provisional", 0)
                deletion_summary["state_glic"] += cascade_counts.get("state_glic", 0)
                deletion_summary["character"] += cascade_counts.get("character", 0)
                deletion_summary["location"] += cascade_counts.get("location", 0)
                deletion_summary["state_game"] += cascade_counts.get("state_game", 0)
                deletion_summary["event"] += cascade_counts.get("event", 0)
                deletion_summary["assets"] += cascade_counts.get("assets", 0)

            series_delete_result = await self.db["series"].delete_one({"_id": ObjectId(series_id)})
            deletion_summary["series_deleted"] = series_delete_result.deleted_count

            return deletion_summary
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error deleting series: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error deleting series")

    async def _delete_game_with_relations(self, game_id: str) -> dict:
        try:
            query_id = ObjectId(game_id) if ObjectId.is_valid(game_id) else game_id
            game_db = await self.db["game"].find_one({"_id": query_id})
            provisional_id = game_db.get("provisional_id") if game_db else None

            assets_deleted = 0
            if game_db and delete_asset_from_url(game_db.get("image")):
                assets_deleted += 1

            # Preparar documentos relacionados para limpiar assets antes de borrar
            state_glic_docs = await self.db["state_glic"].find({"$or": [{"game_id": game_id}, {"data.game_id": game_id}]}).to_list(None)
            event_docs = await self.db["event"].find({"game_id": game_id}).to_list(None)

            for doc in state_glic_docs:
                assets_deleted += self._delete_assets_from_document(doc)

            for doc in event_docs:
                # Campos explícitos de eventos
                for key in ("image", "image_description", "text_image"):
                    if delete_asset_from_url(doc.get(key)):
                        assets_deleted += 1
                assets_deleted += self._delete_assets_from_document(doc.get("data", {}))

            state_glic_result = await self.db["state_glic"].delete_many({"$or": [{"game_id": game_id}, {"data.game_id": game_id}]})
            character_result = await self.db["character"].delete_many({"game_id": game_id})
            location_result = await self.db["location"].delete_many({"game_id": game_id})
            state_game_result = await self.db["state_game"].delete_many({"game_id": game_id})
            event_result = await self.db["event"].delete_many({"game_id": game_id})

            deleted_provisional = 0
            if provisional_id:
                provisional_query = ObjectId(provisional_id) if ObjectId.is_valid(provisional_id) else provisional_id
                provisional_doc = await self.db["game_provisional"].find_one({"_id": provisional_query})
                if provisional_doc and delete_asset_from_url(provisional_doc.get("image")):
                    assets_deleted += 1
                provisional_result = await self.db["game_provisional"].delete_one({"_id": provisional_query})
                deleted_provisional = provisional_result.deleted_count

            game_delete_result = await self.db["game"].delete_one({"_id": query_id})

            return {
                "state_glic": state_glic_result.deleted_count,
                "character": character_result.deleted_count,
                "location": location_result.deleted_count,
                "state_game": state_game_result.deleted_count,
                "event": event_result.deleted_count,
                "game_provisional": deleted_provisional,
                "game": game_delete_result.deleted_count,
                "assets": assets_deleted,
            }
        except Exception as e:
            self.logger.error(f"Error deleting game and relations: {str(e)}")
            raise

    def _delete_assets_from_document(self, doc: dict | list | None) -> int:
        """Recorre un documento o lista y borra URLs de assets (GCS/Spaces)."""
        deleted = 0
        if not doc:
            return deleted

        def _walk(value):
            nonlocal deleted
            if isinstance(value, dict):
                for v in value.values():
                    _walk(v)
            elif isinstance(value, list):
                for item in value:
                    _walk(item)
            elif isinstance(value, str):
                if delete_asset_from_url(value):
                    deleted += 1

        _walk(doc)
        return deleted
