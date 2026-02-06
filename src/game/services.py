import asyncio
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

            existing_code = await self.db['game'].find_one({'code_access': code})

            if not existing_code:
                return code

    async def calculate_number_music_track(self):
        """
        Calcula el número de pista de música para el siguiente juego.
        Busca el último juego creado, obtiene su número y lo incrementa en 1.
        Si es mayor a 3, lo resetea a 1.
        """
        try:
            # Buscar el último juego creado ordenado por fecha de creación descendente
            last_game = await self.db['game'].find_one(
                {},
                sort=[('created_at', -1)]
            )

            if last_game and 'number_music_track' in last_game:
                current_track = last_game['number_music_track']
                # Incrementar en 1, si es mayor a 3, resetear a 1
                next_track = (current_track % 3) + 1
                return next_track
            else:
                # Si no hay juegos previos, empezar en 1
                return 1
        except Exception as e:
            self.logger.error(f"Error calculating number_music_track: {str(e)}")
            return 1

    async def create_game_v2_service(self, user_id: str):
        try:
            # Calcular el número de pista de música
            number_music_track = await self.calculate_number_music_track()

            game_db = Game(
                updated_by=user_id,
                created_by=user_id,
                version=2,
                code_access=await self.generate_code_access_game_service(),
                number_music_track=number_music_track,
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
            # Obtener games_to_review una sola vez
            games_to_review = await self.get_games_of_reviewer(user_id)

            # Construir query combinada
            if games_to_review:
                match_query = {
                    'version': 2,
                    '$or': [
                        {'created_by': user_id},
                        {'_id': {'$in': games_to_review}}
                    ]
                }
            else:
                match_query = {'created_by': user_id, 'version': 2}

            # Pipeline de agregación
            pipeline = [
                {'$match': match_query},
                {'$sort': {'created_at': -1}},
                {'$skip': (skip - 1) * limit},
                {'$limit': limit},
                # Lookup para contar analíticas (plays)
                {
                    '$lookup': {
                        'from': 'analytics',
                        'let': {'game_id': {'$toString': '$_id'}},
                        'pipeline': [
                            {'$match': {'$expr': {'$eq': ['$game_id', '$$game_id']}}},
                            {'$count': 'total'}
                        ],
                        'as': 'analytics_data'
                    }
                },
                # Lookup para obtener estado de publicación
                {
                    '$lookup': {
                        'from': 'published_game',
                        'let': {'game_id': {'$toString': '$_id'}},
                        'pipeline': [
                            {'$match': {'$expr': {'$eq': ['$game_id', '$$game_id']}}},
                            {'$project': {'status': 1, 'return_note': 1}}
                        ],
                        'as': 'published_info'
                    }
                },
                # Lookup para obtener game_provisional
                {
                    '$lookup': {
                        'from': 'game_provisional',
                        'let': {'provisional_id': '$provisional_id'},
                        'pipeline': [
                            {
                                '$match': {
                                    '$expr': {
                                        '$eq': ['$_id', {'$toObjectId': '$$provisional_id'}]
                                    }
                                }
                            }
                        ],
                        'as': 'game_provisional_data'
                    }
                },
                # Agregar campos calculados
                {
                    '$addFields': {
                        'plays': {
                            '$ifNull': [
                                {'$arrayElemAt': ['$analytics_data.total', 0]},
                                0
                            ]
                        },
                        'status': {
                            '$ifNull': [
                                {'$arrayElemAt': ['$published_info.status', 0]},
                                0
                            ]
                        },
                        'reject_note': {
                            '$arrayElemAt': ['$published_info.return_note', 0]
                        },
                        'game_provisional': {
                            '$arrayElemAt': ['$game_provisional_data', 0]
                        }
                    }
                },
                # Limpiar campos temporales
                {'$project': {'analytics_data': 0, 'published_info': 0, 'game_provisional_data': 0}}
            ]

            # Ejecutar agregación y conteo en paralelo
            games_db, count_result = await asyncio.gather(
                db['game'].aggregate(pipeline).to_list(None),
                db['game'].count_documents(match_query)
            )

            # Convertir _id a string para cada juego
            for game in games_db:
                game['_id'] = str(game['_id'])
                # Convertir _id de game_provisional si existe
                if game.get('game_provisional') and game['game_provisional'].get('_id'):
                    game['game_provisional']['_id'] = str(game['game_provisional']['_id'])

            # Marcar juegos para revisar con timestamp actual
            if games_to_review:
                games_to_review_set = set(str(gid) for gid in games_to_review)
                current_time = datetime.utcnow()

                for game in games_db:
                    if game['_id'] in games_to_review_set:
                        game['created_at'] = current_time

                # Reordenar
                games_db.sort(key=lambda x: x['created_at'], reverse=True)

            return games_db, count_result

        except Exception as e:
            self.logger.error(f"Error getting my games service: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Games not found",
            )

    async def get_community_games_service(self, skip: int = 1, limit: int = 100):
        """
        Obtiene juegos comunitarios que están publicados con datos enriquecidos.
        Optimizado con agregación MongoDB para una sola consulta.
        """
        community_categories = [
           "Reading",
           "Maths",
           "Languages",
           "Science & Nature",
           "Social Skills",
           "Values",
           "History",
           "Holidays & Traditions",
           "Emotions",
           "Habits",
           "Stories & Tales"
        ]

        match_query = {
            'version': 2,
            'is_published': True,
            'is_active': True,
            'category_id': {'$in': community_categories}
        }

        pipeline = [
            {'$match': match_query},
            {'$sort': {'created_at': -1}},
            {'$skip': (skip - 1) * limit},
            {'$limit': limit},
            # Contar jugadores únicos que jugaron el juego
            {
                '$lookup': {
                    'from': 'record_game',
                    'let': {'game_id': {'$toString': '$_id'}},
                    'pipeline': [
                        {'$match': {'$expr': {'$eq': ['$game_id', '$$game_id']}}},
                        {'$group': {'_id': '$user_id'}},
                        {'$count': 'count'}
                    ],
                    'as': 'player_stats'
                }
            },
            # Obtener datos del creator
            {
                '$lookup': {
                    'from': 'user',
                    'localField': 'created_by',
                    'foreignField': '_id',
                    'as': 'creator'
                }
            },
            {
                '$lookup': {
                    'from': 'game_provisional',
                    'let': {'provisional_id': '$provisional_id'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': ['$_id', {'$toObjectId': '$$provisional_id'}]
                                }
                            }
                        }
                    ],
                    'as': 'game_provisional_data'
                }
            },
            # Agregar campos calculados
            {
                '$addFields': {
                    'game_provisional': {
                        '$arrayElemAt': ['$game_provisional_data', 0]
                    },
                    'plays': {
                        '$ifNull': [
                            {'$arrayElemAt': ['$player_stats.count', 0]},
                            0
                        ]
                    },
                    'creator_info': {
                        '$arrayElemAt': [
                            {
                                '$map': {
                                    'input': '$creator',
                                    'as': 'c',
                                    'in': {
                                        'name': '$$c.name',
                                        'avatar': '$$c.avatar'
                                    }}}, 0]
                    },
                }
            },
            # Limpiar campos temporales
            {'$project': {
                'player_stats': 0,
                'creator': 0,
                'locations_id': 0,
                'characters_id': 0,
                'items_id': 0,
            }}
        ]

        # Ejecutar agregación y conteo en paralelo
        games_db, count_result = await asyncio.gather(
            db['game'].aggregate(pipeline).to_list(None),
            db['game'].count_documents(match_query)
        )

        # Convertir _id a string para cada juego
        for game in games_db:
            game['_id'] = str(game['_id'])
            # Convertir _id de game_provisional si existe
            if game.get('game_provisional') and game['game_provisional'].get('_id'):
                game['game_provisional']['_id'] = str(game['game_provisional']['_id'])

        # Convertir _id a string
        for game in games_db:
            game['_id'] = str(game['_id'])

        return games_db, count_result

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

    async def get_published_game_detail_service(self, game_id: str) -> dict | None:
        """
        Obtiene los detalles de un juego publicado por ID.
        Solo retorna juegos que están publicados (is_active = True).

        Args:
            game_id: ID del juego publicado

        Returns:
            dict con información completa del juego publicado

        Raises:
            HTTPException: Si el juego no existe o no está publicado
        """
        try:
            # Buscar el juego con is_published = True
            game_db = await self.db['game'].find_one({
                '_id': ObjectId(game_id),

            })

            if not game_db:
                return None

            # Verificar si la serie del juego está publicada
            if game_db.get('serie_id'):
                serie_db = await self.db['series'].find_one({
                    '_id': ObjectId(game_db['serie_id']),
                    'is_published': True,
                    'is_active': True
                })

                # Si la serie no está publicada, no retornar el juego
                if not serie_db:
                    return None

            # Convertir ObjectId a string
            game_db['_id'] = str(game_db['_id'])

            # Obtener locaciones asociadas
            try:
                locations = await self.db['location'].find({
                    'game_id': game_id
                }).to_list(None)
                game_db['locations'] = [
                    {**loc, '_id': str(loc['_id'])} for loc in locations
                ] if locations else []
            except:
                game_db['locations'] = []

            # Obtener personajes asociados
            try:
                characters = await self.db['character'].find({
                    'game_id': game_id
                }).to_list(None)
                game_db['characters'] = [
                    {**char, '_id': str(char['_id'])} for char in characters
                ] if characters else []
            except:
                game_db['characters'] = []

            # Obtener objetos/items asociados
            try:
                items = await self.db['object'].find({
                    'game_id': game_id
                }).to_list(None)
                game_db['items'] = [
                    {**item, '_id': str(item['_id'])} for item in items
                ] if items else []
            except:
                game_db['items'] = []

            return game_db

        except Exception as e:
            self.logger.error(f"Error getting published game detail: {str(e)}")
            raise
