from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from .schemas import SchemaUser
from .schemas import SchemaPartialUpdateUser
from .schemas import SchemaUpdateUser
from .schemas import SchemaUpdatePassword
from .models import User
from .utils import get_password_hash


def create_user_service(db: Session, user: SchemaUser):
    if get_user_by_field(db, 'email', user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de la empresa ya registrado - company_name",
        )
    if get_user_by_field(db, 'phone_number', user.phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de teléfono ya registrado - phone_number",
        )
    if get_user_by_field(db, 'username', user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de usuario ya registrado - username",
        )

    db_user = User(**user.dict())
    db_user.password = get_password_hash(db_user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_field(db: Session, field: str, value: str):
    return db.query(User).filter(getattr(User, field) == value).first()


def get_list_user(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()


def update_user_service(db: Session, user_id: str, user_update: SchemaUpdateUser):
    user_db = get_user_by_field(db, 'id', user_id)
    if user_db:

        user_db.username = user_update.username
        user_db.email = user_update.email
        db.commit()
        db.refresh(user_db)
        return user_db
    else:
        return None


def partial_update_user_service(db: Session, user_id: str, user_update: SchemaPartialUpdateUser):
    user_db = get_user_by_field(db, 'id', user_id)
    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(user_db, key, value)
    db.commit()
    db.refresh(user_db)
    return user_db


def get_current_user_service(db: Session, user: dict) -> User:
    try:
        user: str | None = user.get("sub", None)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username"
            )
        user_db = get_user_by_field(db, "id", user)
        return user_db
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username"
        ) from ex


def update_password_service(db: Session, change_password: SchemaUpdatePassword):
    user_db = get_user_by_field(db, "token_change_password", change_password.token_change_password)
    if user_db:
        user_db.password = get_password_hash(change_password.password)
        db.commit()
        db.refresh(user_db)
        return user_db
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def get_or_created_user_service(db: Session, user: dict):
    user_db = get_user_by_field(db, "email", user.email)
    if user_db:
        return user_db
    else:

        username = user.display_name if user.display_name else user.email.split("@")[0]

        try:
            user_db_ = User(
                email=user.email,
                username=username,
                password=get_password_hash(user.email + user.uid),
                provider=user.provider_id,
                is_active=True,
                uid=user.uid,
                photo=user.photo_url if user.photo_url else None,
                created_by=user.email,
                updated_by=user.email,
            )
            db.add(user_db_)
            db.commit()
            db.refresh(user_db_)
            return user_db_
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"User not created {e}"
            )
