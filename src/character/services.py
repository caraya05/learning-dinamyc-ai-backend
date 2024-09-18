from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from uuid import uuid4

from celery_worker import generate_character_task
from core.database import db

from character.models import Character

from character.schemas import SchemaCreateCharacter, CharacterLocationModel
from character.schemas import SchemaUpdatePhotoCharacter
from character.utils import get_extra_data_character_ai
from customize.services import get_customize_by_type_character_service
from customize.utils import get_customize_by_character
from task.services import create_task_service, update_task_service
from utils import upload_image


async def get_character_service(character_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    return character_db


async def get_characters_service(skip: int = 1, limit: int = 100, game_id: str = None):
    try:
        if characters_db := await db["character"].find({"game_id": game_id}).skip((skip - 1) * limit).limit(
                limit).to_list(None):
            return characters_db
        return None
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

        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=str(character_created.inserted_id),
            _element_type="character",
            _process="create_character"
        )

        task_celery = generate_character_task.delay(_character_id=str(character_created.inserted_id),
                                                  _user_id=user_id,
                                                  _task_id=str(task_db["_id"]))

        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
            _status="pending"
        )

        await db["character"].update_one({"_id": character_created.inserted_id},
                                         {"$set": {"tasks_request": [str(task_db["_id"])]}})

        if character_db := await db["character"].find_one({"_id": character_created.inserted_id}):
            character_db["task_id"] = str(task_db["_id"])
            return character_db
    except Exception as e:
        print(f"Error in create character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not created",
        )


# async def update_partial_character_service(character_id: str, character_update: SchemaUpdatePhotoCharacter):
#     try:
#         if character_db := await db["character"].find_one({"_id": ObjectId(character_id)}):
#             character_update.image = upload_image(
#                 url_image=character_update.image,
#                 file_name=f"characters/{uuid4()}.jpg",
#                 size=(512, 512),
#             )
#
#             prompt_content_extra_data = [
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": "text",
#                             "text": "Describe a detalle el personaje con la siquiente imagen y la descrpccion del personaje,"
#                                     " extrae los colores de la piel, cabello, ojos, labios, zapatos, pantalones y camisa."
#                                     "en dado caso que una prenda no este visible colocar un color adorde a los demas colores,"
#                                     "en dado caso de que la imagen no tenga colores colocar colores que se asemejen a la imagen."
#                                     "en dado caso no se puedan de terminar los colores colocar colores asocidos a la descripcion.",
#                         },
#                         {
#                             "type": "text",
#                             "text": f"Descripcion del personaje: {character_db['description']}",
#                         },
#                         {"type": "image_url", "image_url": {"url": character_update.image}},
#                     ],
#                 }
#             ]
#
#             extra_data = get_extra_data_character_ai(prompt_content_extra_data)
#
#             character_db['extra_data'] = extra_data["extra_data"]
#
#             if character_db['gender'] in ["woman", "man"]:
#                 customizes_db, count_customize = await get_customize_by_type_character_service(character_db['gender'],
#                                                                                                "hair")
#
#                 customize_character = get_customize_by_character(
#                     customizes_db, character_db['description']
#                 )
#
#                 character_db['extra_data']["type_combing"] = customize_character["reference_ui"]
#
#             character_db["image"] = character_update.image
#             await db["character"].update_one({"_id": ObjectId(character_id)},
#                                              {"$set": character_db})
#
#             character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
#             return character_db
#     except Exception as e:
#         print(f"Error in update partial character service: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Character not updated",
#         )


# async def get_character_leading_role_service(game_id: str):
#     try:
#         character_db = await db['character'].find_one({'game_id': game_id, 'type': 'leading role'})
#         if not character_db:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Character not found",
#             )
#         return character_db
#     except Exception as e:
#         print(f"Error in get character leading role service: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Character not found",
#         )

