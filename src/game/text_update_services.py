"""
Servicios para la actualización de textos en juegos, personajes, locaciones y eventos.
Versión corregida que busca estados en la colección state_glic separada.
"""

import logging
from datetime import datetime
from bson import ObjectId
from core.database import db

logger = logging.getLogger(__name__)


class TextUpdateService:
    """Servicio para manejar actualizaciones de textos en el backend"""

    def __init__(self, db_instance=None):
        self.db = db_instance or db
        self.logger = logging.getLogger(__name__)

    # ============ Helper Methods ============
    def _is_valid_objectid(self, value: str) -> bool:
        """Verifica si un string es un ObjectId válido"""
        try:
            ObjectId(value)
            return True
        except:
            return False

    # ============ Game Title Update ============
    async def update_game_title(self, game_id: str, title: str, user_id: str) -> dict:
        """
        Actualiza el título del juego.
        """
        try:
            # Validar que el gameId es válido
            if not self._is_valid_objectid(game_id):
                raise Exception("Invalid game ID format")

            # Buscar el juego
            game = await self.db['game'].find_one({'_id': ObjectId(game_id)})
            if not game:
                raise Exception("Game not found")

            # Verificar permisos
            if str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Actualizar el título
            result = await self.db['game'].update_one(
                {'_id': ObjectId(game_id)},
                {
                    '$set': {
                        'title': title,
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                }
            )

            if result.modified_count == 0:
                raise Exception("Failed to update game title")

            # Retornar el juego actualizado
            updated_game = await self.db['game'].find_one({'_id': ObjectId(game_id)})
            return {
                '_id': str(updated_game['_id']),
                'title': updated_game['title'],
                'updated_at': updated_game['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating game title: {str(e)}")
            raise

    # ============ Character Data Update ============
    async def update_character_data(self, character_id: str, state_id: str, data: dict, user_id: str) -> dict:
        """
        Actualiza los datos de un personaje (nombre y/o descripción).
        Los estados están en la colección 'state_glic' separada.
        """
        try:
            # Validar IDs
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")
            if not self._is_valid_objectid(state_id):
                raise Exception("Invalid state ID format")

            # Buscar el personaje
            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            # Verificar permisos a través del juego
            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Buscar el estado en la colección state_glic
            state_glic = await self.db['state_glic'].find_one({
                'element_id': character_id,
                '_id': ObjectId(state_id),
                'type_element': 'character'
            })

            if not state_glic:
                raise Exception("State not found")

            # Actualizar los campos proporcionados
            update_fields = {}
            if 'name' in data and data['name']:
                update_fields['data.name'] = data['name']
            if 'description' in data and data['description']:
                update_fields['data.description'] = data['description']

            if not update_fields:
                raise Exception("No valid fields to update")

            update_fields['updated_at'] = datetime.utcnow()
            update_fields['updated_by'] = user_id

            result = await self.db['state_glic'].update_one(
                {'_id': ObjectId(state_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update character data")

            # Retornar respuesta
            updated_state = await self.db['state_glic'].find_one({'_id': ObjectId(state_id)})
            return {
                '_id': str(character_id),
                'state_id': str(state_id),
                'data': updated_state.get('data', {}),
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating character data: {str(e)}")
            raise

    # ============ Location Data Update ============
    async def update_location_data(self, location_id: str, state_id: str, data: dict, user_id: str) -> dict:
        """
        Actualiza los datos de una locación (título y/o descripción).
        Los estados están en la colección 'state_glic' separada.
        """
        try:
            # Validar IDs
            if not self._is_valid_objectid(location_id):
                raise Exception("Invalid location ID format")
            if not self._is_valid_objectid(state_id):
                raise Exception("Invalid state ID format")

            # Buscar la locación
            location = await self.db['location'].find_one({'_id': ObjectId(location_id)})
            if not location:
                raise Exception("Location not found")

            # Verificar permisos a través del juego
            game = await self.db['game'].find_one({'_id': ObjectId(location.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Buscar el estado en la colección state_glic
            state_glic = await self.db['state_glic'].find_one({
                'element_id': location_id,
                '_id': ObjectId(state_id),
                'type_element': 'location'
            })

            if not state_glic:
                raise Exception("State not found")

            # Actualizar los campos proporcionados
            update_fields = {}
            if 'title' in data and data['title']:
                update_fields['data.title'] = data['title']
            if 'description' in data and data['description']:
                update_fields['data.description'] = data['description']

            if not update_fields:
                raise Exception("No valid fields to update")

            update_fields['updated_at'] = datetime.utcnow()
            update_fields['updated_by'] = user_id

            result = await self.db['state_glic'].update_one(
                {'_id': ObjectId(state_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update location data")

            # Retornar respuesta
            updated_state = await self.db['state_glic'].find_one({'_id': ObjectId(state_id)})
            return {
                '_id': str(location_id),
                'state_id': str(state_id),
                'data': updated_state.get('data', {}),
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating location data: {str(e)}")
            raise

    # ============ Character Interaction Dialog Update ============
    async def update_interaction_dialog(
        self,
        character_id: str,
        state_id: str,
        interaction_index: int,
        dialog_index: int,
        dialog_text: str,
        user_id: str
    ) -> dict:
        """
        Actualiza el diálogo de una interacción de personaje.
        """
        try:
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")
            if not self._is_valid_objectid(state_id):
                raise Exception("Invalid state ID format")

            # Buscar personaje
            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            # Verificar permisos
            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Buscar estado en state_glic
            state_glic = await self.db['state_glic'].find_one({
                'element_id': character_id,
                '_id': ObjectId(state_id),
                'type_element': 'character'
            })

            if not state_glic:
                raise Exception("State not found")

            # Validar índices
            data = state_glic.get('data', {})
            interactions = data.get('interaction', [])

            if interaction_index >= len(interactions):
                raise Exception("Invalid interaction index")

            conversation = interactions[interaction_index].get('conversation', [])
            if dialog_index >= len(conversation):
                raise Exception("Invalid dialog index")

            # Actualizar diálogo
            interactions[interaction_index]['conversation'][dialog_index]['dialog'] = dialog_text
            data['interaction'] = interactions

            result = await self.db['state_glic'].update_one(
                {'_id': ObjectId(state_id)},
                {
                    '$set': {
                        'data': data,
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                }
            )

            if result.modified_count == 0:
                raise Exception("Failed to update dialog")

            # Retornar respuesta
            updated_state = await self.db['state_glic'].find_one({'_id': ObjectId(state_id)})
            updated_dialog = updated_state['data']['interaction'][interaction_index]['conversation'][dialog_index]

            return {
                'success': True,
                'dialog': updated_dialog,
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating interaction dialog: {str(e)}")
            raise

    # ============ Character Option Question Update ============
    async def update_option_question(
        self,
        character_id: str,
        state_id: str,
        interaction_index: int,
        option_index: int,
        dialog_text: str,
        user_id: str
    ) -> dict:
        """Actualiza la pregunta de una opción múltiple"""
        try:
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")
            if not self._is_valid_objectid(state_id):
                raise Exception("Invalid state ID format")

            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            state_glic = await self.db['state_glic'].find_one({
                'element_id': character_id,
                '_id': ObjectId(state_id),
                'type_element': 'character'
            })

            if not state_glic:
                raise Exception("State not found")

            data = state_glic.get('data', {})
            interactions = data.get('interaction', [])

            if interaction_index >= len(interactions):
                raise Exception("Invalid interaction index")

            options_dialog = interactions[interaction_index].get('options_dialog', {})
            options = options_dialog.get('options', [])

            if option_index >= len(options):
                raise Exception("Invalid option index")

            # Actualizar pregunta
            options[option_index]['prompt_user_option']['dialog'] = dialog_text
            interactions[interaction_index]['options_dialog']['options'] = options
            data['interaction'] = interactions

            result = await self.db['state_glic'].update_one(
                {'_id': ObjectId(state_id)},
                {
                    '$set': {
                        'data': data,
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                }
            )

            if result.modified_count == 0:
                raise Exception("Failed to update option question")

            updated_state = await self.db['state_glic'].find_one({'_id': ObjectId(state_id)})
            updated_option = updated_state['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]

            return {
                'success': True,
                'option': updated_option,
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating option question: {str(e)}")
            raise

    # ============ Character Option Answer Update ============
    async def update_option_answer(
        self,
        character_id: str,
        state_id: str,
        interaction_index: int,
        option_index: int,
        dialog_text: str,
        user_id: str
    ) -> dict:
        """Actualiza la respuesta de una opción múltiple"""
        try:
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")
            if not self._is_valid_objectid(state_id):
                raise Exception("Invalid state ID format")

            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            state_glic = await self.db['state_glic'].find_one({
                'element_id': character_id,
                '_id': ObjectId(state_id),
                'type_element': 'character'
            })

            if not state_glic:
                raise Exception("State not found")

            data = state_glic.get('data', {})
            interactions = data.get('interaction', [])

            if interaction_index >= len(interactions):
                raise Exception("Invalid interaction index")

            options_dialog = interactions[interaction_index].get('options_dialog', {})
            options = options_dialog.get('options', [])

            if option_index >= len(options):
                raise Exception("Invalid option index")

            # Actualizar respuesta
            options[option_index]['prompt_user_answer']['dialog'] = dialog_text
            interactions[interaction_index]['options_dialog']['options'] = options
            data['interaction'] = interactions

            result = await self.db['state_glic'].update_one(
                {'_id': ObjectId(state_id)},
                {
                    '$set': {
                        'data': data,
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                }
            )

            if result.modified_count == 0:
                raise Exception("Failed to update option answer")

            updated_state = await self.db['state_glic'].find_one({'_id': ObjectId(state_id)})
            updated_option = updated_state['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]

            return {
                'success': True,
                'option': updated_option,
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating option answer: {str(e)}")
            raise

    # ============ Character Option Guideline Update ============
    async def update_option_guideline(
        self,
        character_id: str,
        state_id: str,
        interaction_index: int,
        option_index: int,
        guideline: str,
        user_id: str
    ) -> dict:
        """Actualiza la guía de una opción"""
        try:
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")
            if not self._is_valid_objectid(state_id):
                raise Exception("Invalid state ID format")

            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            state_glic = await self.db['state_glic'].find_one({
                'element_id': character_id,
                '_id': ObjectId(state_id),
                'type_element': 'character'
            })

            if not state_glic:
                raise Exception("State not found")

            data = state_glic.get('data', {})
            interactions = data.get('interaction', [])

            if interaction_index >= len(interactions):
                raise Exception("Invalid interaction index")

            options_dialog = interactions[interaction_index].get('options_dialog', {})
            options = options_dialog.get('options', [])

            if option_index >= len(options):
                raise Exception("Invalid option index")

            # Actualizar guía
            options[option_index]['prompt_user_guideline'] = guideline
            interactions[interaction_index]['options_dialog']['options'] = options
            data['interaction'] = interactions

            result = await self.db['state_glic'].update_one(
                {'_id': ObjectId(state_id)},
                {
                    '$set': {
                        'data': data,
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                }
            )

            if result.modified_count == 0:
                raise Exception("Failed to update option guideline")

            return {
                'success': True,
                'guideline': guideline,
                'updated_at': datetime.utcnow()
            }

        except Exception as e:
            self.logger.error(f"Error updating option guideline: {str(e)}")
            raise

    # ============ Event Update ============
    async def update_event(self, event_id: str, data: dict, user_id: str) -> dict:
        """Actualiza datos de evento"""
        try:
            if not self._is_valid_objectid(event_id):
                raise Exception("Invalid event ID format")

            event = await self.db['event'].find_one({'_id': ObjectId(event_id)})
            if not event:
                raise Exception("Event not found")

            # Verificar permisos
            game = await self.db['game'].find_one({'_id': ObjectId(event.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Actualizar campos
            update_fields = {}
            if 'text_image' in data and data['text_image']:
                update_fields['text_image'] = data['text_image']
            if 'description' in data and data['description']:
                update_fields['description'] = data['description']
            if 'prompt_user_text' in data and data['prompt_user_text']:
                update_fields['prompt_user_text'] = data['prompt_user_text']

            if not update_fields:
                raise Exception("No valid fields to update")

            update_fields['updated_at'] = datetime.utcnow()
            update_fields['updated_by'] = user_id

            result = await self.db['event'].update_one(
                {'_id': ObjectId(event_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update event")

            updated_event = await self.db['event'].find_one({'_id': ObjectId(event_id)})
            return {
                '_id': str(updated_event['_id']),
                'text_image': updated_event.get('text_image'),
                'description': updated_event.get('description'),
                'prompt_user_text': updated_event.get('prompt_user_text'),
                'updated_at': updated_event['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating event: {str(e)}")
            raise

    # ============ Character Open Question Update ============
    async def update_open_question_dialog(
        self,
        character_id: str,
        state_id: str,
        interaction_index: int,
        question_index: int,
        dialog_text: str,
        user_id: str
    ) -> dict:
        """Actualiza diálogo de pregunta abierta"""
        try:
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")
            if not self._is_valid_objectid(state_id):
                raise Exception("Invalid state ID format")

            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            state_glic = await self.db['state_glic'].find_one({
                'element_id': character_id,
                '_id': ObjectId(state_id),
                'type_element': 'character'
            })

            if not state_glic:
                raise Exception("State not found")

            data = state_glic.get('data', {})
            interactions = data.get('interaction', [])

            if interaction_index >= len(interactions):
                raise Exception("Invalid interaction index")

            options_dialog = interactions[interaction_index].get('options_dialog', {})
            questions = options_dialog.get('prompt_user_question', [])

            if question_index >= len(questions):
                raise Exception("Invalid question index")

            # Actualizar pregunta
            questions[question_index]['dialog'] = dialog_text
            interactions[interaction_index]['options_dialog']['prompt_user_question'] = questions
            data['interaction'] = interactions

            result = await self.db['state_glic'].update_one(
                {'_id': ObjectId(state_id)},
                {
                    '$set': {
                        'data': data,
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                }
            )

            if result.modified_count == 0:
                raise Exception("Failed to update open question dialog")

            updated_state = await self.db['state_glic'].find_one({'_id': ObjectId(state_id)})
            updated_question = updated_state['data']['interaction'][interaction_index]['options_dialog']['prompt_user_question'][question_index]

            return {
                'success': True,
                'question': updated_question,
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating open question dialog: {str(e)}")
            raise
