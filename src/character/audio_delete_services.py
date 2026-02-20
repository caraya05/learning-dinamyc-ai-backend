"""
Servicios para eliminación de audios de personajes (Characters).
"""

import logging
from bson import ObjectId
from fastapi import HTTPException
from core.database import db

logger = logging.getLogger(__name__)


class CharacterAudioDeleteService:
    """Servicio para eliminar audios de personajes"""

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

    async def delete_dialog_audio(
        self,
        character_id: str,
        state_game: str,
        interaction_index: int,
        dialog_index: int,
        user_id: str
    ) -> dict:
        """
        Elimina el audio de un diálogo de personaje.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado
            interaction_index: Índice de la interacción
            dialog_index: Índice del diálogo
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
            if dialog_index >= len(interaction.get('conversation', [])):
                raise Exception("Dialog index out of range")

            # Verificar que hay audio para eliminar
            dialog = interaction['conversation'][dialog_index]
            if not dialog.get('audio') and not dialog.get('audio_mp3'):
                raise Exception("No audio found for this dialog")

            # Eliminar audios directamente en memoria
            state_glic_check['data']['interaction'][interaction_index]['conversation'][dialog_index]['audio'] = None
            state_glic_check['data']['interaction'][interaction_index]['conversation'][dialog_index]['audio_mp3'] = None

            # Reemplazar el documento completo en la BD
            result = await self.db['state_glic'].replace_one(
                {
                    '_id': ObjectId(state_glic_check.get('_id'))
                },
                state_glic_check
            )

            if result.matched_count == 0:
                raise Exception("Failed to delete dialog audio")

            # Traer el documento actualizado para verificación
            updated_state_glic = await self.db['state_glic'].find_one({
                '_id': ObjectId(state_glic_check.get('_id'))
            })

            if not updated_state_glic:
                raise Exception("Failed to retrieve updated document")

            # Verificar que se eliminó
            updated_audio = updated_state_glic['data']['interaction'][interaction_index]['conversation'][dialog_index].get('audio')
            updated_audio_mp3 = updated_state_glic['data']['interaction'][interaction_index]['conversation'][dialog_index].get('audio_mp3')

            if updated_audio is not None or updated_audio_mp3 is not None:
                raise Exception(f"Failed to delete audio properly")

            return {
                'message': 'Audio deleted successfully',
                'audio_deleted': True,
                'updated_at': updated_state_glic.get('updated_at')
            }

        except Exception as e:
            self.logger.error(f"Error deleting dialog audio: {str(e)}")
            raise
