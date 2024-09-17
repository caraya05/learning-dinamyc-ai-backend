import json
from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from uuid import uuid4

from pyasn1_modules.rfc2985 import gender

from core.database import db

from character.models import Character

from character.schemas import SchemaCreateCharacter, CharacterLocationModel
from character.schemas import SchemaUpdatePhotoCharacter
from character.utils import get_extra_data_character_ai
from customize.services import get_customize_by_type_character_service
from customize.utils import get_customize_by_character
from gpt_ai.utils import generate_gpt4_
from gpt_ai.utils import generate_gpt4o
from gpt_ai.utils import generate_image_dalle
from prompt.services import get_prompt_by_category_service
from utils import upload_image, delete_image


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

            # prompt_content_extra_data = [
            #     {
            #         "role": "user",
            #         "content": [
            #             {
            #                 "type": "text",
            #                 "text": "Describe a detalle el personaje con la siquiente imagen y la descrpccion del personaje,"
            #                         " extrae los colores de la piel, cabello, ojos, labios, zapatos, pantalones y camisa."
            #                         "en dado caso que una prenda no este visible colocar un color adorde a los demas colores,"
            #                         "en dado caso de que la imagen no tenga colores colocar colores que se asemejen a la imagen."
            #                         "en dado caso no se puedan de terminar los colores colocar colores asocidos a la descripcion.",
            #             },
            #             {
            #                 "type": "text",
            #                 "text": f"Descripcion del personaje: {character_db['description']}",
            #             },
            #             {"type": "image_url", "image_url": {"url": character_update.image}},
            #         ],
            #     }
            # ]

            # extra_data = get_extra_data_character_ai(prompt_content_extra_data)

            # character_db['extra_data'] = extra_data["extra_data"]

            # if character_db['genre'] in ["woman", "man"]:
            #     customizes_db, count_customize = await get_customize_by_type_character_service(character_db['gender'],
            #                                                                                    "hair")

                # customize_character = get_customize_by_character(
                #     customizes_db, character_db['description']
                # )
                #
                # character_db['extra_data']["type_combing"] = customize_character["reference_ui"]

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