async def update_character_service(character_id: str, name: str, prompt_user: str):
    try:
        if character_db := await db["character"].find_one({"_id": ObjectId(character_id)}):
            if name:
                character_db["name"] = name
            if prompt_user:
                character_db["prompt_user"] = prompt_user
                json_response = {
                    "description": "string (basic description of the character in which describes the face, hair and aspects of the body that serves to generate other characters.)",
                    "gender": "string (gender of the character, the options are man or woman)",
                }

                response_collection = generate_gpt4o(
                    content_prompt=[
                        {
                            "role": "system",
                            "content": "Genera una descripcion para generar una imagen e identifica el genero del personaje "
                                       "entre hombre, mujer o ninguno, utilizando la descripción base del personaje."
                                       f"responde con un JSON que contenga el esquema {json_response}",
                        },
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": prompt_user}]
                        },
                    ],
                    type_text="collection",
                    model="gpt-4o",
                    max_tokens=4096
                )

                response = json.loads(response_collection)
                character_db["description"] = response.get("description")

            if body_type:
                character_db["body_type"] = body_type

            await db["character"].update_one({"_id": ObjectId(character_id)}, {"$set": character_db})
            character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
            return character_db

    except Exception as e:
        print(f"Error in update character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not updated",
        )



async def delete_character_service(character_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )
    # if character_db['image']:
    #     delete_image(character_db['image'])
    if character_location_db := await db["character_location"].find({"character_id": character_id}).to_list(None):
        for character_location in character_location_db:
            await db["character_location"].delete_one({"_id": character_location["_id"]})
    delete_character = await db["character"].delete_one({"_id": ObjectId(character_id)})
    if delete_character:
        return True
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Character not found",
    )


async def get_characters_by_location_service(skip: int = 1, limit: int = 100, location_id: str = None):
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})
    if not location_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    try:
        if characters_locations_db := await db["character_location"].find(
                {"location_id": location_id}).skip((skip - 1) * limit).limit(limit).to_list(None):
            characters_db = []
            for character_location in characters_locations_db:
                character_db = await db["character"].find_one({"_id": ObjectId(character_location["character_id"])})
                character_db["characteristics"] = character_location["characteristics"]
                character_db["_id"] = str(character_db["_id"])
                characters_db.append(character_db)

            return characters_db
    except Exception as e:
        print(f"Error in get characters service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characters not found",
        )


async def add_character_to_location_service(character_id: str, location_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})

    if not character_db or not location_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character or Location not found",
        )
    try:
        existing_entry = await db["character_location"].find_one(
            {"character_id": character_id, "location_id": location_id})

        if existing_entry:
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="Character already added to location",
            )

        character_location_data = CharacterLocationModel(
            character_id=character_id,
            location_id=location_id,
            characteristics={},
            created_by=character_db["created_by"],
            updated_by=character_db["updated_by"]
        )
        await db["character_location"].insert_one(character_location_data.dict())

    except Exception as e:
        print(f"Error in add character to location service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not added to location",
        )

    return "character added to location"


async def add_or_edit_character_location(character_id: str, location_id: str, characteristics: dict, user_id: str):
    existing_entry = await db["character_location"].find_one({"character_id": character_id, "location_id": location_id})

    if existing_entry:
        await db["character_location"].update_one(
            {"_id": existing_entry["_id"]},
            {"$set": {
                "characteristics": characteristics,
                "updated_by": user_id,
                "updated_at": datetime.utcnow()
            }}
        )
        return "Character location updated successfully"
    else:
        character_location_data = CharacterLocationModel(
            character_id=character_id,
            location_id=location_id,
            characteristics=characteristics,
            created_by=user_id,
            updated_by=user_id
        )
        await db["character_location"].insert_one(character_location_data.dict())
        return "Character location added successfully"


async def get_all_character_service(user_id: str, skip: int = 1, limit: int = 10):
    try:
        characters_db = await (db["character"]
                               .find({"created_by": user_id})
                               .sort("created_at", -1)
                               .skip((skip - 1) * limit)
                               .limit(limit)
                               .to_list(None))
        return characters_db
    except Exception as e:
        print(f"Error in get all character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characters not found",
        )
