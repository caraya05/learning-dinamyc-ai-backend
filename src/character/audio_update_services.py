"""
Servicios para actualización de audios de personajes (Characters).
"""

import logging
from datetime import datetime
from bson import ObjectId
from fastapi import UploadFile
from io import BytesIO
from uuid import uuid4
from core.database import db
from utils import upload_audio

logger = logging.getLogger(__name__)


class CharacterAudioUpdateService:
    """Servicio para actualizar audios de personajes"""

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

    async def update_dialog_audio(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        dialog_index: int,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza el audio de un diálogo de personaje.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado
            interaction_index: Índice de la interacción
            dialog_index: Índice del diálogo
            file: Archivo de audio (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información del audio actualizado
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

            # Validar que el estado_game existe y obtener su _id
            state_glic_check = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })

            if not state_glic_check:
                raise Exception("State not found")

            state_glic_id = state_glic_check.get('_id')

            # Validar que la interacción existe
            if interaction_index >= len(state_glic_check.get('data', {}).get('interaction', [])):
                raise Exception("Interaction index out of range")

            interaction = state_glic_check['data']['interaction'][interaction_index]
            if dialog_index >= len(interaction.get('conversation', [])):
                raise Exception("Dialog index out of range")

            # Leer contenido del archivo
            content = await file.read()
            audio_byte_arr = BytesIO(content)
            audio_byte_arr.seek(0)

            # Subir audio a Google Cloud Storage
            audio_url = upload_audio(
                file_name=f"characters/{character_id}/audios/{uuid4()}_dialog.mp3",
                audio_byte_arr=audio_byte_arr
            )

            # Actualizar directamente el objeto en memoria y luego reemplazar en BD
            # Esto asegura que el update funciona correctamente
            state_glic_check['data']['interaction'][interaction_index]['conversation'][dialog_index]['audio'] = audio_url
            state_glic_check['data']['interaction'][interaction_index]['conversation'][dialog_index]['audio_mp3'] = audio_url
            state_glic_check['updated_at'] = datetime.utcnow()
            state_glic_check['updated_by'] = user_id

            # Reemplazar el documento completo en la BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_id)
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to update dialog audio")

            if result.modified_count == 0:
                raise Exception("No documents were modified")

            # Traer el objeto actualizado de la base de datos para verificación
            updated_state_glic = await self.db['state_glic'].find_one({
                '_id': ObjectId(state_glic_id)
            })

            if not updated_state_glic:
                raise Exception("Failed to retrieve updated document")

            # Obtener el audio actualizado desde la BD
            updated_audio = updated_state_glic['data']['interaction'][interaction_index]['conversation'][dialog_index].get('audio')
            updated_audio_mp3 = updated_state_glic['data']['interaction'][interaction_index]['conversation'][dialog_index].get('audio_mp3')

            # Comparar que la URL se cambió correctamente
            if updated_audio != audio_url or updated_audio_mp3 != audio_url:
                raise Exception(f"Audio URL mismatch in database. Expected: {audio_url}, Got audio: {updated_audio}, audio_mp3: {updated_audio_mp3}")

            return {
                'message': 'Audio updated successfully',
                'audio_url': audio_url,
                'database_url': updated_audio,
                'urls_match': updated_audio == audio_url and updated_audio_mp3 == audio_url,
                'updated_at': updated_state_glic.get('updated_at'),
                'metadata': {
                    'size': len(content),
                    'format': 'mp3'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating dialog audio: {str(e)}")
            raise

    async def update_option_question_audio(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        option_index: int,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza el audio de una pregunta de opción.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado
            interaction_index: Índice de la interacción
            option_index: Índice de la opción
            file: Archivo de audio (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información del audio actualizado
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

            # Validar que el estado_game existe
            state_glic_check = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })

            if not state_glic_check:
                raise Exception("State not found")

            state_glic_id = state_glic_check.get('_id')

            # Validar índices
            if interaction_index >= len(state_glic_check.get('data', {}).get('interaction', [])):
                raise Exception("Interaction index out of range")

            interaction = state_glic_check['data']['interaction'][interaction_index]
            if option_index >= len(interaction.get('options_dialog', {}).get('options', [])):
                raise Exception("Option index out of range")

            # Leer contenido del archivo
            content = await file.read()
            audio_byte_arr = BytesIO(content)
            audio_byte_arr.seek(0)

            # Subir audio a Google Cloud Storage
            audio_url = upload_audio(
                file_name=f"characters/{character_id}/audios/{uuid4()}_option_question.mp3",
                audio_byte_arr=audio_byte_arr
            )

            # Actualizar directamente en memoria
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_option']['audio'] = audio_url
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_option']['audio_mp3'] = audio_url
            state_glic_check['updated_at'] = datetime.utcnow()
            state_glic_check['updated_by'] = user_id

            # Reemplazar en BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_id)
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to update option question audio")

            # Traer el objeto actualizado
            updated_state_glic = await self.db['state_glic'].find_one({
                '_id': ObjectId(state_glic_id)
            })

            if not updated_state_glic:
                raise Exception("Failed to retrieve updated document")

            # Obtener el audio actualizado desde la BD
            updated_audio = updated_state_glic['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_option'].get('audio')
            updated_audio_mp3 = updated_state_glic['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_option'].get('audio_mp3')

            # Comparar que la URL se cambió correctamente
            if updated_audio != audio_url or updated_audio_mp3 != audio_url:
                raise Exception(f"Audio URL mismatch in database. Expected: {audio_url}, Got audio: {updated_audio}, audio_mp3: {updated_audio_mp3}")

            return {
                'message': 'Audio updated successfully',
                'audio_url': audio_url,
                'database_url': updated_audio,
                'urls_match': updated_audio == audio_url and updated_audio_mp3 == audio_url,
                'updated_at': updated_state_glic.get('updated_at'),
                'metadata': {
                    'size': len(content),
                    'format': 'mp3'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating option question audio: {str(e)}")
            raise

    async def update_option_answer_audio(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        option_index: int,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza el audio de una respuesta de opción.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado
            interaction_index: Índice de la interacción
            option_index: Índice de la opción
            file: Archivo de audio (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información del audio actualizado
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

            # Validar que el estado_game existe
            state_glic_check = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })

            if not state_glic_check:
                raise Exception("State not found")

            state_glic_id = state_glic_check.get('_id')

            # Validar índices
            if interaction_index >= len(state_glic_check.get('data', {}).get('interaction', [])):
                raise Exception("Interaction index out of range")

            interaction = state_glic_check['data']['interaction'][interaction_index]
            if option_index >= len(interaction.get('options_dialog', {}).get('options', [])):
                raise Exception("Option index out of range")

            # Leer contenido del archivo
            content = await file.read()
            audio_byte_arr = BytesIO(content)
            audio_byte_arr.seek(0)

            # Subir audio a Google Cloud Storage
            audio_url = upload_audio(
                file_name=f"characters/{character_id}/audios/{uuid4()}_option_answer.mp3",
                audio_byte_arr=audio_byte_arr
            )

            # Actualizar directamente en memoria
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_answer']['audio'] = audio_url
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_answer']['audio_mp3'] = audio_url
            state_glic_check['updated_at'] = datetime.utcnow()
            state_glic_check['updated_by'] = user_id

            # Reemplazar en BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_id)
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to update option answer audio")

            # Traer el objeto actualizado
            updated_state_glic = await self.db['state_glic'].find_one({
                '_id': ObjectId(state_glic_id)
            })

            if not updated_state_glic:
                raise Exception("Failed to retrieve updated document")

            # Obtener el audio actualizado desde la BD
            updated_audio = updated_state_glic['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_answer'].get('audio')
            updated_audio_mp3 = updated_state_glic['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_answer'].get('audio_mp3')

            # Comparar que la URL se cambió correctamente
            if updated_audio != audio_url or updated_audio_mp3 != audio_url:
                raise Exception(f"Audio URL mismatch in database. Expected: {audio_url}, Got audio: {updated_audio}, audio_mp3: {updated_audio_mp3}")

            return {
                'message': 'Audio updated successfully',
                'audio_url': audio_url,
                'database_url': updated_audio,
                'urls_match': updated_audio == audio_url and updated_audio_mp3 == audio_url,
                'updated_at': updated_state_glic.get('updated_at'),
                'metadata': {
                    'size': len(content),
                    'format': 'mp3'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating option answer audio: {str(e)}")
            raise

    async def update_open_question_audio(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        question_index: int,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza el audio de una pregunta abierta.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado
            interaction_index: Índice de la interacción
            question_index: Índice de la pregunta
            file: Archivo de audio (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información del audio actualizado
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

            # Validar que el estado_game existe
            state_glic_check = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })

            if not state_glic_check:
                raise Exception("State not found")

            state_glic_id = state_glic_check.get('_id')

            # Validar índices
            if interaction_index >= len(state_glic_check.get('data', {}).get('interaction', [])):
                raise Exception("Interaction index out of range")

            interaction = state_glic_check['data']['interaction'][interaction_index]
            if question_index >= len(interaction.get('options_dialog', {}).get('prompt_user_question', [])):
                raise Exception("Question index out of range")

            # Leer contenido del archivo
            content = await file.read()
            audio_byte_arr = BytesIO(content)
            audio_byte_arr.seek(0)

            # Subir audio a Google Cloud Storage
            audio_url = upload_audio(
                file_name=f"characters/{character_id}/audios/{uuid4()}_question.mp3",
                audio_byte_arr=audio_byte_arr
            )

            # Actualizar directamente en memoria
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['prompt_user_question'][question_index]['audio'] = audio_url
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['prompt_user_question'][question_index]['audio_mp3'] = audio_url
            state_glic_check['updated_at'] = datetime.utcnow()
            state_glic_check['updated_by'] = user_id

            # Reemplazar en BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_id)
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to update open question audio")

            # Traer el objeto actualizado
            updated_state_glic = await self.db['state_glic'].find_one({
                '_id': ObjectId(state_glic_id)
            })

            if not updated_state_glic:
                raise Exception("Failed to retrieve updated document")

            # Obtener el audio actualizado desde la BD
            updated_audio = updated_state_glic['data']['interaction'][interaction_index]['options_dialog']['prompt_user_question'][question_index].get('audio')
            updated_audio_mp3 = updated_state_glic['data']['interaction'][interaction_index]['options_dialog']['prompt_user_question'][question_index].get('audio_mp3')

            # Comparar que la URL se cambió correctamente
            if updated_audio != audio_url or updated_audio_mp3 != audio_url:
                raise Exception(f"Audio URL mismatch in database. Expected: {audio_url}, Got audio: {updated_audio}, audio_mp3: {updated_audio_mp3}")

            return {
                'message': 'Audio updated successfully',
                'audio_url': audio_url,
                'database_url': updated_audio,
                'urls_match': updated_audio == audio_url and updated_audio_mp3 == audio_url,
                'updated_at': updated_state_glic.get('updated_at'),
                'metadata': {
                    'size': len(content),
                    'format': 'mp3'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating open question audio: {str(e)}")
            raise

    async def delete_option_question_audio(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        option_index: int,
        user_id: str
    ) -> bool:
        """
        Elimina el audio de una pregunta de opción.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado
            interaction_index: Índice de la interacción
            option_index: Índice de la opción
            user_id: ID del usuario que realiza la actualización

        Returns:
            bool: True si se eliminó correctamente

        Raises:
            Exception: Si hay errores
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

            # Validar que el estado_game existe
            state_glic_check = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })

            if not state_glic_check:
                raise Exception("State not found")

            state_glic_id = state_glic_check.get('_id')

            # Validar índices
            if interaction_index >= len(state_glic_check.get('data', {}).get('interaction', [])):
                raise Exception("Interaction index out of range")

            interaction = state_glic_check['data']['interaction'][interaction_index]
            if option_index >= len(interaction.get('options_dialog', {}).get('options', [])):
                raise Exception("Option index out of range")

            # Eliminar audio
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_option']['audio'] = None
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_option']['audio_mp3'] = None
            state_glic_check['updated_at'] = datetime.utcnow()
            state_glic_check['updated_by'] = user_id

            # Reemplazar en BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_id)
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to delete option question audio")

            return True

        except Exception as e:
            self.logger.error(f"Error deleting option question audio: {str(e)}")
            raise

    async def delete_option_answer_audio(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        option_index: int,
        user_id: str
    ) -> bool:
        """
        Elimina el audio de una respuesta de opción.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado
            interaction_index: Índice de la interacción
            option_index: Índice de la opción
            user_id: ID del usuario que realiza la actualización

        Returns:
            bool: True si se eliminó correctamente

        Raises:
            Exception: Si hay errores
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

            # Validar que el estado_game existe
            state_glic_check = await self.db['state_glic'].find_one({
                'element_id': character_id,
                'state': state_game,
                'type_element': 'character'
            })

            if not state_glic_check:
                raise Exception("State not found")

            state_glic_id = state_glic_check.get('_id')

            # Validar índices
            if interaction_index >= len(state_glic_check.get('data', {}).get('interaction', [])):
                raise Exception("Interaction index out of range")

            interaction = state_glic_check['data']['interaction'][interaction_index]
            if option_index >= len(interaction.get('options_dialog', {}).get('options', [])):
                raise Exception("Option index out of range")

            # Eliminar audio
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_answer']['audio'] = None
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index]['prompt_user_answer']['audio_mp3'] = None
            state_glic_check['updated_at'] = datetime.utcnow()
            state_glic_check['updated_by'] = user_id

            # Reemplazar en BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_id)
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to delete option answer audio")

            return True

        except Exception as e:
            self.logger.error(f"Error deleting option answer audio: {str(e)}")
            raise

