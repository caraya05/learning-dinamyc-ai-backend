from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi.responses import StreamingResponse
import httpx
from urllib.parse import unquote
import logging

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from proxy.services_video import proxy_video_stream, get_video_metadata

router = APIRouter(tags=["proxy"])

@router.get("/proxy-google-cloud",)
async def proxy_google_cloud(google_cloud_link: str = None,
                             user_db: dict = Depends(auth),
                             Token: HTTPAuthorizationCredentials = Depends(auth_schema),
                             ):
    if not google_cloud_link:
        raise HTTPException(status_code=400, detail="Google Cloud Storage link is required")

    # Verificar que el enlace comience con la URL base de Google Cloud Storage de Qwestar
    if not google_cloud_link.startswith("https://storage.googleapis.com/qwestar"):
        raise HTTPException(status_code=400, detail="Invalid Google Cloud Storage link")

    try:
        # Decodificar la URL si es necesario
        decoded_link = unquote(google_cloud_link)

        # Crear cliente HTTP asíncrono
        async with httpx.AsyncClient() as client:
            # Proxy la solicitud al enlace de Google Cloud Storage
            response = await client.get(
                decoded_link,
                headers={
                    'User-Agent': 'UnityPlayer/5.3.5f1',
                    'Accept': '*/*'
                },
                follow_redirects=True
            )

            # Preparar los headers para la respuesta
            headers = {key: value for key, value in response.headers.items()
                      if key.lower() in ('content-type', 'content-length', 'content-disposition')}

            # Devolver la respuesta en streaming
            return StreamingResponse(
                content=response.aiter_bytes(),
                status_code=response.status_code,
                headers=headers
            )
    except Exception as e:
        logging.error(f"Error proxying Google Cloud Storage link: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/proxy-video-stream")
async def proxy_video_stream_endpoint(
        video_url: str = Query(..., description="URL of the video in Google Cloud Storage"),
        start_byte: int = Query(None, description="Start byte for range requests"),
        end_byte: int = Query(None, description="End byte for range requests"),
        # user_db: dict = Depends(auth),
        # Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Proxy endpoint for video streaming with support for HTTP range requests.

    This endpoint allows:
    - Direct streaming of MP4 videos from Google Cloud Storage
    - Seeking support via HTTP 206 Partial Content responses
    - Chunked transmission for efficient bandwidth usage
    - Compatible with HTML5 video players and mobile clients

    Query Parameters:
    - video_url: URL of the video in Google Cloud Storage (required)
    - start_byte: Starting byte position for range requests (optional)
    - end_byte: Ending byte position for range requests (optional)

    Returns:
        StreamingResponse with video content and appropriate headers
    """
    return await proxy_video_stream(
        video_url=video_url,
        start_byte=start_byte,
        end_byte=end_byte
    )


@router.get("/video-metadata")
async def get_video_metadata_endpoint(
        video_url: str = Query(..., description="URL of the video in Google Cloud Storage"),
        # user_db: dict = Depends(auth),
        # Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Get metadata of a video without downloading it.

    This endpoint returns information about a video such as:
    - Content type
    - File size
    - Range request support
    - Last modified date
    - ETag

    Query Parameters:
    - video_url: URL of the video in Google Cloud Storage (required)

    Returns:
        JSON object with video metadata
    """
    return await get_video_metadata(video_url=video_url)

