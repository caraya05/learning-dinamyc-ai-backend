"""
Servicios para actualización de imágenes de eventos (Events).
"""

import logging
from datetime import datetime
from bson import ObjectId
from fastapi import UploadFile
from io import BytesIO
from uuid import uuid4
from core.database import db
from utils import upload_image

logger = logging.getLogger(__name__)


class EventImageUpdateService:
    """Servicio para actualizar imágenes de eventos"""

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

    async def update_event_description_image(
        self,
        event_id: str,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza la imagen de descripción de un evento.

        Args:
            event_id: ID del evento
            file: Archivo de imagen (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información de la imagen actualizada
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
            img_byte_arr = BytesIO(content)
            img_byte_arr.seek(0)

            # Subir imagen a Google Cloud Storage
            image_url = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=f"events/{event_id}/{uuid4()}_description.jpg",
                size=(1024, 576)
            )

            # Actualizar en evento
            update_fields = {
                'image_description': image_url,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['event'].update_one(
                {'_id': ObjectId(event_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update event description image")

            return {
                'message': 'Image updated successfully',
                'image_url': image_url,
                'updated_at': datetime.utcnow(),
                'metadata': {
                    'width': 1024,
                    'height': 576,
                    'size': len(content),
                    'format': file.content_type.split('/')[-1] if file.content_type else 'jpg'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating event description image: {str(e)}")
            raise

    async def update_event_image(
        self,
        event_id: str,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza la imagen principal de un evento.

        Args:
            event_id: ID del evento
            file: Archivo de imagen (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información de la imagen actualizada
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
            img_byte_arr = BytesIO(content)
            img_byte_arr.seek(0)

            # Subir imagen a Google Cloud Storage
            image_url = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=f"events/{event_id}/{uuid4()}_image.jpg",
                size=(1920, 1080)
            )

            # Actualizar en evento
            update_fields = {
                'image': image_url,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['event'].update_one(
                {'_id': ObjectId(event_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update event image")

            return {
                'message': 'Image updated successfully',
                'image_url': image_url,
                'updated_at': datetime.utcnow(),
                'metadata': {
                    'width': 1920,
                    'height': 1080,
                    'size': len(content),
                    'format': file.content_type.split('/')[-1] if file.content_type else 'jpg'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating event image: {str(e)}")
            raise
