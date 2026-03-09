import logging

from bson import ObjectId
from fastapi import APIRouter, Form
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from fastapi import status
from fastapi import UploadFile, File
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from utils import upload_file

from series.schemas import (
    SchemaCreateSeries,
    SchemaListSeries,
    SchemaUpdateSeries,
    SchemaPublishSeries,
    SchemaPublishedSeriesDetail,
    SchemaListPublishedSeries,
    SchemaReorderGames,
    SchemaRemoveGame,
    SchemaUpdateGameVisibility,
    SchemaUserStats,
)
from series.services import SeriesService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/series", tags=["Series"])


def get_series_service():
    return SeriesService()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_series(
        series_data: SchemaCreateSeries,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: SeriesService = Depends(get_series_service)
):
    """
    Create a new series.
    Requires authentication.
    """
    try:
        series_db = await service.create_series_service(series_data, str(user.get("_id")))
        series_db["_id"] = str(series_db["_id"])
        return series_db
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error creating series",
        )


@router.get("/{series_id}/", status_code=status.HTTP_200_OK)
async def get_series(
        series_id: str,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: SeriesService = Depends(get_series_service)
):
    """
    Get a series by ID with all its games and game_provisional data.
    Only returns games that have valid game_provisional.
    Requires authentication.
    """
    if not ObjectId.is_valid(series_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid series ID",
        )

    try:
        series_with_games = await service.get_series_with_games_service(series_id)
        if not series_with_games:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Series not found",
            )

        # Convertir ObjectId a string si es necesario
        if isinstance(series_with_games.get("_id"), str):
            series_with_games["_id"] = str(series_with_games["_id"])

        return series_with_games
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting series",
        )


@router.put("/{series_id}/", status_code=status.HTTP_200_OK)
async def update_series(
        series_id: str,
        title: str | None = Form(None),
        description: str | None = Form(None),
        category_id: str | None = Form(None),
        main_character: str | None = Form(None),
        image: UploadFile | None = File(None),
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: SeriesService = Depends(get_series_service)
):
    """
    Update a series. Allows changing metadata and image URL.
    Requires authentication.
    """
    if not ObjectId.is_valid(series_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid series ID",
        )


    series_data = SchemaUpdateSeries(
        title=title,
        description=description,
        category_id=category_id,
        main_character=main_character,
        image=None
    )

    # Si se adjunta archivo en el campo image, súbelo al bucket y reemplaza el campo
    if image is not None:
        uploaded_url = upload_file(image)

        series_data.image = uploaded_url

    try:
        series_db = await service.update_series_service(series_id, series_data, str(user.get("_id")))
        series_db["_id"] = str(series_db["_id"])
        return series_db
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error updating series",
        )


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListSeries)
async def list_series(
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        count: int = 10,
        service: SeriesService = Depends(get_series_service)
):
    """
    Get all series with pagination.
    Requires authentication.
    """
    try:
        skip = (page - 1) * count
        series_list, total = await service.get_all_series_service(skip=skip, limit=count, active_only=True)

        for series in series_list:
            series["_id"] = str(series["_id"])

        total_pages = (total + count - 1) // count

        return {
            "count": total,
            "results": series_list,
            "page": page,
            "total_pages": total_pages
        }
    except Exception as e:
        logger.error(f"Error listing series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error listing series",
        )


@router.get("/user/stats", status_code=status.HTTP_200_OK, response_model=SchemaUserStats)
async def get_user_stats(
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: SeriesService = Depends(get_series_service)
):
    """
    Get aggregated statistics for the authenticated user.

    Returns statistics including:
    - total_series: Total number of series created by the user
    - total_episodes: Total number of episodes/games in all user series
    - published_series: Total number of published series by the user
    - analytics_records: Total number of analytics records for user's games

    Requires authentication.

    Response:
    {
        "total_series": 5,
        "total_episodes": 24,
        "published_series": 3,
        "analytics_records": 156
    }
    """
    try:
        user_id = str(user.get("_id"))
        stats = await service.get_user_stats_service(user_id)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user statistics",
        )


