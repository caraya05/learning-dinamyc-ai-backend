from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi import status

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
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_IN),
        "type": TokenType.ACCESS.value,
    }
    refresh = access.copy()
    refresh.update(
        {
            "exp": datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRES_IN),
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
                exp_date = datetime.fromtimestamp(exp)
                if exp_date > datetime.utcnow():
                    return True
    return False
