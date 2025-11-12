from auth.services import social_auth_firebase
from auth.services import is_token_valid
from auth.services import authenticate_by_game_code
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status
from fastapi import Request
from auth.schemas import Credentials
from auth.schemas import GameCode
from auth.schemas import Refresh
from auth.schemas import Token
from auth.schemas import GameAuthRequest
from auth.schemas import GameToken
from auth.services import auth_refresh
from auth.services import authenticate_user
from auth.services import generate_token
from auth.services import generate_game_token
from core import db
from core.schemas import ExceptionModel
from auth.services import generate_verification_code, validate_verification_code
from auth.schemas import VerificationRequest, VerificationCode
from fastapi import BackgroundTasks

from utils import send_email

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/verify", status_code=status.HTTP_200_OK)
def verify_token(
        token: dict = None,
):
    if token is None:
        token = {"access": ""}
    """
    Verify if token_user is valid
    """
    if is_token_valid(token["access"]):
        return {"message": "Token is valid"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/token", response_model=Token, responses={401: {"model": ExceptionModel}})
async def token(credentials: Credentials):
    if user := await authenticate_user(
            email=credentials.email,
            password=credentials.password,
    ):
        return await generate_token(
            user_id=user.get("_id"),
            password_ts=user.get("password"),
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/google", status_code=status.HTTP_200_OK)
async def sign_in_with_google(data: dict):
    """
    Sign in with google

    """
    return await social_auth_firebase(data)


@router.post("/apple", status_code=status.HTTP_200_OK)
async def sign_in_with_apple(data: dict):
    """
    Sign in with apple
    """
    return await social_auth_firebase(data)


@router.post("/refresh", response_model=Token, responses={401: {"model": ExceptionModel}})
async def refresh(payload: Refresh):
    try:
        if new_token := await auth_refresh(token=payload.refresh):
            return new_token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Error in refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/game-code", response_model=Token, responses={401: {"model": ExceptionModel}})
async def authenticate_with_game_code(game_code: GameCode):
    """
    Autentica un usuario mediante un código de juego y genera tokens de acceso.

    Args:
        game_code: El código de juego proporcionado por el usuario

    Returns:
        Los tokens de acceso y refresco si la autenticación es exitosa

    Raises:
        HTTPException: Si el código de juego es inválido o ha expirado
    """
    if user := await authenticate_by_game_code(code=game_code.code):
        return await generate_token(
            user_id=user.get("_id"),
            password_ts=user.get("password"),
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired game code",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/game-token/", response_model=GameToken, responses={401: {"model": ExceptionModel}})
async def authenticate_by_game_id(request: Request, game_auth: GameAuthRequest):
    """
    Autentica un usuario mediante el ID del juego e IP del cliente.
    Genera un token de corta duración que solo funciona para ese juego.

    Args:
        request: Objeto Request para obtener la IP del cliente
        game_auth: Datos con el game_id

    Returns:
        Token de acceso de corta duración para el juego

    Raises:
        HTTPException: Si el game_id es inválido
    """
    # Obtener la IP del cliente
    client_ip = request.client.host if request.client else "unknown"

    # Validar que el juego existe
    from bson import ObjectId
    try:
        game_id_obj = ObjectId(game_auth.game_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid game_id format",
        )

    game = await db["game"].find_one({"_id": game_id_obj})
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    # Generar el token de juego
    token_data = await generate_game_token(
        game_id=game_auth.game_id,
        client_ip=client_ip,
        expires_in_minutes=15  # Token válido por 15 minutos
    )

    return token_data


@router.post("/send-code", status_code=status.HTTP_200_OK)
async def send_verification_code(request: VerificationRequest, background_tasks: BackgroundTasks):
    """
    Envía un código de verificación al correo proporcionado si el usuario está en la base de datos.
    """
    user = await db["user"].find_one({"email": request.email, "is_preview": True})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generar y enviar el código
    code = await generate_verification_code(request.email)
    html = f"""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <meta name="x-apple-disable-message-reformatting"/>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
        <meta name="color-scheme" content="light dark"/>
        <title>Verification Code</title>
        <style>
            body {{
                background-color: #f3f4f6;
                color: #1f2937;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                font-size: 14px;
                line-height: 1.5;
            }}
    
            .container {{
                max-width: 640px;
                margin: 0 auto;
                padding: 24px;
                background-color: #ffffff;
            }}
    
            .header {{
                text-align: center;
                padding: 24px 0;
                background-color: #ec4899;
                border-radius: 8px;
                margin-bottom: 32px;
            }}
    
            .header h1 {{
                font-size: 28px;
                font-weight: 700;
                color: #ffffff;
                margin: 0;
            }}
    
            .title {{
                font-size: 20px;
                font-weight: 600;
                color: #1f2937;
                margin: 24px 0 16px 0;
            }}
    
            .text {{
                font-size: 14px;
                color: #374151;
                margin: 16px 0;
            }}
    
            .code-wrapper {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 24px;
                margin: 24px 0;
                background-color: #f9fafb;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
            }}
    
            .code {{
                font-size: 32px;
                font-weight: 700;
                color: #293c72;
                letter-spacing: 4px;
                margin: 0;
                font-family: 'Courier New', monospace;
                flex: 1;
            }}
    
            .copy-button {{
                background: none;
                border: none;
                cursor: pointer;
                font-size: 24px;
                padding: 8px;
                margin-left: 16px;
                transition: transform 0.2s;
            }}
    
            .copy-button:hover {{
                transform: scale(1.1);
            }}
    
            .footer-text {{
                font-size: 14px;
                color: #374151;
                margin: 24px 0;
            }}
    
            .signature {{
                font-size: 14px;
                color: #374151;
                margin: 30px 0 0 0;
            }}
    
            .footer {{
                background-color: #343a40;
                color: #ffffff;
                text-align: center;
                padding: 16px;
                border-radius: 0 0 8px 8px;
                font-size: 14px;
                margin: 32px -24px -24px -24px;
            }}
    
            .footer p {{
                margin: 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Qwestar</h1>
            </div>
            
            <h2 class="title">Verification Code</h2>
            
            <p class="text">
                Please use the following verification code to continue:
            </p>
            
            <div class="code-wrapper">
                <p class="code" id="verification-code">{code}</p>
                <button class="copy-button" onclick="copyToClipboard()" title="Copy code">
                    📋
                </button>
            </div>
            
            <p class="footer-text">
                If you have any questions, feel free to contact us.
            </p>
            
            <p class="signature">
                Best regards,<br>
                <strong>Qwestar Team</strong>
            </p>
            
            <div class="footer">
                <p>© 2025 Qwestar. All rights reserved.</p>
            </div>
        </div>
    
        <script>
            function copyToClipboard() {{
                const code = document.getElementById('verification-code').textContent;
                navigator.clipboard.writeText(code);
            }}
        </script>
    </body>
    </html>
        """
    await send_email(
        "Tu código de verificación para Qwestar",
        [str(request.email)],
        html)
    return {"message": "Verification code sent"}


@router.post("/validate-code", status_code=status.HTTP_200_OK)
async def validate_code(payload: VerificationCode):
    """
    Valida el código de verificación y genera tokens si es válido.
    """
    if not await validate_verification_code(payload.email, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    user = await db["user"].find_one({"email": payload.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return await generate_token(user_id=user.get("_id"), password_ts=user.get("password"))
