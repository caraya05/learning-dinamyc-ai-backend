"""
Servicios para actualización de textos de personajes (Characters).
Busca y actualiza datos en la colección state_glic.
"""

import logging
from datetime import datetime
from bson import ObjectId
from core.database import db

logger = logging.getLogger(__name__)


class CharacterTextUpdateService:
    """Servicio para actualizar textos de personajes"""

    def __init__(self, db_instance=None):
        self.db = db_instance or db
        self.logger = logging.getLogger(__name__)

    def _is_valid_objectid(self, value: str) -> bool:
        """Verifica si un string es un ObjectId válido"""
        try:
            ObjectId(value)
            return True
        except:
            return False

    # ============ Character Data Update ============
    async def update_character_data(self, character_id: str, state_game: str, data: dict, user_id: str) -> dict:
        """
        Actualiza los datos de un personaje (nombre y/o descripción).
        IMPORTANTE: Se actualiza en TODOS los estados en los que está el personaje,
        no solo en el estado específico.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado (búsqueda en state_glic)
            data: Diccionario con los campos a actualizar (name, description)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con los datos actualizados

        Raises:
            Exception: Si el personaje o estado no existe
        """
        try:
            # Validar IDs
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")

            # Buscar el personaje
            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            # Verificar permisos a través del juego
            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Buscar el estado en la colección state_glic para validar que existe
            state_glic = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
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

            # Actualizar en TODOS los estados en los que está este personaje
            result = await self.db['state_glic'].update_many(
                {
                    'element_id': character_id,
                    'type_element': 'character'
                },
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update character data")

            # Retornar respuesta
            updated_state = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })
            return {
                '_id': str(character_id),
                'state': state_game,
                'data': updated_state.get('data', {}),
                'updated_at': updated_state['updated_at'],
                'updated_states_count': result.modified_count
            }

        except Exception as e:
            self.logger.error(f"Error updating character data: {str(e)}")
            raise

    # ============ Character Interaction Dialog Update ============
    async def update_interaction_dialog(
        self,
        character_id: str,
        state_game: str,
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

            # Buscar personaje
            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            # Verificar permisos
            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Buscar estado en state_glic usando state_game y element_id
            state_glic = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
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
                {
                    'element_id': character_id,
                    'state': state_game,
                    'type_element': 'character'
                },
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
            updated_state = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })
            updated_dialog = updated_state['data']['interaction'][interaction_index]['conversation'][dialog_index]

            return {
                'success': True,
                'dialog': updated_dialog,
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating interaction dialog: {str(e)}")
            raise

    # ...existing code...

    # ============ Character Open Question Update ============
    async def update_open_question_dialog(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        question_index: int,
        dialog_text: str,
        user_id: str
    ) -> dict:
        """Actualiza diálogo de pregunta abierta"""
        try:
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")

            character = await self.db['character'].find_one({'_id': ObjectId(character_id)})
            if not character:
                raise Exception("Character not found")

            game = await self.db['game'].find_one({'_id': ObjectId(character.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            state_glic = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
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
                {
                    'element_id': character_id,
                    'state': state_game,
                    'type_element': 'character'
                },
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

            updated_state = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })
            updated_question = updated_state['data']['interaction'][interaction_index]['options_dialog']['prompt_user_question'][question_index]

            return {
                'success': True,
                'question': updated_question,
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating open question dialog: {str(e)}")
            raise

    # ============ Option Multiple Dialog Update ============
    async def update_option_question(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        option_index: int,
        dialog: str,
        user_id: str
    ) -> dict:
        """
        Actualiza el texto de la pregunta de una opción múltiple.

        Args:
            character_id: ID del personaje
            state_game: ID del estado del juego
            interaction_index: Índice de la interacción
            option_index: Índice de la opción
            dialog: Nuevo texto de la pregunta
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con el diálogo actualizado

        Raises:
            Exception: Si hay errores de validación
        """
        try:
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")

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
                'state': state_game,
                'type_element': 'character'
            })

            if not state_glic:
                raise Exception("State not found")

            # Validar índices
            data = state_glic.get('data', {})
            interactions = data.get('interaction', [])

            if interaction_index >= len(interactions):
                raise Exception(f"Interaction not found at index {interaction_index}")

            interaction = interactions[interaction_index]

            if 'options_dialog' not in interaction:
                raise Exception("This interaction doesn't have options_dialog")

            options = interaction['options_dialog'].get('options', [])

            if option_index >= len(options):
                raise Exception(f"Option not found at index {option_index}")

            # Validar dialog
            if not dialog or not dialog.strip():
                raise Exception("Dialog cannot be empty")

            # Actualizar en MongoDB
            update_path = f"data.interaction.{interaction_index}.options_dialog.options.{option_index}.prompt_user_option.dialog"

            result = await self.db['state_glic'].update_one(
                {
                    'element_id': character_id,
                    'state': state_game,
                    'type_element': 'character'
                },
                {
                    '$set': {
                        update_path: dialog.strip(),
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                }
            )

            if result.modified_count == 0:
                raise Exception("Failed to update option question dialog")

            # Retornar respuesta
            updated_state = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })
            updated_option = updated_state['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]

            return {
                'success': True,
                'option': updated_option,
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating option question dialog: {str(e)}")
            raise

    async def update_option_answer(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        option_index: int,
        dialog: str,
        user_id: str
    ) -> dict:
        """
        Actualiza el texto de la respuesta de una opción múltiple.

        Args:
            character_id: ID del personaje
            state_game: ID del estado del juego
            interaction_index: Índice de la interacción
            option_index: Índice de la opción
            dialog: Nuevo texto de la respuesta
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con el diálogo actualizado

        Raises:
            Exception: Si hay errores de validación
        """
        try:
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")

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
                'state': state_game,
                'type_element': 'character'
            })

            if not state_glic:
                raise Exception("State not found")

            # Validar índices
            data = state_glic.get('data', {})
            interactions = data.get('interaction', [])

            if interaction_index >= len(interactions):
                raise Exception(f"Interaction not found at index {interaction_index}")

            interaction = interactions[interaction_index]

            if 'options_dialog' not in interaction:
                raise Exception("This interaction doesn't have options_dialog")

            options = interaction['options_dialog'].get('options', [])

            if option_index >= len(options):
                raise Exception(f"Option not found at index {option_index}")

            # Validar dialog
            if not dialog or not dialog.strip():
                raise Exception("Dialog cannot be empty")

            # Actualizar en MongoDB
            update_path = f"data.interaction.{interaction_index}.options_dialog.options.{option_index}.prompt_user_answer.dialog"

            result = await self.db['state_glic'].update_one(
                {
                    'element_id': character_id,
                    'state': state_game,
                    'type_element': 'character'
                },
                {
                    '$set': {
                        update_path: dialog.strip(),
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                }
            )

            if result.modified_count == 0:
                raise Exception("Failed to update option answer dialog")

            # Retornar respuesta
            updated_state = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })
            updated_option = updated_state['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]

            return {
                'success': True,
                'option': updated_option,
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating option answer dialog: {str(e)}")
            raise

    async def update_option_guideline(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        option_index: int,
        guideline: str,
        user_id: str
    ) -> dict:
        """
        Actualiza la guía (guideline) de una opción múltiple.

        Args:
            character_id: ID del personaje
            state_game: ID del estado del juego
            interaction_index: Índice de la interacción
            option_index: Índice de la opción
            guideline: Nueva guía para la IA
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con la guía actualizada

        Raises:
            Exception: Si hay errores de validación
        """
        try:
            if not self._is_valid_objectid(character_id):
                raise Exception("Invalid character ID format")

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
                'state': state_game,
                'type_element': 'character'
            })

            if not state_glic:
                raise Exception("State not found")

            # Validar índices
            data = state_glic.get('data', {})
            interactions = data.get('interaction', [])

            if interaction_index >= len(interactions):
                raise Exception(f"Interaction not found at index {interaction_index}")

            interaction = interactions[interaction_index]

            if 'options_dialog' not in interaction:
                raise Exception("This interaction doesn't have options_dialog")

            options = interaction['options_dialog'].get('options', [])

            if option_index >= len(options):
                raise Exception(f"Option not found at index {option_index}")

            # Validar guideline
            if not guideline or not guideline.strip():
                raise Exception("Guideline cannot be empty")

            # Actualizar en MongoDB
            update_path = f"data.interaction.{interaction_index}.options_dialog.options.{option_index}.prompt_user_guideline"

            result = await self.db['state_glic'].update_one(
                {
                    'element_id': character_id,
                    'state': state_game,
                    'type_element': 'character'
                },
                {
                    '$set': {
                        update_path: guideline.strip(),
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                }
            )

            if result.modified_count == 0:
                raise Exception("Failed to update option guideline")

            # Retornar respuesta
            return {
                'success': True,
                'guideline': guideline.strip(),
                'updated_at': datetime.utcnow()
            }

        except Exception as e:
            self.logger.error(f"Error updating option guideline: {str(e)}")
            raise

