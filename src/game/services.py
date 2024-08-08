from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from uuid import uuid4
from category.services import get_categories_service
from character.services import get_characters_by_location_service

from game.schemas import SchemaCreateGame, SchemaUpdateGameV2
from game.schemas import SchemaPartialUpdateGame

from game.models import Game
from game.utils import get_history
from game.utils import get_category_game_ai
from game.utils import get_synopsis
from gpt_ai.utils import generate_image_dalle
from object.services import get_item_by_location_service
from gpt_ai.utils import generate_gpt4o

from utils import upload_image

from core.database import db


async def get_game_service(game_id: str):
    try:
        if game_db := await db['game'].find_one({'_id': ObjectId(game_id)}):

            if game_db.get('locations_id'):
                game_db['locations'] = await db['location'].find(
                    {'_id': {'$in': [ObjectId(location_id) for location_id in game_db['locations_id']]}}).to_list(None)
            else:
                game_db['locations'] = []

            if game_db.get('characters_id'):
                game_db['characters'] = await db['character'].find(
                    {'_id': {'$in': [ObjectId(character_id) for character_id in game_db['characters_id']]}}).to_list(
                    None)
            else:
                game_db['characters'] = []

            if game_db.get('items_id'):
                game_db['items'] = await db['item'].find(
                    {'_id': {'$in': [ObjectId(item_id) for item_id in game_db['items_id']]}}).to_list(None)
            else:
                game_db['items'] = []

            del game_db['locations_id']
            del game_db['characters_id']
            del game_db['items_id']

            return game_db
    except Exception as e:
        print(f"Error getting game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def get_games_service(*, skip: int = 1, limit: int = 100, user_id: str = None, games_id: list = None):
    if user_id:
        games_query = {'created_by': user_id}
    elif games_id:
        for i in range(len(games_id)):
            games_id[i] = ObjectId(games_id[i])
        games_query = {'_id': {'$in': games_id}}
    else:
        games_query = {}
    games_query['image'] = {'$ne': ""}
    games_db = await db['game'].find(games_query).sort("created_at", -1).skip((skip - 1) * limit).limit(limit).to_list(
        None)
    count_games = await db['game'].count_documents(games_query)
    return games_db, count_games


async def create_game_service(game: SchemaCreateGame, user_id: str):
    history = await get_history(story_line=game.story_line)
    synopsys = await get_synopsis(history=history)
    categories_db, count = await get_categories_service(skip=0, limit=100)
    category = await get_category_game_ai(history=synopsys['summary'], categories=categories_db)
    # characters_principals = get_characters_principals(db=db, history=history)

    try:
        game_db = Game(
            story_line=game.story_line,
            history=history,
            synopsis=synopsys['synopsis_generate'],
            title=synopsys['title'],
            prompt_image=synopsys['prompt_image'],
            summary=synopsys['summary'],
            updated_by=user_id,
            created_by=user_id,
            characters_id=[],
            locations_id=[],
            response_error="",
            image="",
            image_background="",
            attempts=3,
            category_id=category,
        )
        if game_created := await db['game'].insert_one(game_db.dict()):
            return await db['game'].find_one({'_id': game_created.inserted_id})
    except Exception as e:
        print(f"Error creating game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not created",
        )


async def update_partial_game_service(game_id: str, game_update: SchemaPartialUpdateGame, user_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        image = upload_image(
            url_image=game_update.image, file_name=f"covers/{uuid4()}.jpg", size=(512, 896)
        )

        game_db["image"] = image
        game_db["updated_by"] = user_id

        await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
        return await db['game'].find_one({'_id': ObjectId(game_id)})

    except Exception as e:
        print(f"Error updating partial game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="has reached the maximum number of generation attempts",
        )


async def subtract_attempts_game_service(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        if game_db["attempts"] > 0:
            game_db["attempts"] = game_db["attempts"] - 1
            game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})

            if game_updated.modified_count:
                return True

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attempts not subtracted",
        )

    except Exception as e:
        print(f"Error subtract attempts game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error in subtract attempts game service",
        )


async def delete_game_service(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        await db['game'].delete_one({'_id': ObjectId(game_id)})
        return True

    except Exception as e:
        print(f"Error deleting game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not deleted",
        )


async def update_image_background_game_service(game_id: str, image: str, identifier: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        game_db["image_background"] = upload_image(
            url_image=image,
            file_name=f"{game_id}/background/background-{identifier}.jpg",
            size=(996, 612),
        )

        game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})

        if game_updated.modified_count:
            return await db['game'].find_one({'_id': ObjectId(game_id)})

    except Exception as e:
        print(f"Error updating image background game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error updating image background game service",
        )


