import logging
import traceback
from datetime import datetime

import random
import string

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from uuid import uuid4

import game
from character.services import get_characters_by_location_service

from game.schemas import SchemaUpdateGameV2
from game.schemas import SchemaPartialUpdateGame

from game.models import Game
from game.tasks_provisional import generate_code_access_game_service
from game.utils import last_date_played_game_util, get_first_5_records_by_user

from object.services import get_item_by_location_service

from task.services import create_task_service
from task.services import update_task_service

from celery_worker import generate_image_cover_game_task

# from celery_worker import generate_context_new_character_task

from state_game.services import create_state_game
from state_glic.services import get_list_state_glic_by_element_id

from utils import upload_image

from core.database import db


class GameService:
    def __init__(self, db_instance=None):
        self.db = db_instance or db
        self.logger = logging.getLogger(__name__)

    async def get_game(self, game_id: str) -> dict | None:
        try:
            if game_db := await self.db['game'].find_one({'_id': ObjectId(game_id)}):

                try:
                    game_db['locations'] = await self.db['location'].find({'game_id': game_id}).to_list(None)
                    if game_db['locations']:
                        for location in game_db['locations']:
                            location['_id'] = str(location['_id'])
                except Exception as e:
                    self.logger.debug(f"No locations found: {e}")
                    game_db['locations'] = []

                try:
                    game_db['locations_states'] = await self.db['state_glic'].find(
                        {'data.game_id': game_id, 'type_element': 'location'}
                    ).to_list(None)
                    if game_db['locations_states']:
                        for state in game_db['locations_states']:
                            state['_id'] = str(state['_id'])
                except Exception as e:
                    self.logger.debug(f"No location states found: {e}")
                    game_db['locations_states'] = []

                try:
                    game_db['characters'] = await self.db['character'].find(
                        {'game_id': game_id}
                    ).to_list(None)
                    if game_db['characters']:
                        for character in game_db['characters']:
                            character['_id'] = str(character['_id'])
                except Exception as e:
                    self.logger.debug(f"No characters found: {e}")
                    game_db['characters'] = []

                try:
                    game_db['characters_states'] = await self.db['state_glic'].find(
                        {'data.game_id': game_id, 'type_element': 'character'}
                    ).to_list(None)
                    if game_db['characters_states']:
                        for state in game_db['characters_states']:
                            state['_id'] = str(state['_id'])
                except Exception as e:
                    self.logger.debug(f"No character states found: {e}")
                    game_db['characters_states'] = []

                try:
                    game_db['events'] = await self.db['event'].find({'game_id': game_id}).to_list(None)
                    if game_db['events']:
                        for event in game_db['events']:
                            event['_id'] = str(event['_id'])
                except Exception as e:
                    self.logger.debug(f"No events found: {e}")
                    game_db['events'] = []

                # Traer estados de juego generales (state_game)
                try:
                    game_db['state_games'] = await self.db['state_game'].find(
                        {'game_id': game_id}
                    ).to_list(None)
                    for state in game_db['state_games']:
                        state['_id'] = str(state['_id'])
                except Exception as e:
                    self.logger.debug(f"No game states found: {e}")
                    game_db['state_games'] = []

                try:
                    game_db["game_provisional"] = await self.db["game_provisional"].find_one({
                        "_id": ObjectId(game_db.get("provisional_id"))
                    })
                    if game_db["game_provisional"]:
                        game_db["game_provisional"]["_id"] = str(game_db["game_provisional"]["_id"])
                except Exception as e:
                    self.logger.debug(f"No provisional game found: {e}")
                    game_db['game_provisional'] = None

                del game_db['locations_id']
                del game_db['characters_id']
                # del game_db['items_id']

                return game_db
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving game {game_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving game",
            )

    async def get_game_service(self, game_id: str):
        try:
            if game_db := await db['game'].find_one({'_id': ObjectId(game_id)}):

                if game_db.get('locations_id'):
                    game_db['locations'] = (
                        await db['location']
                        .find(
                            {
                                '_id': {
                                    '$in': [
                                        ObjectId(location_id) for location_id in game_db['locations_id']
                                    ]
                                }
                            }
                        )
                        .to_list(None)
                    )
                else:
                    game_db['locations'] = []

                if game_db.get('characters_id'):
                    game_db['characters'] = (
                        await db['character']
                        .find(
                            {
                                '_id': {
                                    '$in': [
                                        ObjectId(character_id)
                                        for character_id in game_db['characters_id']
                                    ]
                                }
                            }
                        )
                        .to_list(None)
                    )
                else:
                    game_db['characters'] = []

                if game_db.get('items_id'):
                    game_db['items'] = (
                        await db['item']
                        .find({'_id': {'$in': [ObjectId(item_id) for item_id in game_db['items_id']]}})
                        .to_list(None)
                    )
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

    async def get_game_by_code_access_service(self, code_access: str):
        try:
            if game_db := await db['game'].find_one({'code_access': code_access}):

                if game_db.get('locations_id'):
                    game_db['locations'] = (
                        await db['location']
                        .find(
                            {
                                '_id': {
                                    '$in': [
                                        ObjectId(location_id) for location_id in game_db['locations_id']
                                    ]
                                }
                            }
                        )
                        .to_list(None)
                    )
                else:
                    game_db['locations'] = []

                if game_db.get('characters_id'):
                    game_db['characters'] = (
                        await db['character']
                        .find(
                            {
                                '_id': {
                                    '$in': [
                                        ObjectId(character_id)
                                        for character_id in game_db['characters_id']
                                    ]
                                }
                            }
                        )
                        .to_list(None)
                    )
                else:
                    game_db['characters'] = []

                if game_db.get('items_id'):
                    game_db['items'] = (
                        await db['item']
                        .find({'_id': {'$in': [ObjectId(item_id) for item_id in game_db['items_id']]}})
                        .to_list(None)
                    )
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

    async def get_games_service(
            self, skip: int = 1, limit: int = 100, user_id: str = None, games_id: list = None
    ):
        if user_id:
            games_query = {'created_by': user_id, 'version': 2}
        elif games_id:
            for i in range(len(games_id)):
                games_id[i] = ObjectId(games_id[i])
            games_query = {'_id': {'$in': games_id}, 'version': 2}
        else:
            games_query = {'version': 2}
        games_query['image'] = {'$ne': ""}
        games_db = (
            await db['game']
            .find(games_query)
            .sort("created_at", -1)
            .skip((skip - 1) * limit)
            .limit(limit)
            .to_list(None)
        )
        # for i in range(len(games_db)):
        #     if games_db[i]["image"]:
        #         if not games_db[i].get("image_minimalist", None):
        #             image_minimalist = upload_image(
        #                 url_image=games_db[i]["image"], file_name=f"covers/{uuid4()}_minimalist.jpg", size=(171, 299)
        #             )
        #             await db["game"].update_one(
        #                 {"_id": games_db[i]["_id"]}, {"$set": {"image_minimalist": image_minimalist}}
        #             )
        #             games_db[i]["image_minimalist"] = image_minimalist
        count_games = await db['game'].count_documents(games_query)
        return games_db, count_games

    async def update_partial_game_service(
            self, game_id: str, game_update: SchemaPartialUpdateGame, user_id: str
    ):
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

    async def delete_game_service(self, game_id: str):
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

    async def update_image_background_game_service(self, game_id: str, image: str, identifier: str):
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

    async def get_my_games_service(self, user_id: str, skip: int = 0, limit: int = 100):
        try:
            games_db = (
                await db['game'].find({'created_by': user_id}).skip(skip).limit(limit).to_list(None)
            )
            count_games = await db['game'].count_documents({'created_by': user_id})
            return games_db, count_games
        except Exception as e:
            print(f"Error getting my games service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Games not found",
            )

    async def update_error_message_game_service(self, game_id: str, error_message: str):
        try:
            game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db:
                if game_db.get('error_message'):
                    game_db["error_message"] = f"{game_db.get('error_message')} - {error_message}"
                else:
                    game_db["error_message"] = error_message
                game_updated = await db['game'].update_one(
                    {'_id': ObjectId(game_id)}, {'$set': game_db}
                )
                if game_updated.modified_count:
                    return await db['game'].find_one({'_id': ObjectId(game_id)})
        except Exception as e:
            print(f"Error updating error message game service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    async def update_likes_game_service(self, game_id: str, user_id: str):
        try:
            game_db = await self.get_game_service(game_id=game_id)
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

    async def generate_code_access_game_service(self):
        while True:
            code = ''.join(
                random.choices(string.ascii_lowercase, k=2) + random.choices(string.digits, k=2)
            )
            code = ''.join(random.sample(code, len(code)))  # Shuffle the characters

            existing_code = await db['game'].find_one({'code_access': code})

            if not existing_code:
                return code

    async def create_game_v2_service(self, user_id: str):
        try:
            game_db = Game(
                updated_by=user_id,
                created_by=user_id,
                version=2,
                code_access=await generate_code_access_game_service(),
            )
            if game_created := await db['game'].insert_one(game_db.dict()):
                # Crear el estado inicial del juego
                # TODO: Comentar cuando se tenga el servicio de tareas
                await create_state_game(
                    game_id=str(game_created.inserted_id), order=1, created_by=user_id
                )
                return await db['game'].find_one({'_id': game_created.inserted_id})
        except Exception as e:
            print(f"Error creating game service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Game not created",
            )

    async def add_characters_game_service(self, game_id: str, character_id: str):
        try:
            game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db:
                if game_db.get('characters_id'):
                    game_db["characters_id"].append(character_id)
                else:
                    game_db["characters_id"] = [character_id]
                game_updated = await db['game'].update_one(
                    {'_id': ObjectId(game_id)}, {'$set': game_db}
                )

                # await db['character'].update_one(
                #     {'_id': ObjectId(character_id)},
                #     {'$set': {'game_id': game_id}}
                # )

                # state_game = await get_state_game_by_game_id(game_id)
                #
                # if game_updated:
                #     task_db = await create_task_service(
                #         _task_id="",
                #         _user_id=user_id,
                #         _task_data={},
                #         _element_id=characters_id,
                #         _element_type="character",
                #         _process="generate_voice_character_game",
                #     )
                #     task_celery = generate_voice_character_task.delay(
                #         _task_id=str(task_db['_id']),
                #         _game_id=game_id,
                #         _character_id=characters_id,
                #         _location_id=location_id,
                #         _user_id=user_id,
                #         _state_game_id=state_game['_id'],
                #         _type_conversation=type_conversation,
                #         _prompt_user_dialog=prompt_user_dialog
                #     )
                #     await update_task_service(
                #         _id=str(task_db["_id"]),
                #         _task_id=task_celery.id,
                #     )
                # return await db['game'].find_one({'_id': ObjectId(game_id)})
                return True
        except Exception as e:
            print(f"Error adding characters game service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    async def add_locations_game_service(self, game_id: str, locations_id: str):
        try:
            game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db:
                if game_db.get('locations_id'):
                    game_db["locations_id"].append(locations_id)
                else:
                    game_db["locations_id"] = [locations_id]
                game_updated = await db['game'].update_one(
                    {'_id': ObjectId(game_id)}, {'$set': game_db}
                )

                return True
                # if game_updated.modified_count:
                #     return await db['game'].find_one({'_id': ObjectId(game_id)})
        except Exception as e:
            print(f"Error adding locations game service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    async def add_items_game_service(self, game_id: str, items_id: str):
        try:
            game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db:
                # Check and update items_id array
                if game_db.get('items_id'):
                    game_db['items_id'].append(items_id)
                else:
                    game_db['items_id'] = [items_id]

                await db['game'].update_one(
                    {'_id': ObjectId(game_id)}, {'$set': {'items_id': game_db['items_id']}}
                )

                # Check and update games_id array
                # item_db = await db['item'].find_one({'_id': ObjectId(items_id)})
                # if item_db.get('games_id'):
                #     item_db['games_id'].append(game_id)
                # else:
                #     item_db['games_id'] = [game_id]

                # await db['item'].update_one(
                #     {'_id': ObjectId(items_id)}, {'$set': {'games_id': item_db['games_id']}}
                # )
                return True
        except Exception as e:
            print(f"Error adding items game service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    async def change_character_principal_game_service(
            self, game_id: str, character_principal: str, user_id: str
    ):
        try:
            game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db:
                game_db["character_principal"] = character_principal
                await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})
                task_db = await create_task_service(
                    _task_id="",
                    _user_id=user_id,
                    _task_data={},
                    _element_id=game_id,
                    _element_type="game",
                    _process="generate_cover_image_context_game",
                )
                task_celery = generate_image_cover_game_task.delay(
                    _task_id=str(task_db['_id']),
                    _game_id=game_id,
                    _user_id=user_id,
                )
                await update_task_service(
                    _id=str(task_db["_id"]),
                    _task_id=task_celery.id,
                )
                game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
                game_db["task_id"] = str(task_db["_id"])
                return game_db
        except Exception as e:
            print(f"Error changing character principal game service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    async def get_game_v2_service(self, game_id: str):
        try:
            if game_db := await db['game'].find_one({'_id': ObjectId(game_id)}):
                game_db["_id"] = str(game_db["_id"])

                if game_db.get('characters_id'):
                    game_db['characters'] = (
                        await db['character']
                        .find(
                            {
                                '_id': {
                                    '$in': [
                                        ObjectId(character_id)
                                        for character_id in game_db['characters_id']
                                    ]
                                }
                            }
                        )
                        .to_list(None)
                    )
                    for character in game_db['characters']:
                        character["_id"] = str(character["_id"])
                        character["data"] = await db["state_glic"].find(
                            {"element_id": character["_id"], "type_element": "character"},
                            {"_id": 0}
                        ).to_list(None)
                else:
                    game_db['characters'] = []

                if game_db.get('items_id'):
                    game_db['items'] = (
                        await db['item']
                        .find({'_id': {'$in': [ObjectId(item_id) for item_id in game_db['items_id']]}})
                        .to_list(None)
                    )
                    for item in game_db['items']:
                        item["_id"] = str(item["_id"])
                        item["data"] = await db["state_glic"].find(
                            {"element_id": str(item["_id"]), "type_element": "item"},
                            {"_id": 0}
                        ).to_list(None)
                else:
                    game_db['items'] = []

                if game_db.get('locations_id'):
                    game_db['locations'] = (
                        await db['location']
                        .find(
                            {
                                '_id': {
                                    '$in': [
                                        ObjectId(location_id) for location_id in game_db['locations_id']
                                    ]
                                }
                            }
                        )
                        .to_list(None)
                    )
                    for location in game_db['locations']:
                        location["_id"] = str(location["_id"])
                        # if location_characters := await get_characters_by_location_service(location_id=str(location['_id'])):
                        #     location['characters'] = location_characters
                        # if location_items := await get_item_by_location_service(location_id=str(location['_id'])):
                        #     location['items'] = location_items
                        location["data"] = await db["state_glic"].find(
                            {"element_id": str(location["_id"]), "type_element": "location"},
                            {"_id": 0}
                        ).to_list(None)
                else:
                    game_db['locations'] = []

                if states_game := await db["state_game"].find({"game_id": game_id}).to_list(None):
                    for state in states_game:
                        state["_id"] = str(state["_id"])
                    game_db["state_game"] = states_game
                else:
                    game_db["state_game"] = []

                del game_db['locations_id']
                del game_db['characters_id']
                del game_db['items_id']
                return game_db
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Game not found",
                )
        except Exception as e:
            traceback.print_exc()
            print(f"Error getting game service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    async def update_game_v2_service(self, game_id: str, game_update: SchemaUpdateGameV2, user_id: str):
        try:
            game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db:
                if game_update.title:
                    game_db["title"] = game_update.title
                if game_update.event_end:
                    game_db["event_end"] = game_update.event_end
                if game_update.event_init:
                    game_db["event_init"] = game_update.event_init
                if game_update.description:
                    game_db["description"] = game_update.description
                if game_update.prompt_image:
                    if game_update.prompt_image != game_db.get('prompt_image'):
                        game_db["prompt_image"] = game_update.prompt_image
                        task_db = await create_task_service(
                            _task_id="",
                            _user_id=user_id,
                            _task_data={},
                            _element_id=game_id,
                            _element_type="game",
                            _process="generate_cover_image_game",
                        )
                        task_celery = generate_image_cover_game_task.delay(
                            _task_id=str(task_db['_id']),
                            _game_id=game_id,
                            _user_id=user_id,
                            _edit=True,
                        )
                        await update_task_service(
                            _id=str(task_db["_id"]),
                            _task_id=task_celery.id,
                        )
                        game_db["task_id"] = str(task_db["_id"])
                game_db["updated_by"] = user_id
                game_updated = await db['game'].update_one(
                    {'_id': ObjectId(game_id)}, {'$set': game_db}
                )
                if game_updated.modified_count:
                    return await db['game'].find_one({'_id': ObjectId(game_id)})
        except Exception as e:
            print(f"Error updating game service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    async def get_my_games_v2_service(self, user_id: str, skip: int = 0, limit: int = 100):
        try:
            # print(f"Getting my games v2 service", user_id)
            # start_date = datetime(2024, 7, 23).replace(hour=0, minute=0, second=0, microsecond=0)
            games_query = {'created_by': user_id, 'version': 2}
            games_db = await (
                db['game']
                .find(games_query)
                .sort('created_at', -1)
                .skip((skip - 1) * limit)
                .limit(limit)
                .to_list(None)
            )

            count_games = await db['game'].count_documents(games_query)

            games_to_review = await self.get_games_of_reviewer(user_id)
            if games_to_review:
                games_db_2 = await db['game'].find({'_id': {'$in': games_to_review}}).to_list(None)
                for game in games_db_2:
                    game['created_at'] = datetime.utcnow()
                games_db.extend(games_db_2)
                games_db = sorted(games_db, key=lambda x: x['created_at'], reverse=True)
                count_games += len(games_to_review)

            return games_db, count_games
        except Exception as e:
            print(f"Error getting my games service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Games not found",
            )

    async def get_community_games_service(self, skip: int = 1, limit: int = 100):
        """
        Obtiene juegos comunitarios que están publicados y tienen categorías específicas.

        Returns:
            tuple: (games_list, total_count)
        """
        # Categorías permitidas para juegos comunitarios
        community_categories = [
            "Marketing",
            "Talent Development",
            "Compliance",
            "Recruiting",
            "Events",
            "Fan Engagement",
            "Health & Wellness",
            "Data Collection",
            "Storytelling",
            "Social Impact",
            "Learning"
        ]

        # Query para buscar juegos publicados con las categorías especificadas
        games_query = {
            'version': 2,
            'published': {'$exists': True},  # Solo juegos publicados
            'is_published': True,
            'is_active': True,
            'category_id': {'$in': community_categories},  # Que tengan alguna de las categorías
        }

        games_db = (
            await db['game']
            .find(games_query)
            .sort("created_at", -1)
            .skip((skip - 1) * limit)
            .limit(limit)
            .to_list(None)
        )

        count_games = await db['game'].count_documents(games_query)
        return games_db, count_games

    async def get_games_played_recent_service(self, user_id: str):
        try:
            games_played = await get_first_5_records_by_user(user_id)
            if games_played:
                games_db = []
                for game in games_played:
                    if game.get('game_id'):
                        if game_ := await db['game'].find_one({'_id': ObjectId(game['game_id'])}):
                            games_db.append(game_)

                return games_db
        except Exception as e:
            traceback.print_exc()
            print(f"Error getting games played recent service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Games not found",
            )

    async def get_characters_game_publish_service(self, game_id: str):
        try:
            game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db and game_db.get('published'):
                if games_published_db := await db['published_game'].find_one(
                        {'_id': ObjectId(game_db['published'])}
                ):
                    return games_published_db['game']['characters']
        except Exception as e:
            print(f"Error getting character game publish service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    async def get_character_game_publish_service(self, game_id: str, character_id: str):
        try:
            game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db and game_db.get('published'):
                if games_published_db := await db['published_game'].find_one(
                        {'_id': ObjectId(game_db['published'])}
                ):
                    for character in games_published_db['game']['characters']:
                        if character['_id'] == character_id:
                            return character
        except Exception as e:
            print(f"Error getting character game publish service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    async def get_locations_game_publish_service(self, game_id: str):
        try:
            game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db and game_db.get('published'):
                if games_published_db := await db['published_game'].find_one(
                        {'_id': ObjectId(game_db['published'])}
                ):
                    return games_published_db['game']['locations']
        except Exception as e:
            print(f"Error getting locations game publish service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    async def get_location_game_publish_service(self, game_id: str, location_id: str):
        try:
            game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db and game_db.get('published'):
                if games_published_db := await db['published_game'].find_one(
                        {'_id': ObjectId(game_db['published'])}
                ):
                    for location in games_published_db['game']['locations']:
                        if location['_id'] == location_id:
                            return location
        except Exception as e:
            print(f"Error getting location game publish service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

    # async def generate_cover_image_game_v2_service(game_id: str):
    #     """
    #     This method will generate the cover image for the game using the characters and locations of the game.
    #     """
    #     # try:
    #     # Retrieve the game information
    #     game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
    #     if not game_db:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="Game not found",
    #         )
    #     if game_db['image']:
    #         return True
    #     # Get the first location and first character
    #     first_location = None
    #     first_character = None
    #     if game_db.get('locations_id'):
    #         first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
    #     if game_db.get('characters_id'):
    #         first_character = await db['character'].find_one({'_id': ObjectId(game_db['characters_id'][0])})
    #     if not first_location or not first_character:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="Location or Character not found",
    #         )
    #     # Generate the prompt for the cover image
    #     prompt = (f"Generate a cover image in 3D animation style of extraordinary quality for the game "
    #               f"'{game_db['title']}' featuring the character {first_character['prompt_user']}'"
    #               f" in the location '{first_location['prompt_user']}'. The scene should depict an "
    #               f"action-packed moment that captures the essence of the game.")
    #     image = generate_image_dalle(prompt=prompt,
    #                                  quality="hd",
    #                                  size="1024x1792")
    #
    #     image = upload_image(
    #         url_image=image,
    #         file_name=f"covers/{uuid4()}.jpg",
    #         size=(512, 896)
    #     )
    #
    #     await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'image': image}})
    #     return True
    #     # except Exception as e:
    #     #     print(f"Error generating cover image prompt: {str(e)}")
    #     #     raise HTTPException(
    #     #         status_code=status.HTTP_400_BAD_REQUEST,
    #     #         detail="Error generating cover image prompt",
    #     #     )
    #
    #
    # async def generate_story_game_service(game_id: str):
    #     try:
    #         # Retrieve the game information
    #         game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
    #         if not game_db:
    #             raise HTTPException(
    #                 status_code=status.HTTP_404_NOT_FOUND,
    #                 detail="Game not found",
    #             )
    #
    #         # Get the game's name and location description
    #         game_name = game_db.get('title')
    #         if not game_name:
    #             raise HTTPException(
    #                 status_code=status.HTTP_404_NOT_FOUND,
    #                 detail="Game title not found",
    #             )
    #
    #         if not game_db.get('locations_id'):
    #             raise HTTPException(
    #                 status_code=status.HTTP_404_NOT_FOUND,
    #                 detail="Locations not found",
    #             )
    #
    #         first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
    #         if not first_location:
    #             raise HTTPException(
    #                 status_code=status.HTTP_404_NOT_FOUND,
    #                 detail="First location not found",
    #             )
    #
    #         location_description = first_location.get('prompt_user')
    #         if not location_description:
    #             raise HTTPException(
    #                 status_code=status.HTTP_404_NOT_FOUND,
    #                 detail="Location description not found",
    #             )
    #
    #         # Generate the story using GPT-4o
    #         content_prompt = [
    #             {"role": "system", "content": "You are a creative story generator."},
    #             {"role": "user",
    #              "content": f"Generate the story init for the game '{game_name}' set in the location '{first_location['title']}'. The location is described as: {location_description}"}
    #         ]
    #
    #         story = generate_gpt4o(
    #             content_prompt=content_prompt,
    #             type_text="story init",
    #             type_='text',
    #             max_tokens=1000,
    #             model="gpt-4o-mini"
    #         )
    #
    #         return {"story": story}
    #
    #     except Exception as e:
    #         print(f"Error generating story: {str(e)}")
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="Error generating story",
    #         )

    async def get_games_of_reviewer(self, user_id: str):
        try:
            print(f"Getting games of reviewer: {user_id}")
            if (
                    games_pending_db := await db['published_game']
                            .find({'reviewer': user_id, 'status': 1})
                            .to_list(None)
            ):
                print(f"Games pending: {games_pending_db}")
                return [ObjectId(game['game_id']) for game in games_pending_db]
            else:
                return []
        except Exception as e:
            print(f"Error getting games of reviewer: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Games not found",
            )

    async def clone_game_service(self, game_id: str, user_id: str):
        """
        Clona un juego completo con todos sus elementos asociados (characters, locations, items)
        creando nuevos IDs para cada elemento y actualizando las referencias correspondientes.

        Este método también clona:
        - Estados del juego (state_game)
        - Estados GLIC asociados (state_glic)
        - Datos de configuración adicionales
        - Referencias cruzadas entre elementos

        Orden de clonado:
        1. Game
        2. State_game
        3. Locations
        4. Characters
        5. Items
        """
        try:
            # Obtener el juego original
            original_game = await db['game'].find_one({'_id': ObjectId(game_id)})
            if not original_game:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Game not found",
                )

            # Mapas para almacenar la correspondencia entre IDs originales y nuevos
            all_id_mappings = {}  # Mapa global con todos los IDs (game, states, locations, characters, items, events)
            location_id_map = {}
            character_id_map = {}
            item_id_map = {}
            state_game_id_map = {}
            event_id_map = {}

            # 1. CLONAR EL GAME PRIMERO
            new_game = original_game.copy()
            del new_game['_id']

            # Actualizar información del nuevo juego
            new_game['title'] = f"{original_game.get('title', 'Game')} (Copy)"
            new_game['created_by'] = user_id
            new_game['updated_by'] = user_id
            new_game['created_at'] = datetime.utcnow()
            new_game['updated_at'] = datetime.utcnow()
            new_game['code_access'] = await generate_code_access_game_service()

            # Limpiar campos de publicación y tareas
            new_game.pop('published', None)
            new_game.pop('published_version', None)
            new_game.pop('is_published', None)
            new_game.pop('published_at', None)
            new_game['tasks_request'] = []
            new_game['tasks_notified'] = []
            new_game['status'] = 0

            # Limpiar likes (el nuevo juego empieza sin likes)
            new_game['likes'] = []

            # Limpiar ID provisional si existe
            new_game.pop('provisional_id', None)

            # Limpiar campos de error si existen
            new_game.pop('error_message', None)

            # Preservar campos importantes del juego original pero limpiar referencias
            # Los campos como synopsis, description, summary, event_init, event_end,
            # prompt_image, category_id, history se mantienen del juego original

            # Inicializar arrays vacíos para elementos (se actualizarán después)
            new_game['locations_id'] = []
            new_game['characters_id'] = []
            new_game['items_id'] = []
            new_game['character_principal'] = None

            # Insertar el nuevo juego
            game_result = await db['game'].insert_one(new_game)
            new_game_id = str(game_result.inserted_id)

            # Agregar mapeo del game ID
            all_id_mappings[game_id] = new_game_id

            # 2. CLONAR ESTADOS DEL JUEGO (state_game)
            original_game_states = await db['state_game'].find({'game_id': game_id}).to_list(None)
            cloned_states_count = 0

            if original_game_states:
                for state in original_game_states:
                    old_state_id = str(state['_id'])
                    new_state = state.copy()
                    del new_state['_id']
                    new_state['game_id'] = new_game_id
                    new_state['created_by'] = user_id
                    new_state['updated_by'] = user_id
                    new_state['created_at'] = datetime.utcnow()
                    new_state['updated_at'] = datetime.utcnow()

                    # Asegurar que todos los campos requeridos estén presentes
                    if 'order' not in new_state:
                        new_state['order'] = 1

                    result = await db['state_game'].insert_one(new_state)
                    new_state_id = str(result.inserted_id)

                    # Guardar mapeo de IDs de estados
                    state_game_id_map[old_state_id] = new_state_id
                    all_id_mappings[old_state_id] = new_state_id

                    cloned_states_count += 1

                print(f"Clonados {cloned_states_count} estados de juego para el nuevo juego {new_game_id}")
            else:
                # Si no hay estados originales, crear estado inicial del juego
                await create_state_game(
                    game_id=new_game_id, order=1, created_by=user_id
                )
                cloned_states_count = 1
                print(f"Creado estado inicial para el nuevo juego {new_game_id}")

            # 3. CLONAR LOCATIONS con sus estados GLIC
            new_locations_id = []
            if original_game.get('locations_id'):
                for location_id in original_game['locations_id']:
                    original_location = await db['location'].find_one({'_id': ObjectId(location_id)})
                    if original_location:
                        # Crear nueva location
                        new_location = original_location.copy()
                        del new_location['_id']
                        new_location['game_id'] = new_game_id
                        new_location['created_by'] = user_id
                        new_location['updated_by'] = user_id
                        new_location['created_at'] = datetime.utcnow()
                        new_location['updated_at'] = datetime.utcnow()

                        # Limpiar tareas
                        new_location['tasks_request'] = []
                        new_location['tasks_notified'] = []
                        new_location['status'] = 0

                        result = await db['location'].insert_one(new_location)
                        new_location_id = str(result.inserted_id)
                        new_locations_id.append(new_location_id)

                        # Guardar mapeo de IDs de locations
                        location_id_map[location_id] = new_location_id
                        all_id_mappings[location_id] = new_location_id

                        # Clonar estados GLIC de la location
                        original_states = await db['state_glic'].find({
                            'element_id': location_id,
                            'type_element': 'location'
                        }).to_list(None)

                        for state in original_states:
                            old_glic_id = str(state['_id'])
                            new_state = state.copy()
                            del new_state['_id']
                            new_state['element_id'] = new_location_id
                            new_state['created_by'] = user_id
                            new_state['updated_by'] = user_id
                            new_state['created_at'] = datetime.utcnow()
                            new_state['updated_at'] = datetime.utcnow()

                            glic_result = await db['state_glic'].insert_one(new_state)
                            new_glic_id = str(glic_result.inserted_id)
                            all_id_mappings[old_glic_id] = new_glic_id

            # 4. CLONAR CHARACTERS con sus estados GLIC (actualizando locations_id si es necesario)
            new_characters_id = []
            if original_game.get('characters_id'):
                for character_id in original_game['characters_id']:
                    original_character = await db['character'].find_one({'_id': ObjectId(character_id)})
                    if original_character:
                        # Crear nuevo character
                        new_character = original_character.copy()
                        del new_character['_id']
                        new_character['game_id'] = new_game_id
                        new_character['created_by'] = user_id
                        new_character['updated_by'] = user_id
                        new_character['created_at'] = datetime.utcnow()
                        new_character['updated_at'] = datetime.utcnow()

                        # Limpiar tareas
                        new_character['tasks_request'] = []
                        new_character['tasks_notified'] = []
                        new_character['status'] = 0

                        # Actualizar locations_id si existe y está en el mapa
                        if new_character.get('locations_id') and new_character['locations_id'] in location_id_map:
                            new_character['locations_id'] = location_id_map[new_character['locations_id']]

                        result = await db['character'].insert_one(new_character)
                        new_character_id = str(result.inserted_id)
                        new_characters_id.append(new_character_id)

                        # Guardar mapeo de IDs de characters
                        character_id_map[character_id] = new_character_id
                        all_id_mappings[character_id] = new_character_id

                        # Clonar estados GLIC del character
                        original_states = await db['state_glic'].find({
                            'element_id': character_id,
                            'type_element': 'character'
                        }).to_list(None)

                        for state in original_states:
                            old_glic_id = str(state['_id'])
                            new_state = state.copy()
                            del new_state['_id']
                            new_state['element_id'] = new_character_id
                            new_state['created_by'] = user_id
                            new_state['updated_by'] = user_id
                            new_state['created_at'] = datetime.utcnow()
                            new_state['updated_at'] = datetime.utcnow()

                            glic_result = await db['state_glic'].insert_one(new_state)
                            new_glic_id = str(glic_result.inserted_id)
                            all_id_mappings[old_glic_id] = new_glic_id

            # 5. CLONAR ITEMS/OBJECTS con sus estados GLIC (actualizando location_id si es necesario)
            new_items_id = []
            if original_game.get('items_id'):
                for item_id in original_game['items_id']:
                    original_item = await db['item'].find_one({'_id': ObjectId(item_id)})
                    if original_item:
                        # Crear nuevo item
                        new_item = original_item.copy()
                        del new_item['_id']
                        new_item['game_id'] = new_game_id
                        new_item['created_by'] = user_id
                        new_item['updated_by'] = user_id
                        new_item['created_at'] = datetime.utcnow()
                        new_item['updated_at'] = datetime.utcnow()

                        # Limpiar tareas
                        new_item['tasks_request'] = 0
                        new_item['tasks_notified'] = []
                        new_item['status'] = 0

                        # Actualizar location_id si existe y está en el mapa
                        if new_item.get('location_id') and new_item['location_id'] in location_id_map:
                            new_item['location_id'] = location_id_map[new_item['location_id']]

                        result = await db['item'].insert_one(new_item)
                        new_item_id = str(result.inserted_id)
                        new_items_id.append(new_item_id)

                        # Guardar mapeo de IDs de items
                        item_id_map[item_id] = new_item_id
                        all_id_mappings[item_id] = new_item_id

                        # Clonar estados GLIC del item
                        original_states = await db['state_glic'].find({
                            'element_id': item_id,
                            'type_element': 'item'
                        }).to_list(None)

                        for state in original_states:
                            old_glic_id = str(state['_id'])
                            new_state = state.copy()
                            del new_state['_id']
                            new_state['element_id'] = new_item_id
                            new_state['created_by'] = user_id
                            new_state['updated_by'] = user_id
                            new_state['created_at'] = datetime.utcnow()
                            new_state['updated_at'] = datetime.utcnow()

                            glic_result = await db['state_glic'].insert_one(new_state)
                            new_glic_id = str(glic_result.inserted_id)
                            all_id_mappings[old_glic_id] = new_glic_id

            # 5.5. CLONAR EVENTOS asociados al juego
            new_events_id = []
            original_events = await db['event'].find({'game_id': game_id}).to_list(None)
            cloned_events_count = 0

            if original_events:
                for event in original_events:
                    old_event_id = str(event['_id'])
                    new_event = event.copy()
                    del new_event['_id']
                    new_event['game_id'] = new_game_id
                    new_event['created_by'] = user_id
                    new_event['updated_by'] = user_id
                    new_event['created_at'] = datetime.utcnow()
                    new_event['updated_at'] = datetime.utcnow()

                    # Limpiar tareas
                    new_event['tasks_request'] = []
                    new_event['tasks_notified'] = []
                    new_event['status'] = 0

                    # Actualizar referencias de personajes en el evento
                    if new_event.get('character_id') and new_event['character_id'] in character_id_map:
                        new_event['character_id'] = character_id_map[new_event['character_id']]

                    # Actualizar referencias de locaciones en el evento
                    if new_event.get('location_id') and new_event['location_id'] in location_id_map:
                        new_event['location_id'] = location_id_map[new_event['location_id']]

                    # Actualizar arrays de personajes si existen
                    if new_event.get('characters_id'):
                        updated_characters_id = []
                        for char_id in new_event['characters_id']:
                            if char_id in character_id_map:
                                updated_characters_id.append(character_id_map[char_id])
                            else:
                                updated_characters_id.append(char_id)
                        new_event['characters_id'] = updated_characters_id

                    # Actualizar arrays de locaciones si existen
                    if new_event.get('locations_id'):
                        updated_locations_id = []
                        for loc_id in new_event['locations_id']:
                            if loc_id in location_id_map:
                                updated_locations_id.append(location_id_map[loc_id])
                            else:
                                updated_locations_id.append(loc_id)
                        new_event['locations_id'] = updated_locations_id

                    result = await db['event'].insert_one(new_event)
                    new_event_id = str(result.inserted_id)
                    new_events_id.append(new_event_id)

                    # Guardar mapeo de IDs de eventos
                    event_id_map[old_event_id] = new_event_id
                    all_id_mappings[old_event_id] = new_event_id

                    cloned_events_count += 1

                print(f"Clonados {cloned_events_count} eventos para el nuevo juego {new_game_id}")

            # 6. ACTUALIZAR EL GAME con los IDs de elementos clonados
            update_data = {
                'locations_id': new_locations_id,
                'characters_id': new_characters_id,
                'items_id': new_items_id
            }

            # Actualizar character_principal si existe y está en el mapa
            if original_game.get('character_principal') and original_game['character_principal'] in character_id_map:
                update_data['character_principal'] = character_id_map[original_game['character_principal']]

            await db['game'].update_one(
                {'_id': game_result.inserted_id},
                {'$set': update_data}
            )

            # 7. REEMPLAZAR TODOS LOS IDs ANTIGUOS EN TODOS LOS OBJETOS CLONADOS
            print(f"Iniciando reemplazo de IDs antiguos. Total de mapeos: {len(all_id_mappings)}")

            # Reemplazar IDs en locations
            for new_location_id in new_locations_id:
                location = await db['location'].find_one({'_id': ObjectId(new_location_id)})
                if location:
                    updated_location = await replace_old_ids_in_object(location, all_id_mappings)
                    await db['location'].update_one(
                        {'_id': ObjectId(new_location_id)},
                        {'$set': updated_location}
                    )

            # Reemplazar IDs en characters
            for new_character_id in new_characters_id:
                character = await db['character'].find_one({'_id': ObjectId(new_character_id)})
                if character:
                    updated_character = await replace_old_ids_in_object(character, all_id_mappings)
                    await db['character'].update_one(
                        {'_id': ObjectId(new_character_id)},
                        {'$set': updated_character}
                    )

            # Reemplazar IDs en items
            for new_item_id in new_items_id:
                item = await db['item'].find_one({'_id': ObjectId(new_item_id)})
                if item:
                    updated_item = await replace_old_ids_in_object(item, all_id_mappings)
                    await db['item'].update_one(
                        {'_id': ObjectId(new_item_id)},
                        {'$set': updated_item}
                    )

            # Reemplazar IDs en eventos
            for new_event_id in new_events_id:
                event = await db['event'].find_one({'_id': ObjectId(new_event_id)})
                if event:
                    updated_event = await replace_old_ids_in_object(event, all_id_mappings)
                    await db['event'].update_one(
                        {'_id': ObjectId(new_event_id)},
                        {'$set': updated_event}
                    )

            # Reemplazar IDs en estados del juego
            for new_state_id in state_game_id_map.values():
                state = await db['state_game'].find_one({'_id': ObjectId(new_state_id)})
                if state:
                    updated_state = await replace_old_ids_in_object(state, all_id_mappings)
                    await db['state_game'].update_one(
                        {'_id': ObjectId(new_state_id)},
                        {'$set': updated_state}
                    )

            # Reemplazar IDs en estados GLIC
            all_new_glic_states = await db['state_glic'].find({
                'element_id': {'$in': new_locations_id + new_characters_id + new_items_id}
            }).to_list(None)

            for glic_state in all_new_glic_states:
                updated_glic_state = await replace_old_ids_in_object(glic_state, all_id_mappings)
                await db['state_glic'].update_one(
                    {'_id': glic_state['_id']},
                    {'$set': updated_glic_state}
                )

            # Reemplazar IDs en el game
            game = await db['game'].find_one({'_id': game_result.inserted_id})
            if game:
                updated_game = await replace_old_ids_in_object(game, all_id_mappings)
                await db['game'].update_one(
                    {'_id': game_result.inserted_id},
                    {'$set': updated_game}
                )

            print(f"Completado reemplazo de IDs antiguos en todos los objetos")

            # 8. Clonar progreso del juego si existe
            original_game_progress = await db['game_progress'].find({'game_id': game_id}).to_list(None)
            cloned_progress_count = 0

            for progress in original_game_progress:
                new_progress = progress.copy()
                del new_progress['_id']
                new_progress['game_id'] = new_game_id
                new_progress['created_by'] = user_id
                new_progress['updated_by'] = user_id
                new_progress['created_at'] = datetime.utcnow()
                new_progress['updated_at'] = datetime.utcnow()
                # Resetear progreso para el nuevo juego
                new_progress['progress'] = 0
                new_progress['is_completed'] = False

                # Reemplazar IDs antiguos en el progreso
                updated_progress = await replace_old_ids_in_object(new_progress, all_id_mappings)
                await db['game_progress'].insert_one(updated_progress)
                cloned_progress_count += 1

            # Retornar el juego clonado completo
            cloned_game = await db['game'].find_one({'_id': game_result.inserted_id})

            # Agregar información adicional para la respuesta
            cloned_game['cloned_from'] = game_id
            cloned_game['cloned_at'] = datetime.utcnow()
            cloned_game['total_elements_cloned'] = {
                'locations': len(new_locations_id),
                'characters': len(new_characters_id),
                'items': len(new_items_id),
                'states': cloned_states_count,
                'id_mappings_applied': len(all_id_mappings)
            }

            return cloned_game

        except Exception as e:
            print(f"Error cloning game service: {str(e)}")
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al clonar el juego: {str(e)}",
            )


async def replace_old_ids_in_object(obj: dict, id_mappings: dict) -> dict:
    """
    Reemplaza recursivamente todos los IDs antiguos por los nuevos en un objeto JSON.

    Args:
        obj: El objeto (diccionario) en el que buscar y reemplazar IDs
        id_mappings: Diccionario con mapeo de IDs antiguos -> IDs nuevos

    Returns:
        El objeto con los IDs reemplazados
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and value in id_mappings:
                # Reemplazar ID encontrado
                obj[key] = id_mappings[value]
            elif isinstance(value, list):
                # Procesar lista
                for i, item in enumerate(value):
                    if isinstance(item, str) and item in id_mappings:
                        value[i] = id_mappings[item]
                    elif isinstance(item, (dict, list)):
                        value[i] = await replace_old_ids_in_object(item, id_mappings)
            elif isinstance(value, dict):
                # Procesar diccionario anidado recursivamente
                obj[key] = await replace_old_ids_in_object(value, id_mappings)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str) and item in id_mappings:
                obj[i] = id_mappings[item]
            elif isinstance(item, (dict, list)):
                obj[i] = await replace_old_ids_in_object(item, id_mappings)

    return obj
