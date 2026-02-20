"""
Servicios para actualización de textos de eventos.
"""

import logging
from datetime import datetime
from bson import ObjectId
from core.database import db

logger = logging.getLogger(__name__)


class EventTextUpdateService:
    """Servicio para actualizar textos de eventos"""

    def __init__(self, db_instance=None):
        self.db = db_instance or db
        self.logger = logging.getLogger(__name__)

    def _is_valid_objectid(self, value: str) -> bool:
        try:
            ObjectId(value)
            return True
        except:
            return False

    async def update_event(self, event_id: str, data: dict, user_id: str) -> dict:
        """Actualiza datos de evento (text_image, description, prompt_user_text)"""
        try:
            if not self._is_valid_objectid(event_id):
                raise Exception("Invalid event ID format")

            event = await self.db['event'].find_one({'_id': ObjectId(event_id)})
            if not event:
                raise Exception("Event not found")

            game = await self.db['game'].find_one({'_id': ObjectId(event.get('game_id'))})
            if not game or str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            update_fields = {}
            if 'text_image' in data and data['text_image']:
                update_fields['text_image'] = data['text_image']
            if 'description' in data and data['description']:
                update_fields['description'] = data['description']
            if 'prompt_user_text' in data and data['prompt_user_text']:
                update_fields['prompt_user_text'] = data['prompt_user_text']

            if not update_fields:
                raise Exception("No valid fields to update")

            update_fields['updated_at'] = datetime.utcnow()
            update_fields['updated_by'] = user_id

            result = await self.db['event'].update_one(
                {'_id': ObjectId(event_id)},
                {'$set': update_fields}
            )

            if result.modified_count == 0:
                raise Exception("Failed to update event")

            updated_event = await self.db['event'].find_one({'_id': ObjectId(event_id)})
            return {
                '_id': str(updated_event['_id']),
                'text_image': updated_event.get('text_image'),
                'description': updated_event.get('description'),
                'prompt_user_text': updated_event.get('prompt_user_text'),
                'updated_at': updated_event['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating event: {str(e)}")
            raise
