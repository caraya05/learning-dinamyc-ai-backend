import asyncio
import os

from celery import Celery

# Importamos la instancia Celery desde el nuevo módulo

from event.tasks import async_generate_image_event
from location.tasks import async_generate_location_task
from location.tasks import async_generate_image_location_task

from character.tasks import async_generate_character_task
from character.tasks import async_generate_image_character_task
from character.tasks import async_update_character_task

# Corregimos las importaciones para usar el archivo directamente, no el paquete
from game.tasks import async_identify_category_game_task
from game.tasks import async_generate_image_cover_game_task
from game.tasks import async_generate_context_new_character_task
# Importamos las funciones asíncronas del módulo tasks_provisional
from game.tasks_provisional import async_create_game_provisional_task, async_generate_scene_interactions_task
from voice.task import async_generate_voice_task
from object.task import async_generate_item, async_updated_item, async_generate_new_interaction_item


celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
celery.conf.update(worker_max_drift=60)  # Permitir hasta 60 segundos de desviación



# Desde aca va lo nuevo
@celery.task(name="generate_character_task")
def generate_character_task(
        _character_id: str,
        _user_id: str,
        _task_id: str,
        _game_id: str,
        _location_id: str = None,
        _state_game_id: str = None,
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
        )
    )


@celery.task(name="update_character_task")
def update_character_task(
        _character_id: str,
        _user_id: str,
        _task_id: str,
        _game_id: str,
        _updated_data: bool,
        _updated_voice: bool,
        _state_game_id: str = None,
        _location_id: str = None,
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_update_character_task(
            _character_id=_character_id,
            _user_id=_user_id,
            _task_id=_task_id,
            _game_id=_game_id,
            _updated_data=_updated_data,
            _updated_voice=_updated_voice,
            _state_game_id=_state_game_id,
            _location_id=_location_id,
        )
    )


@celery.task(name="generate_image_character_task")
def generate_image_character_task(_character_id: str, _user_id: str, _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_image_character_task(_character_id, _user_id, _task_id)
    )


@celery.task(name="generate_location_task")
def generate_location_task(
        _location_id: str, _user_id: str, _task_id: str, _state_game_id: str = None
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_location_task(_location_id, _user_id, _task_id, _state_game_id)
    )


@celery.task(name="generate_image_location_task")
def generate_image_location_task(_location_id: str, _user_id: str, _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_image_location_task(
            _location_id=_location_id, _user_id=_user_id, _task_id=_task_id
        )
    )


@celery.task(name="identify_category_game_task")
def identify_category_game_task(_game_id: str, _user_id: str, _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_identify_category_game_task(_game_id=_game_id, _user_id=_user_id, _task_id=_task_id)
    )


@celery.task(name="generate_image_cover_game_task")
def generate_image_cover_game_task(_game_id: str, _user_id: str, _task_id: str, _edit: bool = False):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_image_cover_game_task(_game_id, _user_id, _task_id, _edit)
    )



@celery.task(name="generate_voice_character_task")
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


@celery.task(name="generate_item_task")
def generate_item_task(
        _item_id: str,
        _user_id: str,
        _task_id: str,
        _location_id: str = None,
        _state_game_id: str = None,
        _game_id: str = None,
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_item(_item_id, _user_id, _task_id, _location_id, _state_game_id, _game_id)
    )


@celery.task(name="updated_item_task")
def updated_item_task(
        _item_id: str,
        _user_id: str,
        _task_id: str,
        _updated_prompt_user: bool,
        _updated_dialog: bool,
        _state_game_id: str = None,
        _location_id: str = None,
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_updated_item(
            _item_id,
            _user_id,
            _task_id,
            _updated_prompt_user,
            _updated_dialog,
            _state_game_id,
            _location_id,
        )
    )


@celery.task(name="generate_new_interaction_item_task")
def generate_new_interaction_item_task(
        _task_id: str,
        _item_id: str,
        _prompt_user_dialog,
        _state_game_id: str,
        location_id: str,
        _user_id: str,
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_new_interaction_item(
            _task_id, _item_id, _prompt_user_dialog, _state_game_id, location_id, _user_id
        )
    )


@celery.task(name="generate_image_event_task")
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


@celery.task(name="create_game_provisional_task")
def create_game_provisional_task(id_game_provisional: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(
        async_create_game_provisional_task(id_game_provisional)
    )


@celery.task(name="generate_scene_interactions_task")
def generate_scene_interactions_task(id_game_provisional: str):
    """
    Tarea Celery para generar las interacciones para cada escena del juego provisional.
    Procesa el guión, extrae el número de escenas y genera contenido específico para cada una.

    Args:
        id_game_provisional: ID del juego provisional

    Returns:
        Resultado de la operación
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        async_generate_scene_interactions_task(id_game_provisional)
    )
