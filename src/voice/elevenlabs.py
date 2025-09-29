from datetime import datetime
from uuid import uuid4

import pytz
import requests

from io import BytesIO
from pydub import AudioSegment

from config import settings
from core import db
from utils import upload_audio

XI_API_KEY = settings.ELEVENLABS_API_KEY


def get_voices() -> list:
    querystring = {"show_legacy": "true"}
    # querystring = {"language": "en", "page_size": "100", "page": "1"}
    url = "https://api.elevenlabs.io/v2/voices?page_size=100"
    headers = {
        "Accept": "application/json",
        "xi-api-key": XI_API_KEY,
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()
    return data['voices']


async def generate_audio(
    text: str,
    voice_id: str,
    model_id: str = "eleven_v3",
    stability: float = 0.5,
    similarity_boost: float = 0.8,
    style: float = 0.0,
    use_speaker_boost: bool = True,
    chunk_size: int = 1024,
    user_id: str = None,
):
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "application/json", "xi-api-key": XI_API_KEY}
    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost,
        },
    }
    response = requests.post(tts_url, headers=headers, json=data, stream=True)

    utc_now = datetime.now(pytz.utc)
    colombia_now = utc_now.astimezone(pytz.timezone("America/Bogota"))

    await db["logs"].insert_one(
        {
            "status": 200,
            "is_error": False,
            "message": "Response stored successfully",
            "response": str(response),
            "prompt": text,
            "model": "elevenlabs",
            "type_generation": "audio",
            "user_id": user_id,
            "created_at": colombia_now,
        }
    )

    if response.ok:
        # Guardamos el MP3 original en memoria
        audio_in_memory = BytesIO()
        for chunk in response.iter_content(chunk_size=chunk_size):
            audio_in_memory.write(chunk)
        audio_in_memory.seek(0)

        # Hacemos una copia del audio MP3 para tener dos versiones
        mp3_audio_in_memory = BytesIO()
        audio_in_memory.seek(0)
        mp3_audio_in_memory.write(audio_in_memory.read())
        mp3_audio_in_memory.seek(0)
        audio_in_memory.seek(0)

        # Convertimos a OGG para compatibilidad
        audio_segment = AudioSegment.from_file(audio_in_memory, format="mp3")
        ogg_audio_in_memory = BytesIO()
        audio_segment.export(ogg_audio_in_memory, format="ogg")
        ogg_audio_in_memory.seek(0)

        # Generamos un ID único para los archivos de audio
        audio_id = uuid4()

        # Subimos el archivo OGG
        url_audio_ogg = upload_audio(
            file_name=f"voice/{audio_id}.ogg", audio_byte_arr=ogg_audio_in_memory
        )

        # Subimos también el archivo MP3 original
        url_audio_mp3 = upload_audio(
            file_name=f"voice/{audio_id}.mp3", audio_byte_arr=mp3_audio_in_memory
        )

        # Devolvemos ambas URLs en un diccionario
        return {
            "ogg": url_audio_ogg,
            "mp3": url_audio_mp3
        }
    else:
        await db["logs"].insert_one(
            {
                "status": response.status_code,
                "is_error": True,
                "message": response.text,
                "response": str(response),
                "prompt": text,
                "model": "elevenlabs",
                "type_generation": "audio",
                "user_id": user_id,
                "created_at": colombia_now,
            }
        )
        return None
