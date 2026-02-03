"""
Servicios para eliminación de videos en interacciones de personajes (Characters).
"""

import logging
from bson import ObjectId
from fastapi import HTTPException
from core.database import db

logger = logging.getLogger(__name__)


class CharacterInteractionVideoDeleteService:
    """Servicio para eliminar videos de interacciones de personajes"""

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

    async def delete_interaction_video(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        user_id: str
    ) -> dict:
        """
        Elimina el video de una interacción de personaje.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado
            interaction_index: Índice de la interacción
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con confirmación de eliminación
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

            # Validar que la interacción existe
            if interaction_index >= len(state_glic_check.get('data', {}).get('interaction', [])):
                raise Exception("Interaction index out of range")

            interaction = state_glic_check['data']['interaction'][interaction_index]

            # Verificar que hay video para eliminar
            if not interaction.get('video_url'):
                raise Exception("No video found for this interaction")

            # Eliminar el video en memoria
            state_glic_check['data']['interaction'][interaction_index]['video_url'] = None
            state_glic_check['data']['interaction'][interaction_index]['video_compressed_quality'] = None
            state_glic_check['data']['interaction'][interaction_index]['video_file_name'] = None

            # Reemplazar el documento completo en la BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_check.get('_id'))
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to delete interaction video")

            # Traer el documento actualizado para verificación
            updated_state_glic = await self.db['state_glic'].find_one({
                '_id': ObjectId(state_glic_check.get('_id'))
            })

            if not updated_state_glic:
                raise Exception("Failed to retrieve updated document")

            # Verificar que se eliminó
            updated_video_url = updated_state_glic['data']['interaction'][interaction_index].get('video_url')

            if updated_video_url is not None:
                raise Exception("Failed to delete video properly")

            return {
                'message': 'Video deleted successfully',
                'video_deleted': True,
                'updated_at': updated_state_glic.get('updated_at')
            }

        except Exception as e:
            self.logger.error(f"Error deleting interaction video: {str(e)}")
            raise
