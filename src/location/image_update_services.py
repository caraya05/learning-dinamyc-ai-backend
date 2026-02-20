"""
Servicios para actualización de imágenes de locaciones (Locations).
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


class LocationImageUpdateService:
    """Servicio para actualizar imágenes de locaciones"""

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

    async def update_location_image(
        self,
        location_id: str,
        state_game: str,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza la imagen de una locación.

        Args:
            location_id: ID de la locación
            state_game: state_game del estado
            file: Archivo de imagen (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información de la imagen actualizada
        """
        try:
            if not self._is_valid_objectid(location_id):
                raise Exception("Invalid location ID format")

            # Buscar locación
            location = await self.db['location'].find_one({'_id': ObjectId(location_id)})
            if not location:
                raise Exception("Location not found")

            # Verificar permisos
            game = await self.db['game'].find_one({'_id': ObjectId(location.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Buscar estado en state_glic
            state_glic = await self.db['state_glic'].find_one({
                'element_id': location_id,
                'state': state_game,
                'type_element': 'location'
            })

            if not state_glic:
                raise Exception("State not found")

            # Leer contenido del archivo
            content = await file.read()
            img_byte_arr = BytesIO(content)
            img_byte_arr.seek(0)

            # Subir imagen a Google Cloud Storage
            image_url = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=f"locations/{location_id}/{uuid4()}_image.jpg",
                size=(1920, 1080)
            )

            # Actualizar en state_glic
            update_fields = {
                'data.image': image_url,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['state_glic'].update_one(
                {
                    'element_id': location_id,
                    'state': state_game,
                    'type_element': 'location'
                },
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update location image")

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
            self.logger.error(f"Error updating location image: {str(e)}")
            raise
