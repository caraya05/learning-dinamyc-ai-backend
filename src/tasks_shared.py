from celery import shared_task
import asyncio
from character.tasks import _generate_image_character, get_voice_for_character
from character.tasks import async_generate_character_task
from event.tasks import _generate_image_event, async_generate_image_event, async_generate_event_audio
from location.tasks import async_generate_location_task
from voice.task import async_generate_voice_task

import traceback
from location.services_video import compress_video, upload_video_to_gcs
from core.database import db
from uuid import uuid4
from bson import ObjectId
import datetime

@shared_task(name="generate_image_character_shared_task")
def generate_image_character_shared_task(_user_id, _prompt_user, _gender, _id_character, _game_provisional, _url_image_reference=None):
    """Tarea compartida para generar la imagen de un personaje"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        _generate_image_character(_user_id, _prompt_user, _gender, _id_character, _game_provisional, _url_image_reference)
    )


@shared_task(name="generate_character_task")
def generate_character_task(
        _character_id: str,
        _user_id: str,
        _task_id: str,
        _game_id: str,
        _location_id: str = None,
        _state_game_id: str = None,
        _is_image: bool = False,
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_character_task(
            _character_id=_character_id,
            _user_id=_user_id,
            _task_id=_task_id,
            _location_id=_location_id,
            _state_game_id=_state_game_id,
            _game_id=_game_id,
            _is_image=_is_image,
        )
    )


@shared_task(name="detection_voice_character_task")
def detection_voice_character_task(
        _prompt_user: str,
        _gender: str,
        _id_character: str,
        _game_provisional: str,
        _user_id: str,
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        get_voice_for_character(
            _prompt_user=_prompt_user,
            _gender=_gender,
            _id_character=_id_character,
            _game_provisional=_game_provisional,
            _user_id=_user_id,
        )
    )


@shared_task(name="generate_image_event_task")
def generate_image_event_task(
        game_id: str, event_id: str, state_game: str, user_id: str, prompt_user_image: str, task_id: str
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_image_event(
            _game_id=game_id,
            _event_id=event_id,
            _state_game=state_game,
            _user_id=user_id,
            _prompt_user_image=prompt_user_image,
            _task_id=task_id,
        )
    )



@shared_task(name="generate_location_task")
def generate_location_task(
        _location_id: str,
        _user_id: str,
        _task_id: str,
        _state_game_id: str
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_location_task(_location_id, _user_id, _task_id, _state_game_id)
    )


@shared_task(name="generate_image_event_shared_task")
def generate_image_event_shared_task(_user_id, _prompt_user_image, _id_event, _game_provisional, _is_init, _url_image_reference=None):
    """Tarea compartida para generar la imagen de un evento"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        _generate_image_event(_user_id, _prompt_user_image, _id_event, _game_provisional, _is_init, _url_image_reference)
    )


@shared_task(name="generate_voice_character_task")
def generate_voice_character_task(
        _game_id,
        _character_id: str,
        _user_id: str,
        _task_id: str,
        _location_id: str = None,
        _state_game_id: str = None,
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_voice_task(
            _game_id,
            _character_id,
            _user_id,
            _task_id,
            _state_game_id,
            _location_id,
        )
    )


@shared_task(name="generate_event_audio_shared_task")
def generate_event_audio_shared_task(event_id: str, user_id: str, text: str = None):
    """Tarea compartida para generar audio de eventos"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_event_audio(event_id=event_id, user_id=user_id, text=text)
    )


async def _async_process_interaction_video(
        location_id: str,
        state: str,
        dialog_number: int,
        video_bytes: bytes,
        quality: str,
):
    """Lógica async para procesar el video de interacción"""

    class VideoFile:
        def __init__(self, content, filename):
            self.content = content
            self.filename = filename
            self.content_type = 'video/mp4'

        async def read(self):
            return self.content

    video_file = VideoFile(video_bytes, f"interaction-{uuid4()}.mp4")

    print(f"   Compressing video (quality: {quality})...")
    compressed_video = await compress_video(video_file, quality=quality)  # type: ignore

    file_name = f"location-interactions/{location_id}/state-{state}/dialog-{dialog_number}-{uuid4()}.mp4"

    print(f"   Uploading to GCS: {file_name}...")
    video_url = await upload_video_to_gcs(compressed_video, file_name)

    print(f"   Updating database...")
    state_glic = await db["state_glic"].find_one({
        "element_id": location_id,
        "state": state
    })

    if not state_glic:
        return None

    state_glic["data"] = state_glic.get("data", {})
    state_glic["data"]["interaction_videos"] = {
        "url": video_url,
        "dialog_number": dialog_number,
        "compressed_quality": quality,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "file_name": file_name,
    }

    await db["state_glic"].find_one_and_update(
        {"_id": ObjectId(state_glic["_id"])},
        {"$set": {"data": state_glic["data"]}},
        return_document=True
    )

    return {
        "status": "success",
        "message": "Video processed successfully",
        "video_url": video_url,
        "state_glic_id": str(state_glic["_id"]),
        "dialog_number": dialog_number
    }


@shared_task(name="process_interaction_video_task")
def process_interaction_video_task(
        location_id: str,
        state: str,
        dialog_number: int,
        video_bytes: bytes,
        quality: str = "medium"
):
    """Procesa un video de interacción en background"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
            _async_process_interaction_video(
                location_id=location_id,
                state=state,
                dialog_number=dialog_number,
                video_bytes=video_bytes,
                quality=quality
            )
        )
