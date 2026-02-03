"""
Servicios para la actualización de textos en juegos, personajes, locaciones y eventos.
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

    def _find_state_index(self, state_glic: list, state_id: str) -> int:
        """
        Encuentra el índice de un estado en el array state_glic.
        Maneja comparación de string y ObjectId.

        Returns:
            Índice del estado o None si no encuentra
        """
        for i, s in enumerate(state_glic):
            state_value = s.get('state')
            if state_value:
                # Comparar como string
                if str(state_value) == state_id:
                    return i
                # Comparar como ObjectId si es posible
                try:
                    if str(state_value) == str(ObjectId(state_id)) or str(state_value) == state_id:
                        return i
                except:
                    pass
        return None

    # ============ Game Title Update ============
    async def update_game_title(self, game_id: str, title: str, user_id: str) -> dict:
        """
        Actualiza el título del juego.

        Args:
            game_id: ID del juego
            title: Nuevo título
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con los datos actualizados

        Raises:
            Exception: Si el juego no existe o no hay permisos
        """
        try:
            # Validar que el juego existe
            game = await self.db['game'].find_one({'_id': ObjectId(game_id)})
            if not game:
                raise Exception("Game not found")

            # Verificar permisos (el juego debe pertenecer al usuario)
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

        Los estados se guardan en la colección 'state_glic' separada.

        Args:
            character_id: ID del personaje
            state_id: ID del estado (ObjectId de state_glic)
            data: Diccionario con los campos a actualizar (name, description)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con los datos actualizados

        Raises:
            Exception: Si el personaje o estado no existe
        """
        try:
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
                '_id': ObjectId(state_id) if self._is_valid_objectid(state_id) else state_id
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

            # Retornar el estado actualizado
            updated_state = await self.db['state_glic'].find_one({'_id': ObjectId(state_id)})
            return {
                '_id': str(character_id),
                'state_glic': [updated_state],
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating character data: {str(e)}")
            raise

    # ============ Location Data Update ============
    async def update_location_data(self, location_id: str, state_id: str, data: dict, user_id: str) -> dict:
        """
        Actualiza los datos de una locación (título y/o descripción).

        Los estados se guardan en la colección 'state_glic' separada.

        Args:
            location_id: ID de la locación
            state_id: ID del estado (ObjectId de state_glic)
            data: Diccionario con los campos a actualizar (title, description)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con los datos actualizados

        Raises:
            Exception: Si la locación o estado no existe
        """
        try:
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
                '_id': ObjectId(state_id) if self._is_valid_objectid(state_id) else state_id
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

            # Retornar la locación actualizada
            updated_state = await self.db['state_glic'].find_one({'_id': ObjectId(state_id)})
            return {
                '_id': str(location_id),
                'state_glic': [updated_state],
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

        Ruta: Character → state_glic[stateId] → data → interaction[interactionIndex] → conversation[dialogIndex] → dialog
        """
        try:
            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            # Verificar permisos
            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Encontrar el estado
            state_glic = character.get('state_glic', [])
            state_index = self._find_state_index(state_glic, state_id)
            if state_index is None:
                raise Exception("State not found")

            # Validar índices de interacción y diálogo
            interactions = state_glic[state_index].get('data', {}).get('interaction', [])
            if interaction_index >= len(interactions):
                raise Exception("Invalid interaction index")

            conversation = interactions[interaction_index].get('conversation', [])
            if dialog_index >= len(conversation):
                raise Exception("Invalid dialog index")

            # Actualizar el diálogo
            update_fields = {
                f'state_glic.{state_index}.data.interaction.{interaction_index}.conversation.{dialog_index}.dialog': dialog_text,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['character'].update_one(
                {'_id': ObjectId(character_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update dialog")

            # Retornar respuesta
            updated_character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            updated_dialog = updated_character['state_glic'][state_index]['data']['interaction'][interaction_index]['conversation'][dialog_index]

            return {
                'success': True,
                'dialog': updated_dialog,
                'updated_at': updated_character['updated_at']
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
        """
        Actualiza la pregunta de una opción múltiple.

        Ruta: Character → state_glic[stateId] → data → interaction[interactionIndex] → options_dialog → options[optionIndex] → prompt_user_option → dialog
        """
        try:
            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            # Verificar permisos
            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Encontrar el estado
            state_glic = character.get('state_glic', [])
            state_index = self._find_state_index(state_glic, state_id)
            if state_index is None:
                raise Exception("State not found")

            # Validar índices
            interactions = state_glic[state_index].get('data', {}).get('interaction', [])
            if interaction_index >= len(interactions):
                raise Exception("Invalid interaction index")

            options = interactions[interaction_index].get('options_dialog', {}).get('options', [])
            if option_index >= len(options):
                raise Exception("Invalid option index")

            # Actualizar la pregunta de opción
            update_fields = {
                f'state_glic.{state_index}.data.interaction.{interaction_index}.options_dialog.options.{option_index}.prompt_user_option.dialog': dialog_text,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['character'].update_one(
                {'_id': ObjectId(character_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update option question")

            # Retornar respuesta
            updated_character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            updated_option = updated_character['state_glic'][state_index]['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]

            return {
                'success': True,
                'option': updated_option,
                'updated_at': updated_character['updated_at']
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
        """
        Actualiza la respuesta de una opción múltiple.

        Ruta: Character → state_glic[stateId] → data → interaction[interactionIndex] → options_dialog → options[optionIndex] → prompt_user_answer → dialog
        """
        try:
            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            # Verificar permisos
            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Encontrar el estado
            state_glic = character.get('state_glic', [])
            state_index = self._find_state_index(state_glic, state_id)
            if state_index is None:
                raise Exception("State not found")

            # Validar índices
            interactions = state_glic[state_index].get('data', {}).get('interaction', [])
            if interaction_index >= len(interactions):
                raise Exception("Invalid interaction index")

            options = interactions[interaction_index].get('options_dialog', {}).get('options', [])
            if option_index >= len(options):
                raise Exception("Invalid option index")

            # Actualizar la respuesta de opción
            update_fields = {
                f'state_glic.{state_index}.data.interaction.{interaction_index}.options_dialog.options.{option_index}.prompt_user_answer.dialog': dialog_text,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['character'].update_one(
                {'_id': ObjectId(character_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update option answer")

            # Retornar respuesta
            updated_character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            updated_option = updated_character['state_glic'][state_index]['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]

            return {
                'success': True,
                'option': updated_option,
                'updated_at': updated_character['updated_at']
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
        """
        Actualiza la guía de una opción (para preguntas abiertas).

        Ruta: Character → state_glic[stateId] → data → interaction[interactionIndex] → options_dialog → options[optionIndex] → prompt_user_guideline
        """
        try:
            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            # Verificar permisos
            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Encontrar el estado
            state_glic = character.get('state_glic', [])
            state_index = self._find_state_index(state_glic, state_id)
            if state_index is None:
                raise Exception("State not found")

            # Validar índices
            interactions = state_glic[state_index].get('data', {}).get('interaction', [])
            if interaction_index >= len(interactions):
                raise Exception("Invalid interaction index")

            options = interactions[interaction_index].get('options_dialog', {}).get('options', [])
            if option_index >= len(options):
                raise Exception("Invalid option index")

            # Actualizar la guía de opción
            update_fields = {
                f'state_glic.{state_index}.data.interaction.{interaction_index}.options_dialog.options.{option_index}.prompt_user_guideline': guideline,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['character'].update_one(
                {'_id': ObjectId(character_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update option guideline")

            # Retornar respuesta
            updated_character = await self.db['character'].find_one({'_id': ObjectId(character_id)})

            return {
                'success': True,
                'guideline': guideline,
                'updated_at': updated_character['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating option guideline: {str(e)}")
            raise

    # ============ Event Update ============
    async def update_event(self, event_id: str, data: dict, user_id: str) -> dict:
        """
        Actualiza los datos de un evento.

        Args:
            event_id: ID del evento
            data: Diccionario con los campos a actualizar (text_image, description, prompt_user_text)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con los datos actualizados

        Raises:
            Exception: Si el evento no existe
        """
        try:
            # Buscar el evento
            event = await self.db['event'].find_one({'_id': ObjectId(event_id)})
            if not event:
                raise Exception("Event not found")

            # Verificar permisos a través del juego
            game = await self.db['game'].find_one({'_id': ObjectId(event.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Actualizar los campos proporcionados
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

            # Retornar el evento actualizado
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
        """
        Actualiza el diálogo de una pregunta abierta.

        Ruta: Character → state_glic[stateId] → data → interaction[interactionIndex] → options_dialog → prompt_user_question[questionIndex] → dialog
        """
        try:
            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            # Verificar permisos
            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Encontrar el estado
            state_glic = character.get('state_glic', [])
            state_index = self._find_state_index(state_glic, state_id)
            if state_index is None:
                raise Exception("State not found")

            # Validar índices
            interactions = state_glic[state_index].get('data', {}).get('interaction', [])
            if interaction_index >= len(interactions):
                raise Exception("Invalid interaction index")

            questions = interactions[interaction_index].get('options_dialog', {}).get('prompt_user_question', [])
            if question_index >= len(questions):
                raise Exception("Invalid question index")

            # Actualizar la pregunta abierta
            update_fields = {
                f'state_glic.{state_index}.data.interaction.{interaction_index}.options_dialog.prompt_user_question.{question_index}.dialog': dialog_text,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['character'].update_one(
                {'_id': ObjectId(character_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update open question dialog")

            # Retornar respuesta
            updated_character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            updated_question = updated_character['state_glic'][state_index]['data']['interaction'][interaction_index]['options_dialog']['prompt_user_question'][question_index]

            return {
                'success': True,
                'question': updated_question,
                'updated_at': updated_character['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating open question dialog: {str(e)}")
            raise
