import traceback
from io import BytesIO
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException, status, UploadFile

from core.database import db
from location.services_video import compress_video, upload_video_to_gcs


async def save_event_video_service(
        event_id: str,
        video_file: UploadFile,
        quality: str = "medium"
) -> dict:
    """
    Guarda un video de evento.

    Args:
        event_id: ID del evento
        video_file: Archivo de video a subir
        quality: Nivel de compresión del video

    Returns:
        Documento actualizado del evento
    """
    try:
        # Validar que el archivo sea un video
        if video_file.content_type not in ['video/mp4', 'video/quicktime', 'video/avi', 'video/x-msvideo']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se permiten videos (mp4, mov, avi)",
            )

        # Buscar el evento por ID
        event = await db["event"].find_one({
            "_id": ObjectId(event_id)
        })

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento no encontrado",
            )

        # Comprimir el video
        compressed_video = await compress_video(video_file, quality=quality)

        # Crear nombre único para el archivo
        file_name = f"event-videos/{event_id}/video-{uuid4()}.mp4"

        # Subir el video comprimido a GCS
        video_url = await upload_video_to_gcs(compressed_video, file_name)

        # Actualizar el documento del evento con el video
        updated_event = await db["event"].find_one_and_update(
            {"_id": ObjectId(event_id)},
            {
                "$set": {
                    "video_url": video_url,
                    "video_compressed_quality": quality,
                    "video_file_name": file_name,
                    "video_updated_at": __import__('datetime').datetime.utcnow()
                }
            },
            return_document=True
        )

        updated_event["_id"] = str(updated_event["_id"])

        return {
            "message": "Video uploaded successfully",
            "video_url": video_url,
            "event_id": updated_event["_id"],
            "quality": quality
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in save_event_video_service: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al guardar el video del evento",
        )


async def get_event_video_service(event_id: str) -> dict:
    """
    Obtiene la URL del video de un evento.

    Args:
        event_id: ID del evento

    Returns:
        Información del video
    """
    try:
        event = await db["event"].find_one({
            "_id": ObjectId(event_id)
        })

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento no encontrado",
            )

        if not event.get("video_url"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay video asociado a este evento",
            )

        return {
            "video_url": event.get("video_url"),
            "quality": event.get("video_compressed_quality"),
            "video_updated_at": event.get("video_updated_at"),
            "file_name": event.get("video_file_name")
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_event_video_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al obtener el video del evento",
        )


async def delete_event_video_service(event_id: str) -> dict:
    """
    Elimina el video de un evento.

    Args:
        event_id: ID del evento

    Returns:
        Mensaje de confirmación
    """
    try:
        event = await db["event"].find_one({
            "_id": ObjectId(event_id)
        })

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento no encontrado",
            )

        if not event.get("video_url"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay video asociado a este evento",
            )

        # Actualizar el documento del evento para eliminar el video
        await db["event"].find_one_and_update(
            {"_id": ObjectId(event_id)},
            {
                "$unset": {
                    "video_url": "",
                    "video_compressed_quality": "",
                    "video_file_name": "",
                    "video_updated_at": ""
                }
            }
        )

        # Opcionalmente, eliminar del storage (comentado por ahora)
        # await delete_video_from_gcs(event.get("video_file_name"))

        return {"message": "Video deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in delete_event_video_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al eliminar el video del evento",
        )

