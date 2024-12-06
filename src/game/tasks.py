import asyncio
from uuid import uuid4

from bson import ObjectId

from pydantic import BaseModel
from pydantic import Field

from core.database import db

from gpt_ai.utils import openai_generator
from state_game.services import get_state_game_by_game_id

from task.services import update_task_service

from utils import upload_image
from voice.task import generate_voice_character


class SchemaResponseImage(BaseModel):
    response_vertical: str


async def generate_cover_image_game(_user_id: str, _game_id: str):
    try:
        print(f"Fetching game with ID: {_game_id}")
        game_db = await db['game'].find_one({'_id': ObjectId(_game_id)})
        print(f"Game data: {game_db}")

        if game_db['image']:
            print("Image already exists for the game.")
            return True

        first_location = None
        first_character = None

        print(f"Fetching state game for game ID: {_game_id}")
        state_game_db = await get_state_game_by_game_id(_game_id)
        print(f"State game data: {state_game_db}")

        if game_db.get('locations_id'):
            print(f"Fetching state for first location with ID: {game_db['locations_id'][0]}")
            first_location_state = await db['state_glic'].find_one({'element_id': game_db['locations_id'][0], 'state': state_game_db['_id'], 'type_element': 'location'})
            print(f"First location state data: {first_location_state}")

        if game_db.get('characters_id'):
            print(f"Fetching state for first character with ID: {game_db['characters_id'][0]}")
            first_character_state = await db['state_glic'].find_one({'element_id': game_db['characters_id'][0], 'state': state_game_db['_id'], 'type_element': 'character'})
            print(f"First character state data: {first_character_state}")

        if not first_location or not first_character:
            print("First location or first character not found.")
            return False

        prompt = (
            f"Generate a image in 3D animation style of extraordinary quality for the game "
            f"{game_db['title']} featuring the character {first_character_state['data']['prompt_user']}"
            f" in the location {first_location_state['data']['prompt_user']}. The scene should depict an "
            f"action-packed moment that captures the essence of the game. with content in vertical."
        )
        print(f"Generated prompt: {prompt}")

        response_image = await openai_generator.generate_image(
            prompt=prompt,
            quality="hd",
            size="1024x1792",
            user_id=_user_id,
            type_generation="generate image cover game",
        )
        print(f"Generated image URL: {response_image}")

        image = upload_image(
            url_image=response_image, file_name=f"covers/{uuid4()}.jpg", size=(512, 896)
        )
        print(f"Uploaded image URL: {image}")

        await db['game'].update_one({'_id': ObjectId(_game_id)}, {'$set': {'image': image}})
        print("Game image updated successfully.")
        return True

    except Exception as e:
        print(f"Error Cover Image: {str(e)}")
        return False


class SchemaResponseStory(BaseModel):
    story: str = Field(..., description="Story generated")


async def generate_context_init_game(_game_id: str, _user_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(_game_id)})
        if not game_db['locations_id']:
            return False
        first_location = await db['location'].find_one(
            {'_id': ObjectId(game_db['locations_id'][0])}
        )
        if not first_location:
            return False
        first_character = await db['character'].find_one(
            {'_id': ObjectId(game_db['characters_id'][0])}
        )
        if not first_character:
            return False
        response_story = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "You are a short initial story generator."
                },
                {
                    "role": "user",
                    "content": f"Generate the story init for the game, set in the location "
                               f"{first_location['title']}. The location is described as: {first_location['prompt_user']}. "
                               f"The main character is {first_character['name']}, described as: {first_character['prompt_user']}.",
                },
            ],
            max_tokens=1000,
            model="gpt-4o-mini",
            response_format=SchemaResponseStory,
            user_id=_user_id,
            type_generation="generate story init game",
        )
        await db['game'].update_one(
            {'_id': ObjectId(_game_id)}, {'$set': {'history': response_story.story}}
        )
        return True
    except Exception as e:
        print(f"Error generating story: {str(e)}")
        return False


