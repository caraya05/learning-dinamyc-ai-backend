from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from character.models import Character

from character.schemas import SchemaCreateCharacter
from character.schemas import SchemaPartialUpdateCharacter


def get_character_by_field(db: Session, field: str, value: str):
    return db.query(Character).filter(getattr(Character, field) == value).first()


def get_character_service(db: Session, character_id: str):
    character_db = get_character_by_field(db, 'id', character_id)
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )
    return character_db


def get_characters_service(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Character).offset(skip).limit(limit).all()


def create_character_service(db: Session, character: SchemaCreateCharacter, game_id: str, user_id: str):
    try:
        db_character = Character(**character.dict())
        db_character.game_id = game_id
        db_character.created_by = user_id
        db_character.updated_by = user_id
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


def update_partial_character_service(db: Session, character_id: str, character_update: SchemaPartialUpdateCharacter):
    character_db = get_character_by_field(db, 'id', character_id)
    if character_db:
        for key, value in character_update.dict().items():
            setattr(character_db, key, value)
        db.commit()
        db.refresh(character_db)
        return character_db
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Character not found",
    )
