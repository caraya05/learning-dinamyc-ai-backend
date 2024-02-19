from datetime import timedelta
from fastapi import HTTPException

from fastapi import APIRouter
from fastapi import Request
from fastapi import status
from fastapi import Depends
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import JWTDecodeError
from sqlalchemy.orm import Session
from fastapi.security import HTTPAuthorizationCredentials
from config import auth_scheme

from config import settings
from user.schemas import SchemaError

from .utils import get_user_authenticate, social_auth_firebase
from .schemas import SchemaTokenAccess
from .schemas import SchemaLogin

from firebase_auth import verify_token_firebase

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_db(request: Request):
    return request.state.db


# @router.post("/access", status_code=status.HTTP_200_OK, response_model=SchemaTokenAccess)
# def access_token(user: SchemaLogin, db: Session = Depends(get_db)):
#     """
#     OAuth2 compatible token_user login, get an access token_user for future requests
#     """
#     user_db = get_user_authenticate(db, user)
#     access_token_expires = timedelta(minutes=settings.authjwt_access_token_expires)
#     auth = AuthJWT()
#     return SchemaTokenAccess(
#         access=auth.create_access_token(
#             subject=user_db.id, expires_time=access_token_expires
#         ),
#         refresh=auth.create_refresh_token(
#             subject=user_db.id, expires_time=timedelta(hours=24)
#         ),
#     )


@router.post("/refresh", response_model=SchemaTokenAccess, status_code=status.HTTP_200_OK)
def refresh_token(
        Authorize: AuthJWT = Depends(),
        Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """
    OAuth2 compatible token_user refresh, get a new access token_user for future requests
    """
    try:
        Authorize.jwt_refresh_token_required()
        current_user = Authorize.get_raw_jwt()["sub"]
        return SchemaTokenAccess(
            access=Authorize.create_access_token(
                subject=current_user,
                expires_time=timedelta(minutes=settings.authjwt_access_token_expires),
            ),
            refresh=Authorize.create_refresh_token(
                subject=current_user, expires_time=timedelta(hours=24)
            ),
        )
    except JWTDecodeError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Error in decoder token_user") from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Error in refresh token_user") from e


@router.post("/verify", status_code=status.HTTP_200_OK)
def verify_token(
        Authorize: AuthJWT = Depends(),
        Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """
    Verify if token_user is valid
    """
    try:
        Authorize.jwt_required()
        return {"message": "Token is valid"}
    except JWTDecodeError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Error token expired") from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Error token expired") from e


@router.post("/google",
             status_code=status.HTTP_200_OK,
             responses={
                 200: {
                     "content": {"application/json": {"example": {"access": "string", "refresh": "string"}}},
                     "description": "Success",
                     "model": SchemaTokenAccess
                 },
                 400: {
                     "content": {"application/json": {"example": {"detail": "string"}}},
                     "description": "Bad Request",
                     "model": SchemaError
                 },
                 401: {
                     "content": {"application/json": {"example": {"detail": "string"}}},
                     "description": "Unauthorized",
                     "model": SchemaError
                 },
                 500: {
                     "content": {"application/json": {"example": {"detail": "string"}}},
                     "description": "Internal Server Error",
                     "model": SchemaError
                 }

             }
             )
def sign_in_with_google(data: dict, db: Session = Depends(get_db)):
    """
    Sign in with google

    """

    return social_auth_firebase(db, data)


@router.post("/apple",
             status_code=status.HTTP_200_OK,
             responses={
                 200: {
                     "content": {"application/json": {"example": {"access": "string", "refresh": "string"}}},
                     "description": "Success",
                     "model": SchemaTokenAccess
                 },
                 400: {
                     "content": {"application/json": {"example": {"detail": "string"}}},
                     "description": "Bad Request",
                     "model": SchemaError
                 },
                 401: {
                     "content": {"application/json": {"example": {"detail": "string"}}},
                     "description": "Unauthorized",
                     "model": SchemaError
                 },
                 500: {
                     "content": {"application/json": {"example": {"detail": "string"}}},
                     "description": "Internal Server Error",
                     "model": SchemaError
                 }

             }
             )
def sign_in_with_apple(data: dict={"uid":"4c8SEAwFb1ZORQ4psCpxOGQP0RK2"}, db: Session = Depends(get_db)):
    """
    Sign in with apple
    """
    return social_auth_firebase(db, data)
