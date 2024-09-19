import asyncio
import json
import os
from datetime import datetime
from uuid import uuid4

from bson import ObjectId
from celery import Celery

from core import db
from gpt_ai.utils import openai_generator
from utils import upload_image

from location.tasks import async_generate_location_task
from location.tasks import async_generate_image_location_task

from character.tasks import async_generate_character_task
from character.tasks import async_generate_image_character_task

celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")


async def async_generate_context_new_character(game_id: str, character_id: str, location_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            print("game not found")
            return False
        game_name = game_db.get('title')
        if not game_name:
            print("game name not found")
            return False
        game_story = game_db.get('history', '')

        character_db = await db['character'].find_one({'_id': ObjectId(character_id)})
        if not character_db:
            print("character not found")
            return False
        character_description = character_db.get('prompt_user')
        if not character_description:
            print("character description not found")
            return False
        location_description = await db['location'].find_one({'_id': ObjectId(location_id)})
        if not location_description:
            print("location not found")
            return False

        location_history = location_description.get('history', '')

        if not location_history:
            location_history = location_description.get('prompt_user', '')

        location_db = await db['location'].find_one({'_id': ObjectId(location_id)})
        if not location_db:
            print("location not found")
            return False

        location_description = location_db.get('prompt_user')
        if not location_description:
            print("location description not found")
            return False

        content_prompt = [
            {"role": "system", "content": "You are a creative story generator,"},
            {"role": "user",
             "content": f"Continue the history for the game '{game_name}' "
                        f"The current game story is: {game_story}."
                        f"New character '{character_db['name']}' is introduced. The character is described as: {character_description}"
                        f"in the location '{location_db['title']}' that is described as {location_description}."
                        f"should be a maximum of 1000 words. "
                        f"Respond only with the text of the story in JSON format: {{'story': '<story_text>'}}"}
        ]
        new_story = generate_gpt4o(
            content_prompt=content_prompt,
            type_text="story continuation",
            max_tokens=1000,
            model="gpt-4o-mini"
        )

        new_story = json.loads(new_story)

        await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'history': new_story['story']}})

        return True

    except Exception as e:
        print(f"Error generating story: {str(e)}")
        return False


@celery.task(name="generate_context_new_character")
def generate_context_new_character(game_id: str, character_id: str, location_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(async_generate_context_new_character(game_id, character_id, location_id))


async def async_generate_game_summary(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            return False
        game_history = game_db.get('history')
        if not game_history:
            return False
        content_prompt = [
            {"role": "system", "content": "You are a summarizer."},
            {"role": "user",
             "content": f"Generate a summary for the following game history: {game_history},"
                        f"should be a maximum of 200 words. "
                        f"Respond only with the text of the summary in JSON format: {{'summary': '<summary_text>'}}"}
        ]
        summary = generate_gpt4o(
            content_prompt=content_prompt,
            type_text="summary",
            max_tokens=500,
            model="gpt-4o-mini"
        )

        summary = json.loads(summary)
        await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'summary': summary['summary']}})

        return True

    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return False


@celery.task(name="generate_game_summary_task")
def generate_game_summary_task(game_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_game_summary(game_id))


async def async_get_category_game_task(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        categories_db = await db['category'].find().to_list(None)
        all_categories = [
            {"_id": str(category.get("_id")), "name": category.get("name"), "description": category.get("description")}
            for category in categories_db
        ]
        prompt_category = (
            f"Based on the following RPG game history {game_db.get('history')}, classify it into one of the following "
            "game categories according to the meaning of each.")
        schema_category = {"category_selected": "string (name of the category selected)"}
        content_prompt = [
            {
                "role": "system",
                "content": f"You are a game category classifier, capable of detecting the category of a game based on its history. "
                           f"Respond with a JSON containing the schema '{schema_category}'",
            },
            {"role": "assistant", "content": f"categories :{all_categories}"},
            {"role": "user", "content": [{"type": "text", "text": prompt_category}]},
        ]
        category_generated = generate_gpt4o(content_prompt=content_prompt, type_text="category", max_tokens=1000,
                                            model="gpt-4o-mini")
        category_id = json.loads(category_generated)["category_selected"]
        await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'category_id': category_id}})
        return True
    except Exception as e:
        print(f"Error generating category: {str(e)}")
        return False


@celery.task(name="get_category_game_task")
def get_category_game_task(game_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_get_category_game_task(game_id))


async def async_background_task(task_id: str):
    try:
        await asyncio.sleep(10)

        await db["task"].update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {"date_notification": datetime.utcnow()}}
        )
        await asyncio.sleep(2)
        return True
    except Exception as e:

        await db["task"].update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {"date_notification": datetime.utcnow()}}
        )

        print(f"Error in async_background_task: {str(e)}")
        return False


@celery.task(name="background_task")
def background_task(task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_background_task(task_id))


# Desde aca va lo nuevo

@celery.task(name="generate_character_task", queue="generate_character_task")
def generate_character_task(_character_id: str,
                            _body_type: list[str],
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


@celery.task(name="generate_image_character_task", queue="generate_image_character_task")
def generate_image_character_task(_character_id: str,
                                  _user_id: str,
                                  _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_image_character_task(_character_id=_character_id,
                                                                       _user_id=_user_id,
                                                                       _task_id=_task_id))


@celery.task(name="generate_location_task", queue="generate_location_task")
def generate_location_task(_location_id: str,
                           _user_id: str,
                           _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_location_task(_location_id=_location_id,
                                                                _user_id=_user_id,
                                                                _task_id=_task_id))


@celery.task(name="generate_image_location_task", queue="generate_image_location_task")
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
