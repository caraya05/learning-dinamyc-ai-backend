from fastapi import Depends, HTTPException, Request, status

from auth.services import auth_access


async def auth_header(request: Request) -> str | None:
    if authorization := request.headers.get("Authorization"):
        scheme, _, token = authorization.partition(" ")
        if scheme and token and scheme.lower() == "bearer":
            return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Authorization Header",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def auth_base(token: str) -> dict:
    if user := await auth_access(token=token):
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def auth(token: str = Depends(auth_header)) -> dict:
    return await auth_base(token=token)


async def auth_admin(token: str = Depends(auth_header)) -> dict:
    if user_admin := await auth_base(token=token):
        if user_admin.get("is_superuser") and user_admin.get("is_active") and user_admin.get("is_staff"):
            return user_admin
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User is not an admin",
        headers={"WWW-Authenticate": "Bearer"},
    )
