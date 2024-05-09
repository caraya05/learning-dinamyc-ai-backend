from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from uuid import uuid4

from core.database import db

from character.models import Character

from character.schemas import SchemaCreateCharacter
from character.schemas import SchemaUpdatePhotoCharacter
from character.utils import get_extra_data_character_ai
from customize.services import get_customize_by_type_character_service
from customize.utils import get_customize_by_character
from utils import upload_image


async def get_character_service(character_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    print()
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    return character_db


async def get_characters_service(skip: int = 0, limit: int = 100, game_id: str = None):
    try:
        if characters_db := await db["character"].find({"game_id": game_id}).skip(skip).limit(limit).to_list(None):
            return characters_db
    except Exception as e:
        print(f"Error in get characters service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characters not found",
        )


async def create_character_service(character: SchemaCreateCharacter, user_id: str):
    try:
        character_db = Character(**character.dict())
        character_db.created_by = user_id
        character_db.updated_by = user_id
        character_created = await db["character"].insert_one(character_db.dict())
        print("character_created", character_created.inserted_id)
        if character_db := await db["character"].find_one({"_id": character_created.inserted_id}):
            return character_db
    except Exception as e:
        print(f"Error in create character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not created",
        )


async def update_partial_character_service(character_id: str, character_update: SchemaUpdatePhotoCharacter):
    try:
        if character_db := await db["character"].find_one({"_id": ObjectId(character_id)}):
            character_update.image = upload_image(
                url_image=character_update.image,
                file_name=f"characters/{uuid4()}.jpg",
                size=(512, 512),
            )

            prompt_content_extra_data = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe a detalle el personaje con la siquiente imagen y la descrpccion del personaje,"
                                    " extrae los colores de la piel, cabello, ojos, labios, zapatos, pantalones y camisa."
                                    "en dado caso que una prenda no este visible colocar un color adorde a los demas colores,"
                                    "en dado caso de que la imagen no tenga colores colocar colores que se asemejen a la imagen."
                                    "en dado caso no se puedan de terminar los colores colocar colores asocidos a la descripcion.",
                        },
                        {
                            "type": "text",
                            "text": f"Descripcion del personaje: {character_db['description']}",
                        },
                        {"type": "image_url", "image_url": {"url": character_update.image}},
                    ],
                }
            ]

            extra_data = get_extra_data_character_ai(prompt_content_extra_data)

            character_db['extra_data'] = extra_data["extra_data"]

            if character_db['gender'] in ["woman", "man"]:
                print("character")
                customizes_db, count_customize = await get_customize_by_type_character_service(character_db['gender'],
                                                                                               "hair")

                customize_character = get_customize_by_character(
                    customizes_db, character_db['description']
                )

                character_db['extra_data']["type_combing"] = customize_character["reference_ui"]

            character_db["image"] = character_update.image
            await db["character"].update_one({"_id": ObjectId(character_id)},
                                             {"$set": character_db})

            character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
            return character_db
    except Exception as e:
        print(f"Error in update partial character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not updated",
        )


async def update_attempts_character_service(character_id: str):
    if character_db := await db["character"].find_one({"_id": ObjectId(character_id)}):
        attempts = character_db.get("attempts", 0)
        character_update = {"attempts": attempts + 1}
        character_db = await db["character"].update_one({"_id": character_id}, {"$set": character_update})

        return character_db
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Character not found",
    )


async def get_character_leading_role_service(game_id: str):
    try:
        character_db = await db['character'].find_one({'game_id': game_id, 'type': 'leading role'})
        if not character_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found",
            )
        return character_db
    except Exception as e:
        print(f"Error in get character leading role service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not found",
        )


async def delete_character_service(character_id: str):
    delete_character = await db["character"].delete_one({"_id": character_id})
    if delete_character.deleted_count:
        return True
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Character not found",
    )
