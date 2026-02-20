"""
Servicios para actualización de imágenes de juegos (Games).
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


class GameImageUpdateService:
    """Servicio para actualizar imágenes de juegos"""

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

    async def update_game_cover(
        self,
        game_id: str,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza la portada (cover) de un juego.

        Args:
            game_id: ID del juego
            file: Archivo de imagen (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información de la imagen actualizada
        """
        try:
            if not self._is_valid_objectid(game_id):
                raise Exception("Invalid game ID format")

            # Buscar juego
            game = await self.db['game'].find_one({'_id': ObjectId(game_id)})
            if not game:
                raise Exception("Game not found")

            # Verificar permisos
            if str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Leer contenido del archivo
            content = await file.read()
            img_byte_arr = BytesIO(content)
            img_byte_arr.seek(0)

            # Subir imagen a Google Cloud Storage
            image_url = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=f"games/{game_id}/{uuid4()}_cover.jpg",
                size=(1920, 1080)
            )

            # Actualizar en game
            update_fields = {
                'image': image_url,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['game'].update_one(
                {'_id': ObjectId(game_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update game cover")

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
            self.logger.error(f"Error updating game cover: {str(e)}")
            raise

    async def update_game_background(
        self,
        game_id: str,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza el fondo (background) de un juego.

        Args:
            game_id: ID del juego
            file: Archivo de imagen (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información de la imagen actualizada
        """
        try:
            if not self._is_valid_objectid(game_id):
                raise Exception("Invalid game ID format")

            # Buscar juego
            game = await self.db['game'].find_one({'_id': ObjectId(game_id)})
            if not game:
                raise Exception("Game not found")

            # Verificar permisos
            if str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Leer contenido del archivo
            content = await file.read()
            img_byte_arr = BytesIO(content)
            img_byte_arr.seek(0)

            # Subir imagen a Google Cloud Storage
            image_url = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=f"games/{game_id}/{uuid4()}_background.jpg",
                size=(1920, 1080)
            )

            # Actualizar en game
            update_fields = {
                'image_background': image_url,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['game'].update_one(
                {'_id': ObjectId(game_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update game background")

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
            self.logger.error(f"Error updating game background: {str(e)}")
            raise

    async def update_game_minimalist(
        self,
        game_id: str,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza el ícono minimalista de un juego.

        Args:
            game_id: ID del juego
            file: Archivo de imagen (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información de la imagen actualizada
        """
        try:
            if not self._is_valid_objectid(game_id):
                raise Exception("Invalid game ID format")

            # Buscar juego
            game = await self.db['game'].find_one({'_id': ObjectId(game_id)})
            if not game:
                raise Exception("Game not found")

            # Verificar permisos
            if str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            # Leer contenido del archivo
            content = await file.read()
            img_byte_arr = BytesIO(content)
            img_byte_arr.seek(0)

            # Subir imagen a Google Cloud Storage
            image_url = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=f"games/{game_id}/{uuid4()}_minimalist.jpg",
                size=(512, 512)
            )

            # Actualizar en game
            update_fields = {
                'image_minimalist': image_url,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['game'].update_one(
                {'_id': ObjectId(game_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update game minimalist")

            return {
                'message': 'Image updated successfully',
                'image_url': image_url,
                'updated_at': datetime.utcnow(),
                'metadata': {
                    'width': 512,
                    'height': 512,
                    'size': len(content),
                    'format': file.content_type.split('/')[-1] if file.content_type else 'jpg'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating game minimalist: {str(e)}")
            raise