@router.get("/user/my-series", status_code=status.HTTP_200_OK, response_model=SchemaListSeries)
async def get_user_series(
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        count: int = 10,
        service: SeriesService = Depends(get_series_service)
):
    """
    Get all series created by the authenticated user with pagination.
    Requires authentication.
    """
    try:
        skip = (page - 1) * count
        user_id = str(user.get("_id"))
        series_list, total = await service.get_series_by_user_service(user_id, skip=skip, limit=count)

        for series in series_list:
            series["_id"] = str(series["_id"])

        total_pages = (total + count - 1) // count

        return {
            "count": total,
            "results": series_list,
            "page": page,
            "total_pages": total_pages
        }
    except Exception as e:
        logger.error(f"Error getting user series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting user series",
        )


@router.get("/{series_id}/games", status_code=status.HTTP_200_OK)
async def get_series_games(
        series_id: str,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: SeriesService = Depends(get_series_service)
):
    """
    Get a series with all its associated games.
    Returns the series information along with complete game data.
    Requires authentication.
    """
    if not ObjectId.is_valid(series_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid series ID",
        )

    try:
        series_with_games = await service.get_series_with_games_service(series_id)

        if not series_with_games:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Series not found",
            )

        series_with_games["_id"] = str(series_with_games["_id"])

        # Convertir IDs de juegos a strings
        if "games_data" in series_with_games:
            for game in series_with_games["games_data"]:
                game["_id"] = str(game.get("_id", ""))

        return series_with_games
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting series games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting series games",
        )


@router.post("/{series_id}/reorder-games/", status_code=status.HTTP_200_OK)
async def reorder_series_games(
        series_id: str,
        payload: SchemaReorderGames,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: SeriesService = Depends(get_series_service)
):
    """Reordenar todos los juegos de una serie."""
    try:
        updated_series = await service.reorder_games_service(series_id, payload.games_order, str(user.get("_id")))
        if updated_series:
            updated_series["_id"] = str(updated_series.get("_id", ""))
        return updated_series
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering series games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error reordering series games",
        )


@router.put("/{series_id}/games/{game_id}/visibility", status_code=status.HTTP_200_OK)
async def update_series_game_visibility(
        series_id: str,
        game_id: str,
        payload: SchemaUpdateGameVisibility,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: SeriesService = Depends(get_series_service)
):
    """Ocultar o mostrar un juego dentro de la serie."""
    try:
        updated_series = await service.update_game_visibility_service(series_id, game_id, payload.is_hidden,
                                                                      str(user.get("_id")))
        if updated_series:
            updated_series["_id"] = str(updated_series.get("_id", ""))
        return updated_series
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating game visibility: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error updating game visibility",
        )


@router.delete("/{series_id}/remove-game/", status_code=status.HTTP_200_OK)
async def remove_game_from_series(
        series_id: str,
        payload: SchemaRemoveGame,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: SeriesService = Depends(get_series_service)
):
    """Eliminar un juego de la serie (hard delete del juego y dependencias)."""
    try:
        updated_series = await service.remove_game_from_series_service(series_id, payload.game_id, str(user.get("_id")))
        if updated_series:
            updated_series["_id"] = str(updated_series.get("_id", ""))
        return updated_series
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing game from series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error removing game from series",
        )


@router.delete("/{series_id}/", status_code=status.HTTP_200_OK)
async def delete_series_hard(
        series_id: str,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: SeriesService = Depends(get_series_service)
):
    """Eliminar en cascada la serie y todos los recursos asociados en un solo llamado."""
    try:
        deletion_summary = await service.delete_series_hard_service(series_id, str(user.get("_id")))
        return {"series_id": series_id, "deleted": deletion_summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error deleting series",
        )


@router.get("/user/series-with-games", status_code=status.HTTP_200_OK)
async def get_user_series_with_games(
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        limit: int = 10,
        search_series_name: str = None,
        game_category: str = None,
        template_type: str = None,
        service: SeriesService = Depends(get_series_service)
):
    """
    Get all series of the authenticated user with all associated games and their game_provisional data.
    Supports pagination and filtering by series name, game category, and template type.

    Query Parameters:
    - page (int, default=1): Page number for pagination
    - limit (int, default=10): Number of series per page
    - search_series_name (str, optional): Search for series by name (case-insensitive)
    - game_category (str, optional): Filter games by category
    - template_type (str, optional): Filter games by template type (story, trivia, form, survey, solve)

    Requires authentication.
    """
    try:
        # Validar parámetros de paginación
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10

        user_id = str(user.get("_id"))
        user_series_data = await service.get_user_series_with_games_service(
            user_id=user_id,
            page=page,
            limit=limit,
            search_series_name=search_series_name,
            game_category=game_category,
            template_type=template_type
        )

        if not user_series_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving user series",
            )

        return user_series_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user series with games: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting user series with games",
        )


