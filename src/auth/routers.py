from auth.services import social_auth_firebase
from auth.services import is_token_valid
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status
from auth.schemas import Credentials
from auth.schemas import Refresh
from auth.schemas import Token
from auth.services import auth_refresh
from auth.services import authenticate_user
from auth.services import generate_token
from core.schemas import ExceptionModel

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/verify", status_code=status.HTTP_200_OK)
def verify_token(
        token: dict = {"access": ""},
):
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
async def sign_in_with_apple(data: dict):
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
