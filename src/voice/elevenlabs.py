from uuid import uuid4

import requests

from io import BytesIO
from pydub import AudioSegment

from config import settings
from utils import upload_audio

XI_API_KEY = settings.ELEVENLABS_API_KEY


def get_voices() -> list:
    querystring = {"show_legacy": "true"}
    # querystring = {"language": "en", "page_size": "100", "page": "1"}
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {
        "Accept": "application/json",
        "xi-api-key": XI_API_KEY,
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()
    return data['voices']


def generate_audio(
    text: str,
    voice_id: str,
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.8,
    style: float = 0.0,
    use_speaker_boost: bool = True,
    chunk_size: int = 1024,
):
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
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

    if response.ok:
        audio_in_memory = BytesIO()
        for chunk in response.iter_content(chunk_size=chunk_size):
            audio_in_memory.write(chunk)
        audio_in_memory.seek(0)

        audio_segment = AudioSegment.from_file(audio_in_memory, format="mp3")
        ogg_audio_in_memory = BytesIO()
        audio_segment.export(ogg_audio_in_memory, format="ogg")
        ogg_audio_in_memory.seek(0)

        url_audio = upload_audio(
            file_name=f"voice/{uuid4()}.ogg", audio_byte_arr=ogg_audio_in_memory
        )
        return url_audio
    else:
        print("error generate voice", response.text)
        return None