# async def async_generate_context_new_location(game_id: str, user_id: str):
#     try:
#         game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
#         if not game_db:
#             return False
#         if not game_db['locations_id']:
#             return False
#         first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
#         if not first_location:
#             return False
#         response_story = await openai_generator.generate_gpt(
#             content_prompt=[
#                 {"role": "system",
#                  "content": "You are a creative story generator."},
#                 {"role": "user",
#                  "content": f"Continue the story for the game '{game_db['title']}' set in the new location "
#                             f"'{first_location['title']}'. The current story is: {game_db.get('history', '')}. "
#                             f"The location is described as: {first_location['prompt_user']}."
#                  }
#             ],
#             type_text="story location",
#             max_tokens=1000,
#             model="gpt-4o-mini",
#             response_format=SchemaResponseStory,
#             user_id=user_id,
#             type_generation="generate story location"
#         )
#         await db['location'].update_one({'_id': ObjectId(game_db['locations_id'][0])}, {'$set': {'history': response_story['story']}})
#
#         new_location_story = response_story['story']
#         response_story = await openai_generator.generate_gpt(
#             content_prompt=[
#                 {"role": "system",
#                  "content": "You are a creative story generator."},
#                 {"role": "user",
#                  "content": f"Continue the history for the game '{game_db['title']}' using the new location story: {new_location_story}. "
#                             f"The current game story is: {game_db.get('history', '')}. "
#                             f"Should be a maximum of 1000 words."
#                  }
#             ],
#             type_text="story continuation",
#             max_tokens=1000,
#             model="gpt-4o-mini",
#             response_format=SchemaResponseStory,
#             user_id=user_id,
#             type_generation="generate story continuation"
#         )
#         await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'history': response_story['story']}})
#
#         return True
#
#     except Exception as e:
#         print(f"Error generating story: {str(e)}")
#         return False


class SchemaResponseStoryNC(BaseModel):
    story: str
    summary: str


async def generate_context_new_character(
        game_id: str, character_id: str, location_id: str, user_id: str
):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        location_db = await db['location'].find_one({'_id': ObjectId(location_id)})
        character_db = await db['character'].find_one({'_id': ObjectId(character_id)})
        response_story = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "You are a creative story generator."
                },
                {
                    "role": "user",
                    "content": f"Continue the story for the game {game_db['title']} with the new character "
                               f"{character_db['name']} in the location {location_db['title']}. "
                               f"The current story is: {game_db.get('history', '')}. "
                               f"The character is described as: {character_db['prompt_user']}. "
                               f"The location is described as: {location_db['prompt_user']}."
                }
            ],
            max_tokens=4000,
            model="gpt-4o-2024-08-06",
            response_format=SchemaResponseStoryNC,
            user_id=user_id,
            type_generation="generate story continuation",
        )
        await db['game'].update_one(
            {'_id': ObjectId(game_id)}, {'$set': {'history': response_story.story}}
        )
        return True
    except Exception as e:
        print(f"Error generating story: {str(e)}")
        return False


class SchemaResponseSummary(BaseModel):
    summary: str = Field(..., description="Summary generated")


async def generate_game_summary(game_id: str, user_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        response_summary = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system", "content": "You are a summarizer."},
                {
                    "role": "user",
                    "content": f"Generate a summary for the following game history: {game_db['history']},"
                               f"should be a maximum of 200 words. "
                               f"Respond only with the text of the summary in JSON format: {{'summary': '<summary_text>'}}",
                },
            ],
            max_tokens=500,
            model="gpt-4o-mini",
            response_format=SchemaResponseSummary,
            user_id=user_id,
            type_generation="generate summary",
        )
        await db['game'].update_one(
            {'_id': ObjectId(game_id)}, {'$set': {'summary': response_summary.summary}}
        )
        return True
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return False


class SchemaResponseCategory(BaseModel):
    category_selected: str = Field(..., description="Category selected")


