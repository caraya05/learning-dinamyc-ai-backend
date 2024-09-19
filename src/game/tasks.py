from uuid import uuid4

from bson import ObjectId

from pydantic import BaseModel
from pydantic import Field

from core.database import db

from gpt_ai.utils import openai_generator

from task.services import update_task_service

from utils import upload_image


class SchemaResponseImage(BaseModel):
    response_vertical: bool = Field(..., description="Response of the content image is vertical or not")


async def generate_cover_image_game(_user_id: str,
                                    _game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(_game_id)})
        if game_db['image']:
            return True
        first_location = None
        first_character = None
        if game_db.get('locations_id'):
            first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
        if game_db.get('characters_id'):
            first_character = await db['character'].find_one({'_id': ObjectId(game_db['characters_id'][0])})
        if not first_location or not first_character:
            return False
        prompt = (f"Generate a image in 3D animation style of extraordinary quality for the game "
                  f"'{game_db['title']}' featuring the character {first_character['prompt_user']}'"
                  f" in the location '{first_location['prompt_user']}'. The scene should depict an "
                  f"action-packed moment that captures the essence of the game.")
        for attempt in range(3):
            response_image = await openai_generator.generate_image(
                prompt=prompt,
                quality="hd",
                size="1024x1792",
                user_id=_user_id,
                type_generation="generate image cover game"
            )
            response_identify = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": "Eres un verificador de imagenes, que puede detectar si contenido de una imagen esta en vertical u horizontal."
                                   "response con la palabra 'vertical' si el contenido es vertical o 'horizontal' si es horizontal.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": response_image}},
                        ],
                    }
                ],
                max_tokens=4096,
                model="gpt-4o-mini",
                response_format=SchemaResponseImage,
                user_id=_user_id,
                type_text="identify image"
            )

            if response_identify:
                image = upload_image(
                    url_image=response_image,
                    file_name=f"covers/{uuid4()}.jpg",
                    size=(512, 896)
                )
                await db['game'].update_one({'_id': ObjectId(_game_id)},
                                            {'$set': {'image': image}})
                return True
            else:
                prompt = (f"Generate a image in 3D animation style of extraordinary quality for the game "
                          f"'{game_db['title']}' featuring the character {first_character['prompt_user']}'"
                          f" in the location '{first_location['prompt_user']}'. The scene should depict an "
                          f"action-packed moment that captures the essence of the game, with content in vertical.")
        return True
    except Exception as e:
        print(f"Error Cover Image: {str(e)}")
        return False


class SchemaResponseStory(BaseModel):
    story: str = Field(..., description="Story generated")


async def async_generate_context_init_game_task(_game_id: str,
                                                _user_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(_game_id)})
        if not game_db:
            return False
        if not game_db['locations_id']:
            return False
        first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
        if not first_location:
            return False
        response_story = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system",
                 "content": "You are a creative story generator."},
                {"role": "user",
                 "content": f"Generate the story init for the game, set in the location "
                            f"'{first_location['title']}'. The location is described as: {first_location['prompt_user']}. "
                 }
            ],
            type_text="story init",
            max_tokens=1000,
            model="gpt-4o-mini",
            response_format=SchemaResponseStory,
            user_id=_user_id,
            type_generation="generate story init game"
        )
        await db['game'].update_one({'_id': ObjectId(_game_id)}, {'$set': {'history': response_story['story']}})

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