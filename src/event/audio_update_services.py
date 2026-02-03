"""
Servicios para actualización de audios de eventos (Events).
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


class EventAudioUpdateService:
    """Servicio para actualizar audios de eventos"""

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

    async def update_event_audio(
        self,
        event_id: str,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza el audio de un evento.

        Args:
            event_id: ID del evento
            file: Archivo de audio (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información del audio actualizado
        """
        try:
            if not self._is_valid_objectid(event_id):
                raise Exception("Invalid event ID format")

            # Buscar evento
            event = await self.db['event'].find_one({'_id': ObjectId(event_id)})
            if not event:
                raise Exception("Event not found")

            # Verificar permisos
            game = await self.db['game'].find_one({'_id': ObjectId(event.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Leer contenido del archivo
            content = await file.read()
            audio_byte_arr = BytesIO(content)
            audio_byte_arr.seek(0)

            # Subir audio a Google Cloud Storage
            audio_url = upload_audio(
                file_name=f"events/{event_id}/audios/{uuid4()}_event.mp3",
                audio_byte_arr=audio_byte_arr
            )

            # Actualizar directamente en memoria
            event['audio'] = audio_url
            event['audio_mp3'] = audio_url
            event['updated_at'] = datetime.utcnow()
            event['updated_by'] = user_id

            # Reemplazar el documento completo en la BD
            result = await self.db['event'].replace_one(
                {'_id': ObjectId(event_id)},
                event
            )

            if result.matched_count == 0:
                raise Exception("Failed to update event audio")

            if result.modified_count == 0:
                raise Exception("No documents were modified")

            # Traer el documento actualizado de la base de datos para verificación
            updated_event = await self.db['event'].find_one({'_id': ObjectId(event_id)})

            if not updated_event:
                raise Exception("Failed to retrieve updated document")

            # Obtener el audio actualizado desde la BD
            updated_audio = updated_event.get('audio')
            updated_audio_mp3 = updated_event.get('audio_mp3')

            # Comparar que la URL se cambió correctamente
            if updated_audio != audio_url or updated_audio_mp3 != audio_url:
                raise Exception(f"Audio URL mismatch in database. Expected: {audio_url}, Got audio: {updated_audio}, audio_mp3: {updated_audio_mp3}")

            return {
                'message': 'Audio updated successfully',
                'audio_url': audio_url,
                'database_url': updated_audio,
                'urls_match': updated_audio == audio_url and updated_audio_mp3 == audio_url,
                'updated_at': updated_event.get('updated_at'),
                'metadata': {
                    'size': len(content),
                    'format': 'mp3'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating event audio: {str(e)}")
            raise