async def identify_category_game(game_id: str, user_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        categories_db = await db['category'].find().to_list(None)
        all_categories = [
            {
                "_id": str(category.get("_id")),
                "name": category.get("name"),
                "description": category.get("description"),
            }
            for category in categories_db
        ]
        prompt_category = (
            f"Based on the following RPG game history {game_db.get('history')}, classify it into one of the following "
            "game categories according to the meaning of each."
        )
        response_category = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f"You are a game category classifier, capable of detecting the category of a game based on its history. ",
                },
                {"role": "assistant", "content": f"categories :{all_categories}"},
                {"role": "user", "content": prompt_category},
            ],
            max_tokens=1000,
            model="gpt-4o-mini",
            response_format=SchemaResponseCategory,
            user_id=user_id,
            type_generation="generate category",
        )
        category_id = response_category.category_selected
        await db['game'].update_one(
            {'_id': ObjectId(game_id)}, {'$set': {'category_id': category_id}}
        )
        return True
    except Exception as e:
        print(f"Error generating category: {str(e)}")
        return False


async def async_generate_image_cover_game_task(_game_id: str, _user_id: str, _task_id: str):
    await update_task_service(_id=_task_id, _status="pending")
    game_db = await db['game'].find_one({'_id': ObjectId(_game_id)})
    if not game_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message=f"Error can't find the game with id {_game_id}.",
        )
        return f"Error can't find game with id {_game_id}"
    response_image = await generate_cover_image_game(_user_id, _game_id)
    if not response_image:
        await update_task_service(_id=_task_id, _status="failed", _message="Error generating image")
        return "Error generating image"
    # response_context = await generate_context_init_game(_game_id, _user_id)
    # if not response_context:
    #     await update_task_service(_id=_task_id, _status="failed", _message="Error generating story")
    #     return "Error generating story"
    await update_task_service(
        _id=_task_id, _status="completed", _message="Cover image and context generated successfully"
    )
    return "Cover image and context generated successfully"


async def async_generate_context_new_character_task(
        _game_id: str, _character_id: str, _location_id: str, _user_id: str, _task_id: str
):
    await update_task_service(_id=_task_id, _status="pending")

#     game_db = await db['game'].find_one({'_id': ObjectId(_game_id)})
#     while not game_db.get('history'):
#         await asyncio.sleep(10)
#         game_db = await db['game'].find_one({'_id': ObjectId(_game_id)})
#
#     game_db = await db['game'].find_one({'_id': ObjectId(_game_id)})
#     if not game_db['character_principal'] or not game_db['history']:
#         await update_task_service(
#             _id=_task_id,
#             _status="completed",
#             _message=f"Game {_game_id} doesn't have a principal character or history",
#         )
#         return f"Game {_game_id} doesn't have a principal character or history"
#
#     # response_story = await generate_context_new_character(
#     #     _game_id, _character_id, _location_id, _user_id
#     # )
#     # if not response_story:
#     #     await update_task_service(
#     #         _id=_task_id, _status="failed", _message="Error generating context"
#     #     )
#     #     return "Error generating context"
#     voice_generated = await generate_voice_character(_game_id, _character_id, _user_id)
#     if not voice_generated:
#         await update_task_service(
#             _id=_task_id, _status="failed", _message="Error voice not generated"
#         )
#         return "Error voice not generated"
#     await update_task_service(
#         _id=_task_id, _status="completed", _message="Story generated successfully"
#     )
#
    return "Story generated successfully"


async def async_generate_summary_game_task(_game_id: str, _user_id: str, _task_id: str):
    await update_task_service(_id=_task_id, _status="pending")
    response_summary = await generate_game_summary(_game_id, _user_id)
    if not response_summary:
        await update_task_service(
            _id=_task_id, _status="failed", _message="Error generating summary"
        )
        return "Error generating summary"

    await update_task_service(
        _id=_task_id, _status="completed", _message="Summary generated successfully"
    )
    return "Summary generated successfully"


async def async_identify_category_game_task(_game_id: str, _user_id: str, _task_id: str):
    await update_task_service(_id=_task_id, _status="pending")
    response_category = await identify_category_game(_game_id, _user_id)
    if not response_category:
        await update_task_service(
            _id=_task_id, _status="failed", _message="Error generating category"
        )
        return "Error generating category"
    response_summary = await generate_game_summary(_game_id, _user_id)
    if not response_summary:
        await update_task_service(
            _id=_task_id, _status="failed", _message="Error generating summary"
        )
        return "Error generating summary"
    await update_task_service(
        _id=_task_id, _status="completed", _message="Category generated successfully"
    )
    return "Category generated successfully"