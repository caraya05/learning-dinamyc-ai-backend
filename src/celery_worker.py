import asyncio
import os
from celery import Celery
from celery.signals import worker_ready, celeryd_after_setup, worker_init
from celery.schedules import crontab
from celery import shared_task
from datetime import timedelta
import redis
import nest_asyncio

# Permitir event loops anidados (necesario para Celery + async)
nest_asyncio.apply()

from event.tasks import async_generate_image_event
from character.tasks import async_generate_character_task, async_generate_image_character_task, \
    async_update_character_task
from location.tasks import async_generate_location_task, async_generate_image_location_task
from game.tasks import async_identify_category_game_task, async_generate_image_cover_game_task
from game.tasks_provisional import async_create_game_provisional_task, async_generate_scene_interactions_task
from game.tasks_provisional_2 import async_create_game_provisional_task_2, async_continue_create_game_provisional_2
from voice.elevenlabs import get_voices
from voice.services import add_voice_service
from voice.task import async_generate_voice_task
from object.task import async_generate_item, async_updated_item, async_generate_new_interaction_item


# Configuración de broker y backend con manejo de errores
def get_redis_url():
    """Obtiene la URL de Redis con fallback a valores por defecto"""
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://redisARM:6379/0")
    if "redis://" not in broker_url:
        broker_url = f"redis://{broker_url}"
    return broker_url

celery = Celery(__name__)

# Configuración base de Celery
broker_url = get_redis_url()
result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)

# Credenciales para Flower
flower_user = os.getenv("FLOWER_USER", "admin")
flower_password = os.getenv("FLOWER_PASSWORD", "admin")

celery.conf.update(
    # Conexión con broker
    broker_url=broker_url,
    result_backend=result_backend,
    broker_connection_retry=True,
    broker_connection_max_retries=None,
    broker_connection_timeout=10,

    # Configuración de worker
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Configuración de Flower
    flower_basic_auth=[f"{flower_user}:{flower_password}"],
    flower_port=5555,
    flower_address='0.0.0.0',

    # Timeouts y reintentos
    task_soft_time_limit=3600,
    task_time_limit=7200,

    # Persistencia y resultados
    result_expires=259200,
    worker_max_drift=60,

    # Configuración de eventos para Flower
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_track_started=True,
    task_track_received=True,
    worker_pool_restarts=True,

    # Configuración de zona horaria
    timezone='America/Bogota',
    enable_utc=True,

    # Configuración de serialización - ACTUALIZADO A JSON (Pickle deprecado)
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
)

# Configurar colas específicas
task_routes = {
    'generate_character_task': {'queue': 'character_queue'},
    'generate_location_task': {'queue': 'location_queue'},
    'generate_image_character_shared_task': {'queue': 'image_character_queue'},
    'generate_image_event_shared_task': {'queue': 'image_event_queue'},
    'generate_event_audio_shared_task': {'queue': 'default'},
    'detection_voice_character_task': {'queue': 'voice_detection_queue'},
    'generate_voice_character_task': {'queue': 'voice_queue'},
    'analyze_visual_style_task': {'queue': 'default'},
    'update_voice_list': {'queue': 'maintenance_queue'},  # Nueva cola para tareas de mantenimiento
    'monitor_and_update_game_tasks': {'queue': 'default'},  # Monitoreo de tareas
    '*': {'queue': 'default'},
}

# Configuración de tareas periódicas
beat_schedule = {
    'update-voice-list': {
        'task': 'celery_worker.update_voice_list',  # Nombre completo de la tarea
        'schedule': crontab(minute='15'),  # Se ejecuta a los 15 minutos de cada hora
        'options': {
            'queue': 'maintenance_queue'
        }
    }
}

celery.conf.update(
    task_routes=task_routes,
    beat_schedule=beat_schedule
)

@worker_init.connect
def init_worker(**kwargs):
    """Inicializa el worker y activa los eventos"""
    print("🚀 Iniciando worker de Celery...")
    celery.conf.update(worker_send_task_events=True)

# Señal para verificar que el worker inició correctamente
@worker_ready.connect
def worker_ready_handler(**kwargs):
    """Verifica la conexión con Redis cuando el worker está listo"""
    try:
        redis_client = redis.Redis.from_url(broker_url)
        redis_client.ping()
        print(f"✅ Celery worker conectado exitosamente a Redis en: {broker_url}")
        print(f"🔄 Colas configuradas: {list(task_routes.keys())}")
        print("📊 Eventos activados para monitoreo con Flower")
        print("⏰ Tareas periódicas configuradas:")
        for task_name in beat_schedule.keys():
            print(f"  - {task_name}")
    except redis.ConnectionError as e:
        print(f"❌ Error conectando a Redis: {str(e)}")
        print(f"🔍 URL de Redis: {broker_url}")

@celeryd_after_setup.connect
def setup_direct_queues(sender, instance, **kwargs):
    """Configura las colas después de iniciar el worker"""
    print(f"🚀 Worker {sender} iniciado y listo para procesar tareas")
    print(f"📩 Procesando colas: {instance.app.conf.task_queues}")
    print("🔌 Eventos de monitoreo activados")


@celery.task(name='celery_worker.update_voice_list')
def update_voice_list():
    """
    Tarea periódica que actualiza la lista de voces disponibles de ElevenLabs.
    Se ejecuta en los minutos 15 de cada hora.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _update_voices():
            try:
                voices_elevenlabs = get_voices()
                result = await add_voice_service(voices=voices_elevenlabs)
                print("✅ Lista de voces actualizada exitosamente")
                return f"Successfully updated voice list: {len(voices_elevenlabs)} voices synchronized"
            except Exception as e:
                print(f"❌ Error updating voice list: {str(e)}")
                return f"Error updating voice list: {str(e)}"
            finally:
                loop.close()

        return loop.run_until_complete(_update_voices())
    except Exception as e:
        print(f"❌ Error in voice update task: {str(e)}")
        return f"Error in voice update task: {str(e)}"


#TODO deprecated
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

#TODO deprecated
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

#TODO deprecated
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

#TODO deprecated
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

#TODO deprecated
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

#TODO deprecated
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

#TODO deprecated
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


#TODO deprecated
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

#TODO deprecated
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

#TODO deprecated
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

#TODO deprecated
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

#TODO deprecated
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

#TODO deprecated
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

@celery.task(name="create_game_provisional_task_2")
def create_game_provisional_task_2(id_game_provisional: str, user_id: str):
    """
    Celery task wrapper for async game creation.
    Handles event loop creation safely with nest_asyncio support.
    """
    try:
        # Intenta obtener el event loop actual
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        # Si no hay event loop o está cerrado, crear uno nuevo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(
            async_create_game_provisional_task_2(id_game_provisional, user_id)
        )
    except Exception as e:
        print(f"❌ Error in create_game_provisional_task_2: {e}")
        raise


@celery.task(name="continue_create_game_provisional_2")
def continue_create_game_provisional_2(id_game_provisional: str, user_id: str):
    """
    Celery task wrapper for continuing async game creation.
    Handles event loop creation safely with nest_asyncio support.
    """
    try:
        # Intenta obtener el event loop actual
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        # Si no hay event loop o está cerrado, crear uno nuevo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(
            async_continue_create_game_provisional_2(id_game_provisional, user_id)
        )
    except Exception as e:
        print(f"❌ Error in continue_create_game_provisional_2: {e}")
        raise

#TODO deprecated
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

# Register visual_style tasks (avoid circular imports)
from visual_style.tasks import register_visual_style_tasks
register_visual_style_tasks(celery)


