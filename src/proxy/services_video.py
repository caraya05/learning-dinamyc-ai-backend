import httpx
import logging
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from urllib.parse import unquote

logger = logging.getLogger(__name__)


async def proxy_video_stream(
        video_url: str,
        start_byte: int = None,
        end_byte: int = None
) -> StreamingResponse:
    """
    Proxy de streaming de video desde Google Cloud Storage.

    Args:
        video_url: URL del video en Google Cloud Storage
        start_byte: Byte inicial para range requests (para seeking)
        end_byte: Byte final para range requests

    Returns:
        StreamingResponse con el contenido del video

    Soporta:
        - Range requests para seeking en el video
        - Streaming de progreso
        - Diferentes tipos de contenido de video
    """
    if not video_url:
        raise HTTPException(status_code=400, detail="Video URL is required")

    # Verificar que el enlace comience con la URL base de Google Cloud Storage de Qwestar
    if not video_url.startswith("https://storage.googleapis.com/qwestar"):
        raise HTTPException(status_code=400, detail="Invalid Google Cloud Storage link")

    try:
        # Decodificar la URL si es necesario
        decoded_url = unquote(video_url)

        # Crear cliente HTTP asíncrono
        async with httpx.AsyncClient() as client:
            # Hacer una solicitud HEAD primero para obtener el tamaño del archivo
            head_response = await client.head(
                decoded_url,
                headers={
                    'User-Agent': 'UnityPlayer/5.3.5f1',
                    'Accept': '*/*'
                },
                follow_redirects=True
            )

            if head_response.status_code != 200:
                raise HTTPException(
                    status_code=head_response.status_code,
                    detail=f"Error fetching video metadata: {head_response.status_code}"
                )

            # Obtener el tamaño total del archivo
            content_length = int(head_response.headers.get('content-length', 0))
            supports_range = head_response.headers.get('accept-ranges', '').lower() == 'bytes'

            # Preparar headers para la solicitud GET
            get_headers = {
                'User-Agent': 'UnityPlayer/5.3.5f1',
                'Accept': '*/*'
            }

            # Agregar header de Range si se solicita
            if supports_range and (start_byte is not None or end_byte is not None):
                if start_byte is None:
                    start_byte = 0
                if end_byte is None:
                    end_byte = content_length - 1

                get_headers['Range'] = f'bytes={start_byte}-{end_byte}'
                response_status = 206  # Partial Content
            else:
                response_status = 200

            # Proxy la solicitud GET al enlace de Google Cloud Storage
            response = await client.get(
                decoded_url,
                headers=get_headers,
                follow_redirects=True
            )

            if response.status_code not in [200, 206]:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Error fetching video: {response.status_code}"
                )

            # Preparar los headers para la respuesta
            response_headers = {
                key: value for key, value in response.headers.items()
                if key.lower() in ('content-type', 'content-length', 'content-disposition',
                                  'accept-ranges', 'content-range')
            }

            # Asegurar que el content-type sea correcto para video
            if 'content-type' not in response_headers:
                response_headers['content-type'] = 'video/mp4'

            # Agregar headers para permitir seeking
            if supports_range:
                response_headers['accept-ranges'] = 'bytes'
                if 'content-length' not in response_headers and content_length:
                    response_headers['content-length'] = str(content_length)

            logger.info(f"Proxying video: {decoded_url[:100]}... (size: {content_length} bytes)")

            # Devolver la respuesta en streaming
            return StreamingResponse(
                content=response.aiter_bytes(chunk_size=1024 * 1024),  # 1MB chunks
                status_code=response_status,
                headers=response_headers
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error proxying video stream: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def get_video_metadata(video_url: str) -> dict:
    """
    Obtiene metadatos del video (tamaño, tipo de contenido, etc).

    Args:
        video_url: URL del video en Google Cloud Storage

    Returns:
        Diccionario con metadatos del video
    """
    if not video_url:
        raise HTTPException(status_code=400, detail="Video URL is required")

    if not video_url.startswith("https://storage.googleapis.com/qwestar"):
        raise HTTPException(status_code=400, detail="Invalid Google Cloud Storage link")

    try:
        decoded_url = unquote(video_url)

        async with httpx.AsyncClient() as client:
            response = await client.head(
                decoded_url,
                headers={
                    'User-Agent': 'UnityPlayer/5.3.5f1',
                    'Accept': '*/*'
                },
                follow_redirects=True
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Error fetching video metadata"
                )

            return {
                "content_type": response.headers.get('content-type', 'video/mp4'),
                "content_length": int(response.headers.get('content-length', 0)),
                "supports_range": response.headers.get('accept-ranges', '').lower() == 'bytes',
                "last_modified": response.headers.get('last-modified'),
                "etag": response.headers.get('etag'),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video metadata: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