@router.put("/{series_id}/publish", status_code=status.HTTP_200_OK)
async def publish_series(
        series_id: str,
        publish_data: SchemaPublishSeries,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: SeriesService = Depends(get_series_service)
):
    """
    Publish or unpublish a series. publish_type controls whether it is public, link-only or private.
    - public: is_published=True, is_link=False
    - link: is_published=True, is_link=True
    - private: is_published=False, is_link=False
    """
    if not ObjectId.is_valid(series_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid series ID",
        )

    expected_is_published = publish_data.publish_type != "private"
    if publish_data.is_published != expected_is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="is_published must match publish_type (private => false, others => true)",
        )

    try:
        series_db = await service.publish_series_service(
            series_id,
            publish_data.publish_type,
            str(user.get("_id")),
            requested_is_published=publish_data.is_published
        )
        series_db["_id"] = str(series_db["_id"])
        return series_db
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error publishing series",
        )


@router.get("/published/list", status_code=status.HTTP_200_OK, response_model=SchemaListPublishedSeries)
async def list_published_series(
        page: int = 1,
        limit: int = 10,
        category_id: str = None,
        search_name: str = None,
        service: SeriesService = Depends(get_series_service)
):
    """
    Get all published series with pagination.
    Supports filtering by category and searching by series name.
    No authentication required.

    Query Parameters:
    - page (int, default=1): Page number for pagination
    - limit (int, default=10): Number of series per page
    - category_id (str, optional): Filter series by category ID
    - search_name (str, optional): Search series by name (case-insensitive)
    """
    try:
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10

        skip = (page - 1) * limit
        series_list, total = await service.get_published_series_service(skip=skip, limit=limit, category_id=category_id,
                                                                        search_name=search_name)

        for series in series_list:
            series["_id"] = str(series["_id"])

        total_pages = (total + limit - 1) // limit

        return {
            "count": total,
            "results": series_list,
            "page": page,
            "total_pages": total_pages
        }
    except Exception as e:
        logger.error(f"Error listing published series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error listing published series",
        )


@router.get("/published/{series_id}", status_code=status.HTTP_200_OK)
async def get_published_series_detail(
        series_id: str,
        service: SeriesService = Depends(get_series_service)
):
    """
    Get a published series with all its associated games and their game_provisional data.
    No authentication required.
    """
    if not ObjectId.is_valid(series_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid series ID",
        )

    try:
        series_with_games = await service.get_published_series_detail_service(series_id)
        if not series_with_games:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Published series not found",
            )

        return series_with_games
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting published series detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting published series detail",
        )


@router.get("/debug/analytics/{game_id}", status_code=status.HTTP_200_OK)
async def debug_analytics(
        game_id: str = None,
        service: SeriesService = Depends(get_series_service)
):
    """
    Debug endpoint to check the structure of analytics collection.
    Shows sample documents and how analytics are stored.
    """
    try:
        analytics_info = await service.debug_analytics_structure(game_id)
        return analytics_info
    except Exception as e:
        logger.error(f"Error in debug analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error in debug analytics: {str(e)}",
        )


@router.get("/debug/mapping/{series_id}", status_code=status.HTTP_200_OK)
async def debug_series_analytics_mapping(
        series_id: str,
        service: SeriesService = Depends(get_series_service)
):
    """
    Debug endpoint to verify how analytics are matched with games in a series.
    Shows which games have analytics and which don't, and what values they have.
    """
    try:
        mapping_info = await service.debug_series_analytics_mapping(series_id)
        return mapping_info
    except Exception as e:
        logger.error(f"Error in debug series analytics mapping: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error in debug series analytics mapping: {str(e)}",
        )