async def get_my_games_service(user_id: str, skip: int = 0, limit: int = 100):
    try:
        games_db = await db['game'].find({'created_by': user_id}).skip(skip).limit(limit).to_list(None)
        count_games = await db['game'].count_documents({'created_by': user_id})
        return games_db, count_games
    except Exception as e:
        print(f"Error getting my games service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Games not found",
        )


async def update_error_message_game_service(game_id: str, error_message: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db:
            if game_db.get('error_message'):
                game_db["error_message"] = f"{game_db.get('error_message')} - {error_message}"
            else:
                game_db["error_message"] = error_message
            game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
            if game_updated.modified_count:
                return await db['game'].find_one({'_id': ObjectId(game_id)})
    except Exception as e:
        print(f"Error updating error message game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def update_likes_game_service(game_id: str, user_id: str):
    try:
        game_db = await get_game_service(game_id=game_id)
        if game_db.get('likes', None):
            if user_id in game_db.get('likes'):
                game_db['likes'].remove(user_id)
            else:
                game_db['likes'].append(user_id)
        else:
            game_db['likes'] = [user_id]

        game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
        if game_updated.modified_count:
            return await db['game'].find_one({'_id': ObjectId(game_id)})
    except Exception as e:
        print(f"Error updating likes game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def create_game_v2_service(user_id: str):
    try:
        game_db = Game(
            updated_by=user_id,
            created_by=user_id,
            version=2,
        )
        if game_created := await db['game'].insert_one(game_db.dict()):
            return await db['game'].find_one({'_id': game_created.inserted_id})
    except Exception as e:
        print(f"Error creating game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not created",
        )


async def add_characters_game_service(game_id: str, characters_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db:
            if game_db.get('characters_id'):
                game_db["characters_id"].append(characters_id)
            else:
                game_db["characters_id"] = [characters_id]
            game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
            if game_updated.modified_count:
                return await db['game'].find_one({'_id': ObjectId(game_id)})
    except Exception as e:
        print(f"Error adding characters game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def add_locations_game_service(game_id: str, locations_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db:
            if game_db.get('locations_id'):
                game_db["locations_id"].append(locations_id)
            else:
                game_db["locations_id"] = [locations_id]
            game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
            if game_updated.modified_count:
                return await db['game'].find_one({'_id': ObjectId(game_id)})
    except Exception as e:
        print(f"Error adding locations game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def add_items_game_service(game_id: str, items_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db:
            if game_db.get('items_id'):
                game_db["items_id"].append(items_id)
            else:
                game_db["items_id"] = [items_id]
            game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
            if game_updated.modified_count:
                return await db['game'].find_one({'_id': ObjectId(game_id)})
    except Exception as e:
        print(f"Error adding items game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def change_character_principal_game_service(game_id: str, character_principal: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db:
            game_db["character_principal"] = character_principal
            game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
            return await db['game'].find_one({'_id': ObjectId(game_id)})
    except Exception as e:
        print(f"Error changing character principal game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def get_game_v2_service(game_id: str):
    try:
        if game_db := await db['game'].find_one({'_id': ObjectId(game_id)}):
            if game_db.get('characters_id'):
                game_db['characters'] = await db['character'].find(
                    {'_id': {'$in': [ObjectId(character_id) for character_id in game_db['characters_id']]}}).to_list(
                    None)
                for character in game_db['characters']:
                    character["_id"] = str(character["_id"])
            else:
                game_db['characters'] = []

            if game_db.get('items_id'):
                game_db['items'] = await db['item'].find(
                    {'_id': {'$in': [ObjectId(item_id) for item_id in game_db['items_id']]}}).to_list(None)
                for item in game_db['items']:
                    item["_id"] = str(item["_id"])
            else:
                game_db['items'] = []

            if game_db.get('locations_id'):
                game_db['locations'] = await db['location'].find(
                    {'_id': {'$in': [ObjectId(location_id) for location_id in game_db['locations_id']]}}).to_list(None)
                for location in game_db['locations']:
                    location["_id"] = str(location["_id"])
                    if location_characters := await get_characters_by_location_service(
                            location_id=str(location['_id'])):
                        location['characters'] = location_characters
                    if location_items := await get_item_by_location_service(location_id=str(location['_id'])):
                        location['items'] = location_items
            else:
                game_db['locations'] = []
            del game_db['locations_id']
            del game_db['characters_id']
            del game_db['items_id']
            return game_db
    except Exception as e:
        print(f"Error getting game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def update_game_v2_service(game_id: str, game_update: SchemaUpdateGameV2, user_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db:
            if game_update.title:
                game_db["title"] = game_update.title
            game_db["updated_by"] = user_id
            game_updated = await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
            if game_updated.modified_count:
                return await db['game'].find_one({'_id': ObjectId(game_id)})
    except Exception as e:
        print(f"Error updating game service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def get_my_games_v2_service(user_id: str, skip: int = 0, limit: int = 100):
    try:
        # print(f"Getting my games v2 service", user_id)
        # start_date = datetime(2024, 7, 23).replace(hour=0, minute=0, second=0, microsecond=0)
        games_db = await (db['game'].find({'created_by': user_id, 'version': 2})
                          .sort('created_at', -1)
                          .skip((skip - 1) * limit)
                          .limit(limit)
                          .to_list(None))

        count_games = await db['game'].count_documents({
            'created_by': user_id,
            'version': 2
        })
        return games_db, count_games
    except Exception as e:
        print(f"Error getting my games service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Games not found",
        )


async def get_characters_game_publish_service(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db and game_db.get('published'):
            if games_published_db := await db['published_game'].find_one({'_id': ObjectId(game_db['published'])}):
                return games_published_db['game']['characters']
    except Exception as e:
        print(f"Error getting character game publish service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def get_character_game_publish_service(game_id: str, character_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db and game_db.get('published'):
            if games_published_db := await db['published_game'].find_one({'_id': ObjectId(game_db['published'])}):
                for character in games_published_db['game']['characters']:
                    if character['_id'] == character_id:
                        return character
    except Exception as e:
        print(f"Error getting character game publish service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def get_locations_game_publish_service(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db and game_db.get('published'):
            if games_published_db := await db['published_game'].find_one({'_id': ObjectId(game_db['published'])}):
                return games_published_db['game']['locations']
    except Exception as e:
        print(f"Error getting locations game publish service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def get_location_game_publish_service(game_id: str, location_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db and game_db.get('published'):
            if games_published_db := await db['published_game'].find_one({'_id': ObjectId(game_db['published'])}):
                for location in games_published_db['game']['locations']:
                    if location['_id'] == location_id:
                        return location
    except Exception as e:
        print(f"Error getting location game publish service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )


async def generate_cover_image_game_v2_service(game_id: str):
    """
    This method will generate the cover image for the game using the characters and locations of the game.
    """
    # try:
    # Retrieve the game information
    game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
    if not game_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )
    if game_db['image']:
        return True
    # Get the first location and first character
    first_location = None
    first_character = None
    if game_db.get('locations_id'):
        first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
    if game_db.get('characters_id'):
        first_character = await db['character'].find_one({'_id': ObjectId(game_db['characters_id'][0])})
    if not first_location or not first_character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location or Character not found",
        )
    # Generate the prompt for the cover image
    prompt = (f"Generate a cover image in 3D animation style of extraordinary quality for the game "
              f"'{game_db['title']}' featuring the character {first_character['prompt_user']}'"
              f" in the location '{first_location['prompt_user']}'. The scene should depict an "
              f"action-packed moment that captures the essence of the game.")
    image = generate_image_dalle(prompt=prompt,
                                 quality="hd",
                                 size="1024x1792")

    image = upload_image(
        url_image=image,
        file_name=f"covers/{uuid4()}.jpg",
        size=(512, 896)
    )

    await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'image': image}})
    return True
    # except Exception as e:
    #     print(f"Error generating cover image prompt: {str(e)}")
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Error generating cover image prompt",
    #     )


async def generate_story_game_service(game_id: str):
    try:
        # Retrieve the game information
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        # Get the game's name and location description
        game_name = game_db.get('title')
        if not game_name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game title not found",
            )

        if not game_db.get('locations_id'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Locations not found",
            )

        first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
        if not first_location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="First location not found",
            )

        location_description = first_location.get('prompt_user')
        if not location_description:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location description not found",
            )

        # Generate the story using GPT-4o
        content_prompt = [
            {"role": "system", "content": "You are a creative story generator."},
            {"role": "user",
             "content": f"Generate the story init for the game '{game_name}' set in the location '{first_location['title']}'. The location is described as: {location_description}"}
        ]

        story = generate_gpt4o(
            content_prompt=content_prompt,
            type_text="story init",
            type_='text',
            max_tokens=1000,
            model="gpt-4o-mini"
        )

        return {"story": story}

    except Exception as e:
        print(f"Error generating story: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error generating story",
        )
