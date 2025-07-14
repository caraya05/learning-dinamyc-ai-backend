from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
import httpx
from urllib.parse import unquote
import logging

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

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
