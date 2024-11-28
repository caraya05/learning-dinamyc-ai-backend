import asyncio
import os


from celery import Celery


from location.tasks import async_generate_location_task
from location.tasks import async_generate_image_location_task


from character.tasks import async_generate_character_task
from character.tasks import async_generate_image_character_task
from character.tasks import async_update_character_task


from game.tasks import async_identify_category_game_task
from game.tasks import async_generate_image_cover_game_task
from game.tasks import async_generate_context_new_character_task
from voice.task import async_generate_voice_task
from object.task import async_generate_item, async_updated_item, async_generate_new_interaction_item


celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
celery.conf.update(
   worker_max_drift=60  # Permitir hasta 60 segundos de desviación
)




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
                           _task_id: str,
                           _game_id: str,
                           _location_id: str = None,
                           _state_game_id: str = None):
   try:
       loop = asyncio.get_event_loop()
   except RuntimeError:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)


   return loop.run_until_complete(
       async_generate_character_task(_character_id=_character_id,
                                     _user_id=_user_id,
                                     _task_id=_task_id,
                                     _location_id=_location_id,
                                     _state_game_id=_state_game_id,
                                     _game_id=_game_id)
   )




@celery.task(name="update_character_task")
def update_character_task(_character_id: str, _user_id: str, _task_id: str, _game_id: str, _updated_data: bool,
                         _updated_voice: bool, _state_game_id: str = None, _location_id: str = None):
   try:
       loop = asyncio.get_event_loop()
   except RuntimeError:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)


   return loop.run_until_complete(
       async_update_character_task(
           _character_id=_character_id, _user_id=_user_id, _task_id=_task_id, _game_id=_game_id,
           _updated_data=_updated_data, _updated_voice=_updated_voice, _state_game_id=_state_game_id,
           _location_id=_location_id
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
def generate_location_task(_location_id: str, _user_id: str, _task_id: str, _state_game_id: str = None):
   try:
       loop = asyncio.get_event_loop()
   except RuntimeError:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)


   return loop.run_until_complete(async_generate_location_task(_location_id, _user_id, _task_id, _state_game_id))




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
def generate_image_cover_game_task(_game_id: str, _user_id: str, _task_id: str):
   try:
       loop = asyncio.get_event_loop()
   except RuntimeError:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)


   return loop.run_until_complete(
       async_generate_image_cover_game_task(_game_id, _user_id, _task_id)
   )




# TODO: Revisar si se necesita
# @celery.task(name="generate_context_new_character_task")
# def generate_context_new_character_task(
#         _game_id: str, _user_id: str, _task_id: str, _character_id: str, _location_id: str
# ):
#     try:
#         loop = asyncio.get_event_loop()
#     except RuntimeError:
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#
#     return loop.run_until_complete(
#         async_generate_context_new_character_task(
#             _game_id, _character_id, _location_id, _user_id, _task_id
#         )
#     )


@celery.task(name="generate_voice_character_task")
def generate_voice_character_task(_game_id,
                                 _character_id: str,
                                 _user_id: str,
                                 _task_id: str,
                                 _location_id: str = None,
                                 _state_game_id: str = None,
                                 _type_conversation: str = None,
                                 _prompt_user_dialog: str = None,
                                 _options_dialog: list = None):
   try:
       loop = asyncio.get_event_loop()
   except RuntimeError:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)


   return loop.run_until_complete(
       async_generate_voice_task(_game_id, _character_id, _user_id, _task_id, _state_game_id, _location_id,
                                 _type_conversation, _prompt_user_dialog, _options_dialog))




@celery.task(name="generate_item_task")
def generate_item_task(_item_id: str, _user_id: str, _task_id: str, _location_id: str = None, _state_game_id: str = None,
                      _game_id: str = None):
   try:
       loop = asyncio.get_event_loop()
   except RuntimeError:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)


   return loop.run_until_complete(
       async_generate_item(_item_id, _user_id, _task_id, _location_id, _state_game_id, _game_id))




@celery.task(name="updated_item_task")
def updated_item_task(_item_id: str, _user_id: str, _task_id: str, _updated_prompt_user: bool, _updated_dialog: bool):
   try:
       loop = asyncio.get_event_loop()
   except RuntimeError:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)


   return loop.run_until_complete(
       async_updated_item(_item_id, _user_id, _task_id, _updated_prompt_user, _updated_dialog))




@celery.task(name="generate_new_interaction_item_task")
def generate_new_interaction_item_task(_task_id: str, _item_id: str, _prompt_user_dialog, _state_game_id: str,
                                      location_id: str,
                                      _user_id: str):
   try:
       loop = asyncio.get_event_loop()
   except RuntimeError:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)


   return loop.run_until_complete(
       async_generate_new_interaction_item(_task_id, _item_id, _prompt_user_dialog, _state_game_id, location_id,
                                           _user_id))


