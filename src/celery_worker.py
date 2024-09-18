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

from character.tasks import async_create_character_task, async_update_character_task

celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")


def image_is_vertical(image_url: str) -> bool:
    prompt = [
        {
            "role": "system",
            "content": "Eres un verificador de imagenes, que puede detectar si contenido de una imagen esta en vertical u horizontal."
                       "response con la palabra 'vertical' si el contenido es vertical o 'horizontal' si es horizontal.",
        },
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]

    response_identify = generate_gpt4o(content_prompt=prompt, max_tokens=4096, type_="text")

    if "vertical" in response_identify.lower() or "Vertical" in response_identify.lower():
        return True
    else:
        return False


async def async_create_cover_image_task(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            return False

        if game_db.get('image', None):
            return True
        first_location = None
        first_character = None
        if game_db.get('locations_id'):
            first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
        if game_db.get('characters_id'):
            first_character = await db['character'].find_one({'_id': ObjectId(game_db['characters_id'][0])})
        if not first_location or not first_character:
            return False

        # Generate the prompt for the cover image
        prompt = (f"Generate a image in 3D animation style of extraordinary quality for the game "
                  f"'{game_db['title']}' featuring the character {first_character['prompt_user']}'"
                  f" in the location '{first_location['prompt_user']}'. The scene should depict an "
                  f"action-packed moment that captures the essence of the game.")

        for attempt in range(3):
            try:
                image = generate_image_dalle(prompt=prompt, quality="hd", size="1024x1792")
                # Check if the image is vertical
                if image_is_vertical(image):
                    image = upload_image(url_image=image, file_name=f"covers/{uuid4()}.jpg", size=(512, 896))
                    await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'image': image}})
                    return True
                else:
                    prompt += ", el contenido en vertical"
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")

        return False

    except Exception as e:
        print(f"Error Cover Image: {str(e)}")
        return False


@celery.task(name="create_cover_image_task")
def create_cover_image_task(game_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_create_cover_image_task(game_id))


async def async_generate_context_init_game_task(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            print("game not found")
            return False

        # TODO: Revisar cuando este toda la implementacion comentada

        # if not game_db.get('history'):
        #     print("game history not found")
        #     return False

        # game_name = game_db.get('title')
        # if not game_name:
        #     print("game name not found")
        #     return False

        if not game_db.get('locations_id'):
            print("locations not found")
            return False

        first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
        if not first_location:
            print("location not found")
            return False

        location_description = first_location.get('prompt_user')
        if not location_description:
            print("location description not found")
            return False

        # generate the story for the game

        content_prompt = [
            {"role": "system", "content": "You are a creative story generator."},
            {"role": "user",
             "content": f"Generate the story init for the game, set in the location "
                        f"'{first_location['title']}'. The location is described as: {location_description}. "
                        f"Respond only with the text of the story in JSON format: {{'story': '<story_text>'}}"}
        ]
        story = generate_gpt4o(
            content_prompt=content_prompt,
            type_text="story init",
            max_tokens=1000,
            model="gpt-4o-mini"
        )

        story = json.loads(story)
        await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'history': story['story']}})

        return True

    except Exception as e:
        print(f"Error generating story: {str(e)}")
        return False


@celery.task(name="generate_context_init_game_task")
def generate_context_init_game_task(game_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_context_init_game_task(game_id))


async def async_generate_context_new_location(game_id: str, location_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            return False

        game_name = game_db.get('title')
        if not game_name:
            return False

        game_story = game_db.get('history', '')

        location_db = await db['location'].find_one({'_id': ObjectId(location_id)})
        if not location_db:
            return False

        location_description = location_db.get('prompt_user')
        if not location_description:
            return False

        # update history of the location - new location

        content_prompt = [
            {"role": "system", "content": "You are a creative story generator."},
            {"role": "user",
             "content": f"Continue the story for the game '{game_name}' set in the new location '{location_db['title']}'. "
                        f"The current story is: {game_story}. The location is described as: {location_description}."
                        f"Respond only with the text of the story in JSON format: {{'story': '<story_text>'}}"}
        ]
        story = generate_gpt4o(
            content_prompt=content_prompt,
            type_text="story location",
            max_tokens=1000,
            model="gpt-4o-mini"
        )

        story = json.loads(story)
        await db['location'].update_one({'_id': ObjectId(location_id)}, {'$set': {'history': story['story']}})

        location_db = await db['location'].find_one({'_id': ObjectId(location_id)})
        if not location_db:
            return False

        new_location_story = location_db.get('history')
        if not new_location_story:
            return False

        # update history of the game - new location

        content_prompt = [
            {"role": "system", "content": "You are a creative story generator,"},
            {"role": "user",
             "content": f"Continue the history for the game '{game_name}' using the new location story: {new_location_story}. "
                        f"The current game story is: {game_story}."
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

    except Exception as e:
        print(f"Error generating story: {str(e)}")
        return False


@celery.task(name="generate_context_new_location")
def generate_context_new_location(game_id: str, location_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_context_new_location(game_id, location_id))


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

@celery.task(name="create_character_task", queue="create_character_task", retry=True, max_retries=1)
def create_character_task(_character_id: str,
                          _body_type: list[str],
                          _user_id: str,
                          _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_create_character_task(_character_id=_character_id,
                                                               _body_type=_body_type,
                                                               _user_id=_user_id,
                                                               _task_id=_task_id))

@celery.task(name="update_character_task", queue="update_character_task", retry=True, max_retries=1)
def update_character_task(_character_id: str,
                          _body_type: list[str],
                          _user_id: str,
                          _task_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_update_character_task(_character_id=_character_id,
                                                               _body_type=_body_type,
                                                               _user_id=_user_id,
                                                               _task_id=_task_id))