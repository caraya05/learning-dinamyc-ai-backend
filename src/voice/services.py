import json
from datetime import datetime
from random import random

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core import db
from gpt_ai.utils import generate_gpt4o
from utils import delete_image
from voice.elevenlabs import generate_audio


async def add_voice_service(voices: list):
    for voice in voices:
        try:
            await db["voice"].insert_one({
                "voice_id": voice["voice_id"],
                "name": voice["name"],
                "age": voice["labels"]["age"],
                "accent": voice["labels"]["accent"],
                "gender": voice["labels"]["gender"],
                "language": voice["fine_tuning"]["language"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
        except Exception as e:
            print(f"Error in add voice service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Error in add voice service",
            )
    return True


async def get_voices_service():
    try:
        voices = await db["voice"].find({}).to_list(None)
        return voices
    except Exception as e:
        print(f"Error in get voice service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error in get voice service",
        )


async def get_variants_service():
    try:
        variants = await get_voices_service()
        ages = []
        # accents = []
        genders = []
        for variant in variants:
            if variant["age"] not in ages:
                ages.append(variant["age"])
            # if variant["accent"] not in accents:
            #     accents.append(variant["accent"])
            if variant["gender"] not in genders:
                genders.append(variant["gender"])
        return {
            "ages": ages,
            # "accents": accents,
            "genders": genders
        }
    except Exception as e:
        print(f"Error in get variants service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error in get variants service",
        )


async def get_voice_by_criteria_service(criteria: dict):
    try:
        voice_by_gender = await db["voice"].find({"gender": criteria["gender"]}).to_list(None)

        if not voice_by_gender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No voice found matching the specified gender"
            )

        voice_by_age = [voice for voice in voice_by_gender if voice["age"] == criteria["age"]]

        if voice_by_age:
            voice = voice_by_age[0]
        else:
            voice = random.choice(voice_by_gender)
        return voice
    except Exception as e:
        print(f"Error in get voice by criteria service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error in get voice by criteria service",
        )


async def identify_voice_service(text_description: str, gender: str) -> dict:
    variants_voices = await get_variants_service()

    json_response = {
        "age": "edad de la voz segun la descripcion",
        "gender": "genero de la voz segun la descripcion"
    }

    content_prompt = [
        {
            "role": "system",
            "content": "Utilizando la siguiente descripción, identificar la voz que mejor se ajuste a la descripción. "
                       f"Respondiendo con la edad y género de la voz, con el siguiente formato JSON: {json_response}"
        },
        {
            "role": "assistant",
            "content": f"Variantes de voces a identificar: {variants_voices}"
        },
        {
            "role": "user",
            "content": f"Descripción del personaje: {text_description}"
                       f"Genero del personaje: {gender}"
        }
    ]

    response_generated = generate_gpt4o(
        content_prompt=content_prompt,
        type_text="Identify Voice",
        type_="json_object"
    )

    return json.loads(response_generated)


async def generate_voice_service(character: dict):
    try:
        criteria_voice = await identify_voice_service(text_description=character["description"],
                                                      gender=character["body_type"])

        voice = await get_voice_by_criteria_service(criteria=criteria_voice)

        if character["audio"]:
            delete_image(character["audio"])

        if not character.get("presentation"):
            text_generated = generate_gpt4o(content_prompt=[
                {"role": "user",
                 "content": f"Generate a first-person introduction in English about the life and story of the "
                            f"character described as: {character['description']}, named {character['name']}."
                            f" The introduction should be a maximum of 25 words."
                 },
            ],
                type_text="Generate Voice",
                type_="text")
        else:
            text_generated = character["presentation"]

        voice_url = generate_audio(text=text_generated,
                                   voice_id=voice["voice_id"])

        character["audio"] = voice_url
        character["presentation"] = text_generated

        character_update = await db["character"].update_one({"_id": ObjectId(character["_id"])},
                                                            {"$set": character})
        if character_update.modified_count:

            return character
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found"
            )
    except Exception as e:
        print(f"Error in generate voice service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error in generate voice service",
        )
