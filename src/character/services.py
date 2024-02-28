from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from character.models import Character

from character.schemas import SchemaCreateCharacter
from character.schemas import SchemaUpdatePhotoCharacter
from character.schemas import SchemaRetrieveCharacter
from utils import upload_image
from weapon.services import get_weapon_by_field

from customize.services import get_customize_by_type_character_service

from customize.utils import get_customize_by_character


def get_character_by_field(db: Session, field: str, value: str):
    return db.query(Character).filter(getattr(Character, field) == value).first()


def get_character_service(db: Session, character_id: str):
    character_db = get_character_by_field(db, 'id', character_id)
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    weapon_ = get_weapon_by_field(db, "character_id", character_db.id)
    if weapon_:
        character_db.weapon = weapon_
    else:
        character_db.weapon = ""

    return character_db


def get_characters_service(db: Session, skip: int = 0, limit: int = 100, game_id: str = None):
    try:
        if game_id:
            all_ = db.query(Character).filter(Character.game_id == game_id).offset(skip).limit(limit).all()
            for character__ in all_:
                weapon_ = get_weapon_by_field(db, "character_id", character__.id)
                if weapon_:
                    character__.weapon = weapon_
                else:
                    character__.weapon = ""

            return all_
        return db.query(Character).offset(skip).limit(limit).all()
    except Exception as e:
        print("Error character  ", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Characters not found",
        )


def create_character_service(db: Session, character: SchemaCreateCharacter, user_id: str):
    try:
        db_character = Character(**character.dict())
        db_character.created_by = user_id
        db_character.updated_by = user_id
        print("genero :   ", character.genre)
        if character.genre in ["woman", "man"]:
            all_customizes = get_customize_by_type_character_service(db, character.genre, "hair")

            customize_character = get_customize_by_character(all_customizes,
                                                             db_character.description)

            print(customize_character)
            print("customize_character")

            db_character.extra_data["hair_ui"] = customize_character["id"]

        db.add(db_character)
        db.commit()
        db.refresh(db_character)
        return db_character
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not created",
        )


def update_partial_character_service(db: Session, character_id: str, character_update: SchemaUpdatePhotoCharacter):
    character_db = get_character_by_field(db, 'id', character_id)
    if character_db:

        image_name = f"{character_db.name.replace(' ', '_')}"
        character_update.image = upload_image(url_image=character_update.image,
                                              file_name=f"{character_db.game_id}/characters/{image_name}.jpg")

        for key, value in character_update.dict().items():
            setattr(character_db, key, value)
        db.commit()
        db.refresh(character_db)
        return character_db
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Character not found",
    )


def update_attempts_character_service(db: Session, character_id: str):
    character_db = get_character_by_field(db, 'id', character_id)
    if character_db:
        character_db.attempts = character_db.attempts - 1
        db.commit()
        db.refresh(character_db)
        return character_db
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Character not found",
    )


def get_character_leading_role_service(db: Session, game_id: str):
    try:
        return db.query(Character).filter(Character.game_id == game_id, Character.type == 'leading role').first()
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not found",
        )
