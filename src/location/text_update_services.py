"""
Servicios para actualización de textos de locaciones.
"""

import logging
from datetime import datetime
from bson import ObjectId
from core.database import db

logger = logging.getLogger(__name__)


class LocationTextUpdateService:
    """Servicio para actualizar textos de locaciones"""

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

    async def update_location_data(self, location_id: str, state_id: str, data: dict, user_id: str) -> dict:
        """Actualiza título y descripción de una locación"""
        try:
            if not self._is_valid_objectid(location_id):
                raise Exception("Invalid location ID format")
            if not self._is_valid_objectid(state_id):
                raise Exception("Invalid state ID format")

            location = await self.db['location'].find_one({'_id': ObjectId(location_id)})
            if not location:
                raise Exception("Location not found")

            game = await self.db['game'].find_one({'_id': ObjectId(location.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            state_glic = await self.db['state_glic'].find_one({
                'element_id': location_id,
                '_id': ObjectId(state_id),
                'type_element': 'location'
            })

            if not state_glic:
                raise Exception("State not found")

            update_fields = {}
            if 'title' in data and data['title']:
                update_fields['data.title'] = data['title']
            if 'description' in data and data['description']:
                update_fields['data.description'] = data['description']

            if not update_fields:
                raise Exception("No valid fields to update")

            update_fields['updated_at'] = datetime.utcnow()
            update_fields['updated_by'] = user_id

            result = await self.db['state_glic'].update_one(
                {'_id': ObjectId(state_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update location data")

            updated_state = await self.db['state_glic'].find_one({'_id': ObjectId(state_id)})
            return {
                '_id': str(location_id),
                'state_id': str(state_id),
                'data': updated_state.get('data', {}),
                'updated_at': updated_state['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating location data: {str(e)}")
            raise
