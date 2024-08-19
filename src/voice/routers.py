import time
from fastapi import HTTPException

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import status

from auth.auth import auth_admin, auth
from auth.utils import auth_schema
from character.services import get_character_service
from voice.elevenlabs import get_voices
from voice.services import add_voice_service, generate_voice_service

router = APIRouter(prefix='/voice', tags=['voice'])


@router.get("/add/")
async def add_voice(
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    voices_elevenlabs = get_voices()
    return await add_voice_service(voices=voices_elevenlabs)


@router.get("/generate-voice/{character_id}")
async def generate_voice(
        character_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    character_db = await get_character_service(character_id=character_id)
    # for _ in range(2):
    #     if "presentation" in character_db:
    #         break
    #     else:
    #         time.sleep(2)
    #         character_db = await get_character_service(character_id=character_id)

    # raise HTTPException(
    #     status_code=status.HTTP_400_BAD_REQUEST,
    #     detail="Error in generate voice service",
    # )
    if voice_generation := await generate_voice_service(character_db):
        time.sleep(2)
        return "Voice generated successfully"
