"""
Servicios para actualización de imágenes de personajes (Characters).
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


class CharacterImageUpdateService:
    """Servicio para actualizar imágenes de personajes"""

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

    async def update_character_full_image(
        self,
        character_id: str,
        state_game: str,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza la imagen completa (full body) de un personaje en TODOS los estados.

        NOTA: Cuando se cambia la imagen de un personaje, se actualiza en todos
        los estados donde aparece ese personaje, no solo en uno.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado (usado para validar que existe)
            file: Archivo de imagen (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información de la imagen actualizada
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

            # Leer contenido del archivo
            content = await file.read()
            img_byte_arr = BytesIO(content)
            img_byte_arr.seek(0)

            # Subir imagen a Google Cloud Storage
            image_url = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=f"characters/{character_id}/{uuid4()}_full.jpg",
                size=(1024, 1024)
            )

            # Actualizar en TODOS los estados del personaje
            update_fields = {
                'data.image_full': image_url,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['state_glic'].update_many(
                {
                    'element_id': character_id,
                    'type_element': 'character'
                },
                {'$set': update_fields}
            )

            if result.matched_count == 0:
                raise Exception("Failed to update character full image - no states found")

            return {
                'message': f'Image updated successfully in {result.modified_count} states',
                'image_url': image_url,
                'states_updated': result.modified_count,
                'updated_at': datetime.utcnow(),
                'metadata': {
                    'width': 1024,
                    'height': 1024,
                    'size': len(content),
                    'format': file.content_type.split('/')[-1] if file.content_type else 'jpg'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating character full image: {str(e)}")
            raise

    async def update_character_description_image(
        self,
        character_id: str,
        state_game: str,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza la imagen de referencia/descripción de un personaje en TODOS los estados.

        NOTA: Cuando se cambia la imagen de un personaje, se actualiza en todos
        los estados donde aparece ese personaje, no solo en uno.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado (usado para validar que existe)
            file: Archivo de imagen (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información de la imagen actualizada
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

            # Leer contenido del archivo
            content = await file.read()
            img_byte_arr = BytesIO(content)
            img_byte_arr.seek(0)

            # Subir imagen a Google Cloud Storage
            image_url = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=f"characters/{character_id}/{uuid4()}_description.jpg",
                size=(1024, 576)
            )

            # Actualizar en TODOS los estados del personaje
            update_fields = {
                'data.image_reference': image_url,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['state_glic'].update_many(
                {
                    'element_id': character_id,
                    'type_element': 'character'
                },
                {'$set': update_fields}
            )

            if result.matched_count == 0:
                raise Exception("Failed to update character description image - no states found")

            return {
                'message': f'Image updated successfully in {result.modified_count} states',
                'image_url': image_url,
                'states_updated': result.modified_count,
                'updated_at': datetime.utcnow(),
                'metadata': {
                    'width': 1024,
                    'height': 576,
                    'size': len(content),
                    'format': file.content_type.split('/')[-1] if file.content_type else 'jpg'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating character description image: {str(e)}")
            raise

    async def update_character_image(
        self,
        character_id: str,
        state_game: str,
        file: UploadFile,
        user_id: str
    ) -> dict:
        """
        Actualiza la imagen/avatar (foto) de un personaje en TODOS los estados.

        NOTA: Cuando se cambia la imagen de un personaje, se actualiza en todos
        los estados donde aparece ese personaje, no solo en uno.

        Args:
            character_id: ID del personaje
            state_game: state_game del estado (usado para validar que existe)
            file: Archivo de imagen (UploadFile)
            user_id: ID del usuario que realiza la actualización

        Returns:
            Diccionario con información de la imagen actualizada
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

            # Leer contenido del archivo
            content = await file.read()
            img_byte_arr = BytesIO(content)
            img_byte_arr.seek(0)

            # Subir imagen a Google Cloud Storage
            image_url = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=f"characters/{character_id}/{uuid4()}_avatar.jpg",
                size=(512, 512)
            )

            # Actualizar en TODOS los estados del personaje
            update_fields = {
                'data.image': image_url,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            result = await self.db['state_glic'].update_many(
                {
                    'element_id': character_id,
                    'type_element': 'character'
                },
                {'$set': update_fields}
            )

            if result.matched_count == 0:
                raise Exception("Failed to update character image - no states found")

            return {
                'message': f'Image updated successfully in {result.modified_count} states',
                'image_url': image_url,
                'states_updated': result.modified_count,
                'updated_at': datetime.utcnow(),
                'metadata': {
                    'width': 512,
                    'height': 512,
                    'size': len(content),
                    'format': file.content_type.split('/')[-1] if file.content_type else 'jpg'
                }
            }

        except Exception as e:
            self.logger.error(f"Error updating character image: {str(e)}")
            raise
