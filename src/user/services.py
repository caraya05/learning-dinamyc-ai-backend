from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from record_daily.service import register_daily_record_service

from user.schemas import SchemaUser

from user.utils import get_password_hash
from core.database import db

from user.models import User

from configuration.services import get_configurations_service


async def create_user_service(user: SchemaUser):
    if user_db := await db["user"].find_one({"email": user.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Correo electrónico ya registrado - email",
        )
    if user_db := await db["user"].find_one({"username": user.username}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de usuario ya registrado - username",
        )

    db_user = User(**user.dict())
    db_user.password = get_password_hash(db_user.password)
    new_user = await db["user"].insert_one(db_user.dict())
    user_created = await db["user"].find_one({"_id": new_user.inserted_id})

    return user_created


async def get_user_by_field(field: str, value: str):
    game_db = await db["user"].find_one({field: value})
    return game_db


# def get_list_user(skip: int = 0, limit: int = 100):
#     return user_document.find()


# def update_user_service(user_id: str, user_update: SchemaUpdateUser):
#     user_db = get_user_by_field('id', user_id)
#     if user_db:
#         user_db.username = user_update.username
#         user_db.email = user_update.email
#         db.commit()
#         db.refresh(user_db)
#         return user_db
#     else:
#         return None


# def partial_update_user_service(user_id: str, user_update: SchemaPartialUpdateUser):
#     user_db = get_user_by_field('id', user_id)
#     for key, value in user_update.dict(exclude_unset=True).items():
#         setattr(user_db, key, value)
#     db.commit()
#     db.refresh(user_db)
#     return user_db


# async def get_current_user_service(user: dict):
#     try:
#         user: str | None = user.get("sub", None)
#         print("user", user)
#         if user is None:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username")
#         user_db = await db["user"].find_one({"_id": ObjectId(user)})
#         print("user_db", user_db)
#         return user_db
#     except Exception as ex:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username"
#         ) from ex


# def update_password_service(change_password: SchemaUpdatePassword):
#     user_db = get_user_by_field("token_change_password", change_password.token_change_password)
#     if user_db:
#         user_db.password = get_password_hash(change_password.password)
#         db.commit()
#         db.refresh(user_db)
#         return user_db
#     else:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_or_created_user_service(user: dict):
    try:
        user_db = await db["user"].find_one({"email": user.email})
        if user_db:
            return user_db.get("_id"), user_db.get("password")

        configuration_db = await get_configurations_service()
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
                stars=configuration_db["stars_news_users"] if configuration_db.get("stars_news_users", None) else 20,
            )
            new_user = await db["user"].insert_one(user_db_.dict())
            user_created = await db["user"].find_one({"_id": new_user.inserted_id})
            return user_created.get("_id"), user_created.get("password")
        except Exception as e:
            print("Error in create user", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"User not created {e}"
            )
    except Exception as e:
        print("Error in create user", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"User not created {e}"
        )


async def deduct_stars_service(user_id: str, stars: int):
    try:
        user_db = await db["user"].find_one({"_id": ObjectId(user_id)})
        if user_db:
            user_db["stars"] -= stars
            await register_daily_record_service(
                user_id=user_id,
                created_at=datetime.utcnow(),
                balance=user_db["stars"],
                expenses=stars,
                games_created=1,
                sets_with_errors=0,
                attempts_to_create_without_balance=0,
            )
            await db["user"].update_one({"_id": ObjectId(user_id)}, {"$set": user_db})
            return await db["user"].find_one({"_id": ObjectId(user_id)})
        else:
            return None
    except Exception as e:
        print(f"Error in deduct stars {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error in deduct stars {e}"
        )


async def update_photo_service(user_id: str, photo: str):
    try:
        user_db = await db["user"].find_one({"_id": ObjectId(user_id)})
        if user_db:
            user_db['photo'] = photo
            await db["user"].update_one({"_id": ObjectId(user_id)}, {"$set": user_db})
            return await db["user"].find_one({"_id": ObjectId(user_id)})
        else:
            return None
    except Exception as e:
        print(f"Error in update photo {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error in update photo {e}"
        )


async def update_attempt_to_create_service(user_id: str):
    try:
        user_db = await db["user"].find_one({"_id": ObjectId(user_id)})
        if user_db:
            user_db['attempt_to_create'] = True
            if user_db['stars'] is None:
                user_db['stars'] = 0
            if user_db['number_of_creation_attempts'] is None:
                user_db['number_of_creation_attempts'] = 0
            user_db['number_of_creation_attempts'] += 1
            await register_daily_record_service(
                user_id=user_id,
                created_at=datetime.utcnow(),
                balance=user_db['stars'],
                attempts_to_create_without_balance=1,
            )
            await db["user"].update_one({"_id": ObjectId(user_id)}, {"$set": user_db})
            return await db["user"].find_one({"_id": ObjectId(user_id)})
        else:
            return None
    except Exception as e:
        print(f"Error in update attempt to create {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error in update attempt to create {e}"
        )


async def get_user_by_id_service(user_id: str):
    try:
        user_db = await db["user"].find_one({"_id": ObjectId(user_id)})
        return user_db
    except Exception as e:
        print(f"Error in get user by id {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error in get user by id {e}"
        )


async def disable_user_service(user_id: str, section: str):
    try:
        user_db = await db["user"].find_one({"_id": ObjectId(user_id)})
        stars_disabled = 0
        if section == "character":
            stars_disabled = 1
        elif section == "place":
            stars_disabled = 1
        elif section == "location":
            stars_disabled = 1
        elif section == "item":
            stars_disabled = 1
        if user_db:

            await register_daily_record_service(
                user_id=user_id,
                created_at=datetime.utcnow(),
                balance=user_db["stars"],
                expenses=stars_disabled,
                games_created=0,
                sets_with_errors=0,
                attempts_to_create_without_balance=0,
                assets_created={"section": section, "stars": stars_disabled}
            )

            user_db['stars'] = user_db['stars'] - stars_disabled
            await db["user"].update_one({"_id": ObjectId(user_id)}, {"$set": user_db})
        else:
            return None
    except Exception as e:
        print(f"Error in disable user {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error in disable user {e}"
        )
