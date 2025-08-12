from datetime import datetime, timedelta, timezone
import random

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status
from pydantic import EmailStr

from jose import ExpiredSignatureError
from jose import JWTError
from jose import jwt
from jose.exceptions import JWTClaimsError

from config import settings

from firebase_auth import get_user_token_firebase

from auth.enums import TokenType
from auth.utils import verify_password

from core.database import PyObjectId
from core.database import db

from user.services import get_or_created_user_service
from auth.schemas import VerificationCodeDB


async def authenticate_user(email: str, password: str) -> dict | None:
    if user := await db["user"].find_one({"email": email}):
        if verify_password(password, user.get("password")):
            if user.get("is_active"):
                return user
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your account is banned",
            )


async def authenticate_token(user_id: str, password_ts: float) -> dict | None:
    try:
        user_id = PyObjectId(user_id)
    except ValueError:
        return None
    if user := await db["user"].find_one({"_id": user_id}):
        if password_ts == user.get("password"):
            if user.get("is_active"):
                return user
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your account is banned",
            )


async def generate_token(user_id: PyObjectId, password_ts: float) -> dict:
    access = {
        "user_id": str(user_id),
        "password_ts": password_ts,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_IN),
        "type": TokenType.ACCESS.value,
    }
    refresh = access.copy()
    refresh.update(
        {
            "exp": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRES_IN),
            "type": TokenType.REFRESH.value,
        }
    )
    access_token = jwt.encode(access, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {
        "access": access_token,
        "refresh": refresh_token,
        "token_type": "bearer",
    }


async def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
    except (JWTError, ExpiredSignatureError, JWTClaimsError):
        return None


async def auth_access(token: str) -> dict | None:
    if payload := await decode_token(token):
        if payload.get("type") == TokenType.ACCESS.value:
            if user := await authenticate_token(payload.get("user_id"), payload.get("password_ts")):
                if user.get("is_active"):
                    return user


async def auth_refresh(token: str) -> dict | None:
    if payload := await decode_token(token):
        if payload.get("type") == TokenType.REFRESH.value:
            if user := await authenticate_token(payload.get("user_id"), payload.get("password_ts")):
                return await generate_token(
                    user_id=user.get("_id"), password_ts=user.get("password")
                )


async def social_auth_firebase(data: dict):
    user_token = await get_user_token_firebase(data)
    user_id, user_password = await get_or_created_user_service(user_token)
    return await generate_token(user_id, user_password)


async def is_token_valid(token: str) -> bool:
    if payload := await decode_token(token):
        if payload.get("type") == TokenType.ACCESS.value:
            exp = payload.get("exp")
            if exp:
                exp_date = datetime.fromtimestamp(exp, tz=timezone.utc)  # Asegura que sea offset-aware
                if exp_date > datetime.now(timezone.utc):
                    return True
    return False


async def authenticate_by_game_code(code: str) -> dict | None:
    """
    Autentica a un usuario mediante un código de juego.

    Args:
        code: El código de juego proporcionado por el usuario

    Returns:
        Un diccionario con la información del usuario si la autenticación es exitosa, None en caso contrario
    """
    if game := await db["game"].find_one({"_id": ObjectId(code)}):
        # Verificar si el código no ha expirado

        # Si el código es válido, obtener o crear el usuario asociado
        user_id = game.get("created_by")
        if not user_id:
            # Si no hay usuario asociado, crear uno anónimo
            new_user = {
                "email": f"game_user_{code}@qwestar.com",
                "password": str(datetime.now(timezone.utc).timestamp()),
                "is_active": True,
                "is_anonymous": True,
                "created_at": datetime.now(timezone.utc),
            }
            result = await db["user"].insert_one(new_user)
            user_id = str(result.inserted_id)

            # Asociar el usuario al código de juego
            await db["game_code"].update_one(
                {"_id": game.get("_id")},
                {"$set": {"created_by": user_id}},
            )

        # Obtener el usuario
        user = await db["user"].find_one({"_id": ObjectId(user_id)})
        if user and user.get("is_active"):
            user["_id"] = str(user["_id"])  # Convertir a string para consistencia
            return user

    return None


async def generate_verification_code(email: EmailStr) -> str:
    """
    Genera un código de verificación de 6 dígitos y lo almacena en la base de datos.
    """
    code = f"{random.randint(100000, 999999)}"
    verification_entry = VerificationCodeDB(
        email=email,
        code=code,
        created_at=datetime.now(timezone.utc)
    )
    await db["verification_codes"].insert_one(verification_entry.dict())
    return code


async def validate_verification_code(email: str, code: str) -> bool:
    """
    Valida si el código de verificación es correcto y no ha expirado.
    """
    entry = await db["verification_codes"].find_one({"email": email, "code": code})
    if not entry:
        return False

    created_at = entry.get("created_at")
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) - created_at > timedelta(hours=1):
        return False

    return True
