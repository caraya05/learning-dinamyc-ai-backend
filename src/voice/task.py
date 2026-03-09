import random

from bson import ObjectId
from pydantic import BaseModel, Field

from character.tasks import generate_voice_character
from core.database import db
from gpt_ai.utils import openai_generator
from task.services import update_task_service
from voice.elevenlabs import generate_audio
from voice.utils import get_variants_service


async def async_generate_voice_task(
    _game_id,
    _character_id: str,
    _user_id: str,
    _task_id: str,
    _state_game_id: str,
    _location_id: str,
    _type_conversation: str = None,
    _prompt_user_dialog: str = None,
    _options_dialog: list = None,
):

    await update_task_service(_id=_task_id, _status="pending")

    character_db = await db["character"].find_one({"_id": ObjectId(_character_id)})
    if not character_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message=f"Error can't find character with id {_character_id}",
        )
        return "Error can't find character"

    # Convertir character_id a string para búsqueda
    character_id_str = str(_character_id)

    # Búsqueda robusta de state_glic con fallbacks
    element_state_db = await db["state_glic"].find_one({
        "element_id": character_id_str,
        "type_element": "character",
        "state": _state_game_id
    })

    # Si no se encuentra, intentar buscar sin state
    if not element_state_db:
        print(f"[DEBUG] state_glic no encontrado para element_id={character_id_str}, state={_state_game_id}")
        element_state_db = await db["state_glic"].find_one({
            "element_id": character_id_str,
            "type_element": "character"
        })

    # Si aún no se encuentra, intentar sin type_element
    if not element_state_db:
        print(f"[DEBUG] state_glic no encontrado para element_id={character_id_str} con type_element")
        element_state_db = await db["state_glic"].find_one({
            "element_id": character_id_str,
            "state": _state_game_id
        })

    if not element_state_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message=f"Error can't find state_glic for character {_character_id}",
        )
        return f"Error can't find state_glic for character {_character_id}"

    if not _type_conversation:
        _type_conversation = element_state_db.get("data", {}).get("conversation_type")
    if not _prompt_user_dialog:
        _prompt_user_dialog = element_state_db.get("data", {}).get("prompt_user_dialog")
    if not _options_dialog:
        _options_dialog = element_state_db.get("data", {}).get("options_dialog")

    voice_generated = await generate_voice_character(
        game_id=_game_id,
        character_id=_character_id,
        user_id=_user_id,
        state_game=_state_game_id,
        location_id=_location_id,
        type_conversation=_type_conversation,
        prompt_user_dialog=_prompt_user_dialog,
        options_dialog=_options_dialog,
    )
    if not voice_generated:
        await update_task_service(
            _id=_task_id, _status="failed", _message="Error voice not generated"
        )
        return "Error voice not generated"
    await update_task_service(
        _id=_task_id, _status="completed", _message="Voice character generated"
    )
    return "Voice character generated"
