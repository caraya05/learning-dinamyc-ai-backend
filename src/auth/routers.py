from auth.services import social_auth_firebase
from auth.services import is_token_valid
from auth.services import authenticate_by_game_code
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status
from auth.schemas import Credentials
from auth.schemas import GameCode
from auth.schemas import Refresh
from auth.schemas import Token
from auth.services import auth_refresh
from auth.services import authenticate_user
from auth.services import generate_token
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


@router.post("/send-code", status_code=status.HTTP_200_OK)
async def send_verification_code(request: VerificationRequest, background_tasks: BackgroundTasks):
    """
    Envía un código de verificación al correo proporcionado si el usuario está en la base de datos.
    """
    user = await db["user"].find_one({"email": request.email})
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
<html xmlns="http://www.w3.org/1999/xhtml" xmlns="http://www.w3.org/1999/xhtml"
      style="color-scheme: light dark; supported-color-schemes: light dark;">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <meta name="x-apple-disable-message-reformatting"/>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    <meta name="color-scheme" content="light dark"/>
    <meta name="supported-color-schemes" content="light dark"/>
    <title></title>

    <style>
        body {{
            background-color: #f3f4f6;
            color: #1f2937;
            font-family: Arial, sans-serif;
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
        }}

        .header h1 {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #ffffff;
            background-color: #ec4899;
            padding: 8px;
            display: inline-block;
        }}

        .title {{
            font-size: 1.125rem;
            font-weight: 600;
            color: #4b5563;
        }}

        .text {{
            margin-top: 16px;
            font-size: 0.875rem;
            color: #374151;
        }}

        .text span {{
            font-family: monospace;
            color: #6b7280;
        }}
    </style>

</head>
<body>
  
<div class="container">
    <div class="header"
         style="position:relative; text-align:center; padding:12px 0; background-color:#ec4899; border-radius:4px;">
    
        <h1 style="position:relative; z-index:1; font-size:1.5rem; font-weight:700; color:#ffffff; margin:0; padding:8px;">
            Qwestar
         </h1>
    </div>
    <h2 class="title">Verification Code</h2>
    <p class="text">
        Please use the following verification code to proceed:
    </p>
   <div style="padding:24px; margin:24px auto; box-shadow:0 2px 8px #0001;">
     <div style="text-align:center; font-size:1.5rem; font-weight:700; color:#ec4899;">
       {code}
     </div>
   </div>
</div>
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
