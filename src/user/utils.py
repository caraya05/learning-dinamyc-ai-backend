from fastapi import HTTPException
from fastapi import status
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception as ex:
        print("error",ex)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error in convert"
        ) from ex


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as ex:
        return False


def verify_is_superuser(data_user) -> bool:
    if data_user.is_superuser:
        return True
    else:
        return False


def verify_is_staff(data_user) -> bool:
    if data_user.is_staff:
        return True
    else:
        return False


