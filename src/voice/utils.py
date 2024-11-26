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
        for variant in variants:
            if variant["age"] not in ages:
                ages.append(variant["age"])
            if variant["gender"] not in genders:
                genders.append(variant["gender"])
        return {"ages": ages, "genders": genders}
    except Exception as e:
        print(f"Error in get variants service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error in get variants service",
        )
