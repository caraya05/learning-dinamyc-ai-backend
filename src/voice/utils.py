from fastapi import HTTPException, status

from core.database import db


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
        genders = []
        accents = []
        descriptions = []
        for variant in variants:
            if variant["age"] not in ages:
                ages.append(variant["age"])
            if variant["gender"] not in genders:
                genders.append(variant["gender"])
            if variant["accent"] not in accents:
                accents.append(variant["accent"])
            if variant["description"] and variant["description"] not in descriptions:
                descriptions.append(variant["description"])
        return {"ages": ages, "genders": genders, "accents": accents, "descriptions": descriptions}
    except Exception as e:
        print(f"Error in get variants service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error in get variants service",
        )
