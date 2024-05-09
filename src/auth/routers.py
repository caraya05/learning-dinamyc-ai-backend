from auth.services import social_auth_firebase
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from auth.schemas import Credentials, Refresh, Token
from auth.services import auth_refresh, authenticate_user, generate_token
from core.schemas import ExceptionModel

router = APIRouter(prefix="/auth", tags=["Auth"])


# @router.post("/verify", status_code=status.HTTP_200_OK)
# def verify_token(
#         user: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     """
#     Verify if token_user is valid
#     """
#     try:
#         Authorize.jwt_required()
#         return {"message": "Token is valid"}
#     except JWTDecodeError as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail="Error token expired"
#         ) from e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail="Error token expired"
#         ) from e

@router.post(
    "/token",
    response_model=Token,
    responses={401: {"model": ExceptionModel}}
)
async def token(credentials: Credentials):
    if user := await authenticate_user(
            email=credentials.email,
            password=credentials.password,
    ):
        return await generate_token(
            user_id=user.get("_id"),
            password_ts=user.get("password_ts"),
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/google",
    status_code=status.HTTP_200_OK
)
async def sign_in_with_google(data: dict):
    """
    Sign in with google

    """
    return await social_auth_firebase(data)


@router.post(
    "/apple",
    status_code=status.HTTP_200_OK
)
async def sign_in_with_apple(data: dict ):
    """
    Sign in with apple
    """
    return await social_auth_firebase(data)


@router.post(
    "/refresh",
    response_model=Token,
    responses={401: {"model": ExceptionModel}}
)
async def refresh(payload: Refresh):
    if new_token := await auth_refresh(token=payload.refresh_token):
        return new_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
