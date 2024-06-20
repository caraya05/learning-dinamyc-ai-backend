import json

from bson import ObjectId

from core.database import db
from gpt_ai.utils import generate_gpt4o
# from prompt.services import get_prompt_by_category_service

from characters_collection.schemas import SchemaCreateCharactersCollection

from character.services import create_character_by_collection_service


async def create_character_collection_service(user_id: str):
    schema_collection = SchemaCreateCharactersCollection(created_by=user_id,
                                                         updated_by=user_id)
    collection_db = schema_collection.dict()
    collection_created = await db["characters_collection"].insert_one(collection_db)
    return await get_characters_collection_by_id_service(str(collection_created.inserted_id))


async def get_characters_collection_service(user_id: str):
    if collections := await db["characters_collection"].find({"created_by": user_id}).to_list(None):
        for collection in collections:
            collection["_id"] = str(collection.get("_id"))
            if collection.get("characters_id"):
                characters = await (db["character"]
                                    .find({"_id": {"$in": [ObjectId(i) for i in collection.get("characters_id")]}})
                                    .sort("order", 1)
                                    .to_list(None))
                if characters:
                    collection["name"] = characters[0]["name"]
                    collection["image"] = characters[0]["image"]
        return collections
    return []


async def get_characters_collection_by_id_service(collection_id: str):
    if collection_db := await db["characters_collection"].find_one({"_id": ObjectId(collection_id)}):
        if collection_db.get("characters_id"):
            characters = await (db["character"]
                                .find({"_id": {"$in": [ObjectId(i) for i in collection_db.get("characters_id")]}})
                                .sort("order", 1)
                                .to_list(None))
            for character in characters:
                character["_id"] = str(character.get("_id"))
            collection_db["characters_id"] = characters
        if collection_db.get("weapons_id"):
            weapons = await (db["weapon"]
                             .find({"_id": {"$in": [ObjectId(i) for i in collection_db.get("weapons_id")]}})
                             .to_list(None))
            for weapon in weapons:
                weapon["_id"] = str(weapon.get("_id"))
            collection_db["weapons_id"] = weapons
        if collection_db["characters_id"]:
            collection_db["name"] = collection_db["characters_id"][0]["name"]
            collection_db["image"] = collection_db["characters_id"][0]["image"]

        return collection_db
    return None


async def update_characters_collection_service(collection_id: str, character_id: str):
    if collection_db := await db["characters_collection"].find_one({"_id": collection_id}):
        collection_db["characters_id"].append(character_id)
        await db["characters_collection"].update_one({"_id": collection_id}, {"$set": collection_db})
        return await get_characters_collection_by_id_service(collection_id)
    return None


async def delete_characters_collection_service(collection_id: str):
    if collection_db := await db["characters_collection"].find_one({"_id": ObjectId(collection_id)}):
        if collection_db.get("characters_id"):
            for character_id in collection_db.get("characters_id"):
                await db["character"].delete_one({"_id": ObjectId(character_id)})
        if collection_db.get("weapons_id"):
            for weapon_id in collection_db.get("weapons_id"):
                await db["weapon"].delete_one({"_id": ObjectId(weapon_id)})
        await db["characters_collection"].delete_one({"_id": ObjectId(collection_id)})
        return True
    return False


async def add_character_to_collection_service(collection_id: str, character_id: str):
    if collection_db := await db["characters_collection"].find_one({"_id": ObjectId(collection_id)}):
        collection_db["characters_id"].append(character_id)
        await db["characters_collection"].update_one({"_id": ObjectId(collection_id)}, {"$set": collection_db})
        return await get_characters_collection_by_id_service(collection_id)
    return None


async def add_weapon_to_collection_service(collection_id: str, weapon_id: str):
    if collection_db := await db["characters_collection"].find_one({"_id": ObjectId(collection_id)}):
        collection_db["weapons_id"].append(weapon_id)
        await db["characters_collection"].update_one({"_id": ObjectId(collection_id)}, {"$set": collection_db})
        return await get_characters_collection_by_id_service(collection_id)
    return None


async def get_count_characters_collection_service(collection_id: str):
    if collection_db := await db["characters_collection"].find_one({"_id": ObjectId(collection_id)}):
        return len(collection_db.get("characters_id"))
    return 0


async def get_count_weapons_collection_service(collection_id: str):
    if collection_db := await db["characters_collection"].find_one({"_id": ObjectId(collection_id)}):
        return len(collection_db.get("weapons_id"))
    return 0
