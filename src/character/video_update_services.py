"""
Servicios para actualización de videos de personajes (Characters).
"""

import logging
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import UploadFile
from uuid import uuid4
from core.database import db
from location.services_video import upload_video_to_gcs, compress_video

logger = logging.getLogger(__name__)


class CharacterVideoUpdateService:
    """Servicio para actualizar videos de personajes"""

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

    async def update_option_question_video(
            self,
            character_id: str,
            state_game: str,
            interaction_index: int,
            option_index: int,
            file: UploadFile,
            user_id: str
    ) -> dict:
        """
        Actualiza el video de una pregunta de opción.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado
            interaction_index: Índice de la interacción
            option_index: Índice de la opción
            file: Archivo de video (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información del video actualizado
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

            # Comprimir video
            compressed_video = await compress_video(file)

            # Subir video a Google Cloud Storage
            file_name = f"characters/{character_id}/videos/{uuid4()}_option_question.mp4"
            video_url = await upload_video_to_gcs(
                video_file=compressed_video,
                file_name=file_name
            )

            # Actualizar directamente en memoria
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_option']['video'] = video_url
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_option']['video_url'] = video_url
            state_glic_check['updated_at'] = datetime.now(timezone.utc)
            state_glic_check['updated_by'] = user_id

            # Reemplazar en BD
            result = await self.db['state_glic'].update_one(
                {
                    '_id': ObjectId(state_glic_id)
                },
                {
                    '$set': state_glic_check
                }
            )

            if result.matched_count == 0:
                raise Exception("Failed to update option question video")

            # Traer el objeto actualizado
            updated_state_glic = await self.db['state_glic'].find_one({
                '_id': ObjectId(state_glic_id)
            })

            if not updated_state_glic:
                raise Exception("Failed to retrieve updated document")

            # Obtener el video actualizado desde la BD
            updated_video = \
            updated_state_glic['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_option'].get('video')
            updated_video_url = \
            updated_state_glic['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_option'].get('video_url')

            # Comparar que la URL se cambió correctamente
            if updated_video != video_url or updated_video_url != video_url:
                raise Exception(
                    f"Video URL mismatch in database. Expected: {video_url}, Got video: {updated_video}, video_url: {updated_video_url}")

            return {
                'message': 'Video updated successfully',
                'video_url': video_url,
                'database_url': updated_video,
                'urls_match': updated_video == video_url and updated_video_url == video_url,
                'updated_at': updated_state_glic.get('updated_at'),
                'metadata': {
                    'format': 'mp4'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating option question video: {str(e)}")
            raise

    async def update_option_answer_video(
            self,
            character_id: str,
            state_game: str,
            interaction_index: int,
            option_index: int,
            file: UploadFile,
            user_id: str
    ) -> dict:
        """
        Actualiza el video de una respuesta de opción.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado
            interaction_index: Índice de la interacción
            option_index: Índice de la opción
            file: Archivo de video (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información del video actualizado
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

            # Comprimir video
            compressed_video = await compress_video(file)

            # Subir video a Google Cloud Storage
            file_name = f"characters/{character_id}/videos/{uuid4()}_option_answer.mp4"
            video_url = await upload_video_to_gcs(
                video_file=compressed_video,
                file_name=file_name
            )

            # Actualizar directamente en memoria
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_answer']['video'] = video_url
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_answer']['video_url'] = video_url
            state_glic_check['updated_at'] = datetime.now(timezone.utc)
            state_glic_check['updated_by'] = user_id

            # Reemplazar en BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_id)
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to update option answer video")

            # Traer el objeto actualizado
            updated_state_glic = await self.db['state_glic'].find_one({
                '_id': ObjectId(state_glic_id)
            })

            if not updated_state_glic:
                raise Exception("Failed to retrieve updated document")

            # Obtener el video actualizado desde la BD
            updated_video = \
            updated_state_glic['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_answer'].get('video')
            updated_video_url = \
            updated_state_glic['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_answer'].get('video_url')

            # Comparar que la URL se cambió correctamente
            if updated_video != video_url or updated_video_url != video_url:
                raise Exception(
                    f"Video URL mismatch in database. Expected: {video_url}, Got video: {updated_video}, video_url: {updated_video_url}")

            return {
                'message': 'Video updated successfully',
                'video_url': video_url,
                'database_url': updated_video,
                'urls_match': updated_video == video_url and updated_video_url == video_url,
                'updated_at': updated_state_glic.get('updated_at'),
                'metadata': {
                    'format': 'mp4'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating option answer video: {str(e)}")
            raise

    async def delete_option_question_video(
            self,
            character_id: str,
            state_game: str,
            interaction_index: int,
            option_index: int,
            user_id: str
    ) -> bool:
        """
        Elimina el video de una pregunta de opción.

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

            # Eliminar video
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_option']['video'] = None
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_option']['video_url'] = None
            state_glic_check['updated_at'] = datetime.now(timezone.utc)
            state_glic_check['updated_by'] = user_id

            # Reemplazar en BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_id)
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to delete option question video")

            return True

        except Exception as e:
            self.logger.error(f"Error deleting option question video: {str(e)}")
            raise

    async def delete_option_answer_video(
            self,
            character_id: str,
            state_game: str,
            interaction_index: int,
            option_index: int,
            user_id: str
    ) -> bool:
        """
        Elimina el video de una respuesta de opción.

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

            # Eliminar video
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_answer']['video'] = None
            state_glic_check['data']['interaction'][interaction_index]['options_dialog']['options'][option_index][
                'prompt_user_answer']['video_url'] = None
            state_glic_check['updated_at'] = datetime.now(timezone.utc)
            state_glic_check['updated_by'] = user_id

            # Reemplazar en BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_id)
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to delete option answer video")

            return True

        except Exception as e:
            self.logger.error(f"Error deleting option answer video: {str(e)}")
            raise


def get_character_video_service(db_instance=None):
    """Dependency para inyectar el servicio de video"""
    return CharacterVideoUpdateService(db_instance)
