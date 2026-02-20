"""
Tareas opcionales para procesar imágenes de referencia de forma asíncrona
Si quieres procesar las categorías de imágenes en background después de crear el juego
"""

from celery_worker import celery
from core.database import db
from game.reference_image_service import categorize_reference_images
from bson import ObjectId
from datetime import datetime
import pytz


@celery.task(bind=True, max_retries=3)
async def categorize_reference_images_task(self, game_id: str, image_urls: list, prompt_user: str, template_type: str):
    """
    Tarea asíncrona para categorizar imágenes de referencia usando GPT-4 Vision.

    Args:
        game_id: ID del juego provisional
        image_urls: Lista de URLs de imágenes cargadas
        prompt_user: Prompt del usuario
        template_type: Tipo de plantilla
    """
    try:
        categorized_images = await categorize_reference_images(
            image_urls=image_urls,
            prompt_user=prompt_user
        )

        # Actualizar el documento con las imágenes categorizadas
        await db["game_provisional"].update_one(
            {"_id": ObjectId(game_id)},
            {
                "$set": {
                    "reference_images": categorized_images,
                    "updated_at": datetime.now(pytz.utc)
                }
            }
        )

        return {
            "status": "success",
            "game_id": game_id,
            "categorized_images": categorized_images
        }

    except Exception as e:
        print(f"Error in categorize_reference_images_task: {str(e)}")
        # Reintentar si falla
        raise self.retry(exc=e, countdown=60)

