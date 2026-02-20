"""
Servicios para actualización de textos de juegos.
"""

import logging
from datetime import datetime
from bson import ObjectId
from core.database import db

logger = logging.getLogger(__name__)


class GameTextUpdateService:
    """Servicio para actualizar textos de juegos"""

    def __init__(self, db_instance=None):
        self.db = db_instance or db
        self.logger = logging.getLogger(__name__)

    def _is_valid_objectid(self, value: str) -> bool:
        try:
            ObjectId(value)
            return True
        except:
            return False

    async def update_game_title(self, game_id: str, title: str, user_id: str) -> dict:
        """Actualiza el título del juego"""
        try:
            if not self._is_valid_objectid(game_id):
                raise Exception("Invalid game ID format")

            game = await self.db['game'].find_one({'_id': ObjectId(game_id)})
            if not game:
                raise Exception("Game not found")

            if str(game.get('created_by')) != user_id:
                raise Exception("Permission denied")

            result = await self.db['game'].update_one(
                {'_id': ObjectId(game_id)},
                {
                    '$set': {
                        'title': title,
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                }
            )

            if result.modified_count == 0:
                raise Exception("Failed to update game title")

            updated_game = await self.db['game'].find_one({'_id': ObjectId(game_id)})
            return {
                '_id': str(updated_game['_id']),
                'title': updated_game['title'],
                'updated_at': updated_game['updated_at']
            }

        except Exception as e:
            self.logger.error(f"Error updating game title: {str(e)}")
            raise
