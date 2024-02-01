from datetime import timedelta

from sqlalchemy.orm import Session

from config import settings
from firebase_auth import get_user_token_firebase

from fastapi import HTTPException
from fastapi import status
from auth.schemas import SchemaLogin, SchemaTokenAccess
from fastapi_jwt_auth import AuthJWT

from user.services import get_or_created_user_service
from user.utils import verify_password
from user.models import User
from user.schemas import SchemaRetrieveUser

def get_user_authenticate(db: Session, user: SchemaLogin) -> User:
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Credentials Invalid"
        )
    # if not db_user.is_active:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user"
    #     )
    if not verify_password(user.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )
    return db_user


def generate_tokens(user: User):
    # data = {
    #     "id": user.id,
    #     "username": user.username,
    #     "email": user.email,
    #     "is_active": user.is_active,
    #     "is_superuser": user.is_superuser,
    # }
    access_token_expires = timedelta(minutes=settings.authjwt_access_token_expires)
    auth = AuthJWT()
    return SchemaTokenAccess(
        access=auth.create_access_token(
            subject=user.id, expires_time=access_token_expires
        ),
        refresh=auth.create_refresh_token(
            subject=user.id, expires_time=timedelta(hours=24)
        ),
    )


def social_auth_firebase(db: Session, data: dict):
    user_token = get_user_token_firebase(data)

    user_db = get_or_created_user_service(db, user_token)

    return generate_tokens(user_db)
