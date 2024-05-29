import json

from bson import ObjectId

from core.database import db
from gpt_ai.utils import generate_gpt4o
# from prompt.services import get_prompt_by_category_service

from characters_collection.schemas import SchemaCreateCharactersCollection

from character.services import create_character_by_collection_service


async def create_character_collection_service(prompt_user: str,
                                              name_character_collection: str,
                                              user_id: str):
    # prompt_create_collection = await get_prompt_by_category_service("create_collection")
    json_response = {
        "description_base": "basic description of the character in which describes the face, hair and aspects of the "
                            "body that serves to generate other characters.",
    }
    response_collection = generate_gpt4o(
        content_prompt=[
            # {
            #     "role": "system",
            #     "content": f"{prompt_create_collection.get('prompt_system')} "
            #                f"responde con un JSON que contenga el esquema '{json_response}'",
            # },
            {
                "role": "system",
                "content": "Genera una descripción base de un personaje, la descripción debe describir detalladamente "
                           "de desde la cabeza hasta los pies."
                           f"responde con un JSON que contenga el esquema '{json_response}'",
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt_user}]},
        ],
        type_text="collection",
        model="gpt-4o",
        max_tokens=4096
    )
    response = json.loads(response_collection)
    character_db = await create_character_by_collection_service(description_base=response.get("description_base"),
                                                                user_id=user_id,
                                                                name_character=name_character_collection,
                                                                prompt_user=prompt_user,
                                                                order=1)
    schema_collection = SchemaCreateCharactersCollection(name=name_character_collection,
                                                         characters_id=[str(character_db.get("_id"))],
                                                         description_base=response.get("description_base"),
                                                         created_by=user_id,
                                                         updated_by=user_id)
    collection_db = schema_collection.dict()
    collection_created = await db["characters_collection"].insert_one(collection_db)
    return await get_characters_collection_by_id_service(str(collection_created.inserted_id))


async def get_characters_collection_service(user_id: str):
    if collections := await db["characters_collection"].find({"created_by": user_id}).to_list(None):
        for collection in collections:
            collection["_id"] = str(collection.get("_id"))
        return collections
    return []


async def get_characters_collection_by_id_service(collection_id: str):
    if collection_db := await db["characters_collection"].find_one({"_id": ObjectId(collection_id)}):
        if collection_db.get("characters_id"):
            characters = await (db["character"]
                                .find({"_id": {"$in": [ObjectId(i) for i in collection_db.get("characters_id")]}})
                                .to_list(None))
            for character in characters:
                character["_id"] = str(character.get("_id"))
            collection_db["characters_id"] = characters
        return collection_db
    return None


async def update_characters_collection_service(collection_id: str, character_id: str):
    if collection_db := await db["characters_collection"].find_one({"_id": collection_id}):
        collection_db["characters_id"].append(character_id)
        await db["characters_collection"].update_one({"_id": collection_id}, {"$set": collection_db})
        return await get_characters_collection_by_id_service(collection_id)
    return None
