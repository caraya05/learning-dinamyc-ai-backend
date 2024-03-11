from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from character.models import Character

from character.schemas import SchemaCreateCharacter
from character.schemas import SchemaUpdatePhotoCharacter
from character.schemas import SchemaRetrieveCharacter
from character.utils import get_extra_data_character_ai
from utils import upload_image
from weapon.services import get_weapon_by_field

from customize.services import get_customize_by_type_character_service

from customize.utils import get_customize_by_character


def get_character_by_field(db: Session, field: str, value: str, game_id: str = None):
    if game_id:
        return db.query(Character).filter(getattr(Character, field) == value, Character.game_id == game_id).first()
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
    # try:
    #     if game_id:
    all_ = db.query(Character).filter(Character.game_id == game_id).offset(skip).limit(limit).all()
    for character__ in all_:
        weapon_ = get_weapon_by_field(db, "character_id", character__.id)
        if weapon_:
            character__.weapon = weapon_
        else:
            character__.weapon = ""
    return all_


# return db.query(Character).offset(skip).limit(limit).all()
# except Exception as e:
#     print("Error character  ", e)
#     raise HTTPException(
#         status_code=status.HTTP_400_BAD_REQUEST,
#         detail="Characters not found",
#     )


def create_character_service(db: Session, character: SchemaCreateCharacter, user_id: str):
    try:
        db_character = Character(**character.dict())
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


def update_partial_character_service(db: Session, character_id: str, character_update: SchemaUpdatePhotoCharacter):
    character_db = get_character_by_field(db, 'id', character_id)
    if character_db:
        image_name = f"{character_db.name.replace(' ', '_')}"
        character_update.image = upload_image(url_image=character_update.image,
                                              file_name=f"{character_db.game_id}/characters/{image_name}.jpg",
                                              size=(512, 512))

        prompt_content_extra_data = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe a detalle el personaje con la siquiente imagen y la descrpccion del personaje, extrae los colores de la piel, cabello, ojos, labios, zapatos, pantalones y camisa."
                                "en dado caso que una prenda no este visible colocar un color adorde a los demas colores."
                    },
                    {
                        "type": "text",
                        "text": f"Descripcion del personaje: {character_db.description}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": character_update.image
                        }
                    }
                ]
            }
        ]

        extra_data = get_extra_data_character_ai(prompt_content_extra_data)

        print("extra_data", str(extra_data))


        character_db.extra_data = extra_data["extra_data"]

        if character_db.genre in ["woman", "man"]:
            print("character_db.genre", character_db.genre)
            customizes_db = get_customize_by_type_character_service(db, character_db.genre, "hair")

            customize_character = get_customize_by_character(customizes_db,
                                                             character_db.description)

            character_db.extra_data["type_combing"] = customize_character["reference_ui"]

        print("character_db.extra_data", str(character_db.extra_data))


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
