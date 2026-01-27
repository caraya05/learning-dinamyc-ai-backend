import logging

from bson import ObjectId
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from series.schemas import SchemaCreateSeries, SchemaListSeries, SchemaUpdateSeries, SchemaPublishSeries, SchemaPublishedSeriesDetail, SchemaListPublishedSeries
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


@router.get("/{series_id}", status_code=status.HTTP_200_OK)
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


@router.put("/{series_id}", status_code=status.HTTP_200_OK)
async def update_series(
    series_id: str,
    series_data: SchemaUpdateSeries,
    user: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
    service: SeriesService = Depends(get_series_service)
):
    """
    Update a series.
    Requires authentication.
    """
    if not ObjectId.is_valid(series_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid series ID",
        )

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
    Publish or unpublish a series.
    Only the owner of the series can publish it.
    Requires authentication.
    """
    if not ObjectId.is_valid(series_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid series ID",
        )

    try:
        series_db = await service.publish_series_service(
            series_id,
            publish_data.is_published,
            str(user.get("_id"))
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
        series_list, total = await service.get_published_series_service(skip=skip, limit=limit, category_id=category_id, search_name=search_name)


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
