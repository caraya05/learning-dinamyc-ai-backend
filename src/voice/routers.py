from fastapi import APIRouter
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth_admin
from auth.auth import auth
from auth.utils import auth_schema
from voice.elevenlabs import get_voices
from voice.services import add_voice_service
from voice.services import generate_voice_service

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
    if voice_generation := await generate_voice_service(character_id=character_id, user_id=user_db["_id"]):
        return "Voice generated successfully"
