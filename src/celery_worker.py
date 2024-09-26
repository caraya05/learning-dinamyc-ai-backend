import asyncio
import os

from celery import Celery

from location.tasks import async_generate_location_task
from location.tasks import async_generate_image_location_task

from character.tasks import async_generate_character_task
from character.tasks import async_generate_image_character_task

from game.tasks import async_identify_category_game_task
from game.tasks import async_generate_image_cover_game_task
from game.tasks import async_generate_context_new_character_task
from voice.task import async_generate_voice_task

celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")


# async def async_background_task(task_id: str):
#     try:
#         await asyncio.sleep(10)
#
#         await db["task"].update_one(
#             {"_id": ObjectId(task_id)},
#             {"$set": {"date_notification": datetime.utcnow()}}
#         )
#         await asyncio.sleep(2)
#         return True
#     except Exception as e:
#
#         await db["task"].update_one(
#             {"_id": ObjectId(task_id)},
#             {"$set": {"date_notification": datetime.utcnow()}}
#         )
#
#         print(f"Error in async_background_task: {str(e)}")
#         return False
#
#
# @celery.task(name="background_task")
# def background_task(task_id: str):
#     try:
#         loop = asyncio.get_event_loop()
#     except RuntimeError:
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#
#     return loop.run_until_complete(async_background_task(task_id))


# Desde aca va lo nuevo
@celery.task(name="generate_character_task")
def generate_character_task(_character_id: str,
                            _user_id: str,
                            _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_character_task(_character_id=_character_id,
                                                                 _user_id=_user_id,
                                                                 _task_id=_task_id))


@celery.task(name="generate_image_character_task")
def generate_image_character_task(_character_id: str,
                                  _user_id: str,
                                  _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_image_character_task(_character_id,
                                                                       _user_id,
                                                                       _task_id))


@celery.task(name="generate_location_task")
def generate_location_task(_location_id: str,
                           _user_id: str,
                           _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_location_task(_location_id,
                                                                _user_id,
                                                                _task_id))


@celery.task(name="generate_image_location_task")
def generate_image_location_task(_location_id: str,
                                 _user_id: str,
                                 _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_image_location_task(_location_id=_location_id,
                                                                      _user_id=_user_id,
                                                                      _task_id=_task_id))


@celery.task(name="identify_category_game_task")
def identify_category_game_task(_game_id: str,
                                _user_id: str,
                                _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_identify_category_game_task(_game_id=_game_id,
                                                                     _user_id=_user_id,
                                                                     _task_id=_task_id))


@celery.task(name="generate_image_cover_game_task")
def generate_image_cover_game_task(_game_id: str,
                                   _user_id: str,
                                   _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_image_cover_game_task(_game_id,
                                                                        _user_id,
                                                                        _task_id))


@celery.task(name="generate_context_new_character_task")
def generate_context_new_character_task(_game_id: str,
                                        _user_id: str,
                                        _task_id: str,
                                        _character_id: str,
                                        _location_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_context_new_character_task(_game_id,
                                                                             _user_id,
                                                                             _task_id,
                                                                             _character_id,
                                                                             _location_id))


@celery.task(name="generate_voice_character_task")
def generate_voice_character_task(_character_id: str,
                                  _user_id: str,
                                  _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_voice_task(_character_id,
                                                             _user_id,
                                                             _task_id))