async def create_character_by_collection_service(*,
                                                 user_id: str,
                                                 name: str,
                                                 prompt_user: str,
                                                 ):

    json_response_1= {
        "body_type": "string (are the types of body types that are available for the character the options are adult, child, animal)",
        "genre": "string (are the types of genres that are available for the character the options are man, woman if the character is adult or child, if animal it is null)",
    }

    response_1 = generate_gpt4o(
        content_prompt=[
            {
                "role": "system",
                "content": "Eres un identificador de genero y tipo de cuerpo de un personaje, "
                           f" responde con un JSON que contenga el esquema {json_response_1}",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"nombre del personaje: {name} y descripción del personaje por parte del usuario: {prompt_user}",
                    },
                ],
            },
        ],
        type_text="collection",
        model="gpt-4o",
        max_tokens=4096
    )

    response_1 = json.loads(response_1)

    json_response_2 = {
        "character_type": "string (are the types of characters that are available for the character)",
    }

    character_type_db = await db["character_type"].find({"body_type": response_1["body_type"], "genre": response_1["genre"]}).to_list(None)

    response_2 = generate_gpt4o(
        content_prompt=[
            {
                "role": "system",
                "content": "Eres un identificador de tipo de personaje, "
                           f" responde con un JSON que contenga el esquema {json_response_2}",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"nombre del personaje: {name} y descripción del personaje por parte del usuario: {prompt_user}",
                    },
                    {
                        "type": "text",
                        "text": f"escoge uno de los siquientes tipos de personajes: {character_type_db}",
                    }
                ],
            },
        ],
        type_text="collection",
        model="gpt-4o",
        max_tokens=4096
    )

    response_2 = json.loads(response_2)


    # if response_1["body_type"] in ["woman", "man", "MAN", "WOMAN"]:
    #     customizes_db, count_customize = await get_customize_by_type_character_service(response_1["body_type"], "hair")

    json_response = {
        "description": "string (description to identify the colors that the character has, it is necessary to know the"
                       " colors of clothes, shoes, hair, skin, eyes and lips.)",
        "description_shoulder_up": "string (15-word description cut from the head to the waist of the character, to generate an image of the character).",
    }

    response_collection = generate_gpt4o(
        content_prompt=[
            {
                "role": "system",
                "content": "crear una descripcion para indentificar aspectos visuales del personaje y poder generar una imagen"
                           f" responde con un JSON que contenga el esquema {json_response}",
            },
            # {
            #     "role": "assistant",
            #     "content": [
            #         {
            #             "type": "text",
            #             "text": f"escoge uno de los siquientes tipos de cabello: {customizes_db}",
            #         },
            #     ],
            # },
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

    character = SchemaCreateCharacter(
        name=name,
        created_by=user_id,
        updated_by=user_id,
        description=response.get("description"),
        body_type=response_1["body_type"],
        prompt_user=prompt_user,
        genre=response_1["genre"],
        character_type=response_2["character_type"]
    )

    character_db = Character(**character.dict())
    if response.get("description_shoulder_up"):
        character_db.description_shoulder_up = response.get("description_shoulder_up")
    character_created = await db["character"].insert_one(character_db.dict())
    if character_db := await db["character"].find_one({"_id": character_created.inserted_id}):
        return character_db


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


async def get_images_character_face_service(character_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )
    try:
        # image_face = generate_image_dalle(prompt=f"Genera una imagen en arte pixel de extraordinaria calidad, "
        #                                          f"de la cara vista closeup de frente de personaje en la imagen, con "
        #                                          f"fondo blanco, descripcción del personaje:"
        #                                          f" {character_db['prompt_user']}",
        #                                   quality="hd",
        #                                   size="1024x1024")

        description_character = character_db['description_shoulder_up'] \
            if character_db.get("description_shoulder_up", None) \
            else character_db['prompt_user']

        image_face = generate_image_dalle(
            prompt=f"Genera una imagen cuadrada en vista frontal de {description_character},"
                   " de ojos vivos, rasgos faciales exagerados y expresivos, de la "
                   "cintura para arriba, en estilo 3D Cel-shaded que Imita el aspecto "
                   "de los dibujos animados 2D, utilizando colores planos pero vivos y "
                   f"contornos marcados. Con fondo Blanco. el sexo del personaje es {character_db['body_type']}",
            quality="hd",
            size="1024x1024")

        # if character_db['image']:
        #     delete_image(character_db['image'])

        character_db['image'] = upload_image(
            url_image=image_face,
            file_name=f"characters/{uuid4()}.jpg",
            size=(512, 512),
        )
        # customizes_db = []
        # if character_db['body_type'] in ["woman", "man", "MAN", "WOMAN"]:
        #     customizes_db, count_customize = await get_customize_by_type_character_service(character_db['body_type'],
        #                                                                                    "hair")

        # prompt_content_extra_data = [
        #     {
        #         "role": "system",
        #         "content": "Describe a detalle el personaje con la siquiente imagen y la descrpccion del personaje,"
        #                    " extrae los colores de la piel, cabello, ojos, labios, zapatos, pantalones y camisa."
        #                    "en dado caso que una prenda no este visible colocar un color adorde a los demas colores,"
        #                    "en dado caso de que la imagen no tenga colores colocar colores que se asemejen a la imagen."
        #                    "en dado caso no se puedan de terminar los colores colocar colores asocidos a la descripcion.",
        #     },
        #     {
        #         "role": "assistant",
        #         "content": [
        #             {
        #                 "type": "text",
        #                 "text": f"tipos de peinados: {customizes_db}",
        #             },
        #         ],
        #     },
        #     {
        #         "role": "user",
        #         "content": [
        #             # {
        #             #     "type": "text",
        #             #     "text": "Describe a detalle el personaje con la siquiente imagen y la descrpccion del personaje,"
        #             #             " extrae los colores de la piel, cabello, ojos, labios, zapatos, pantalones y camisa."
        #             #             "en dado caso que una prenda no este visible colocar un color adorde a los demas colores,"
        #             #             "en dado caso de que la imagen no tenga colores colocar colores que se asemejen a la imagen."
        #             #             "en dado caso no se puedan de terminar los colores colocar colores asocidos a la descripcion.",
        #             # },
        #             {
        #                 "type": "text",
        #                 "text": f"Descripcion del personaje: {character_db['description']}",
        #             },
        #             {"type": "image_url", "image_url": {"url": character_db["image"]}},
        #         ],
        #     }
        # ]

        # extra_data = get_extra_data_character_ai(prompt_content_extra_data)

        # character_db['extra_data'] = extra_data["extra_data"]

        # if character_db['body_type'] in ["woman", "man", "MAN", "WOMAN"]:
            # customizes_db, count_customize = await get_customize_by_type_character_service(character_db['body_type'],
            #                                                                                "hair")

            # customize_character = get_customize_by_character(
            #     customizes_db, character_db['description']
            # )

            # character_db['extra_data']["type_combing"] = customize_character["reference_ui"]

        await db["character"].update_one({"_id": ObjectId(character_id)}, {"$set": character_db})

        return await db["character"].find_one({"_id": ObjectId(character_id)})
    except Exception as e:
        print(f"Error in get images character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error in get images character service",
        )


async def update_character_service(character_id: str, name: str, prompt_user: str, body_type: str):
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


async def add_character_to_location_service(character_id: str, location_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})

    if not character_db or not location_db:
        print(f"Character { '(yes)' if character_db else  '(no)'} or Location {'(yes)' if location_db else  '(no)'} not found")
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
