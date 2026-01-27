import logging
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from core.database import db
from series.models import Series
from series.schemas import SchemaCreateSeries, SchemaUpdateSeries


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
                games_id=[],
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

    async def publish_series_service(self, series_id: str, is_published: bool, user_id: str) -> dict:
        """
        Publish or unpublish a series.

        Args:
            series_id: ID of the series to publish/unpublish
            is_published: Boolean indicating publish status
            user_id: ID of the user publishing the series

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

            await self.db["series"].update_one(
                {"_id": ObjectId(series_id)},
                {
                    "$set": {
                        "is_published": is_published,
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
                "is_active": True
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

            # Obtener los juegos de la serie
            games_ids = series_db.get("games_id", [])
            games = []

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

