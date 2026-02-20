import traceback
import tempfile
import os
import subprocess
from io import BytesIO
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException, status, UploadFile
from google.cloud import storage

from core.database import db


async def get_video_info(video_path: str) -> dict:
    """
    Obtiene información del video usando ffprobe.

    Args:
        video_path: Ruta del archivo de video

    Returns:
        Diccionario con información del video
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_format',
            '-show_streams',
            '-of', 'json',
            video_path
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )

        if result.returncode == 0:
            import json
            info = json.loads(result.stdout.decode('utf-8'))

            # Log información importante del video
            if 'streams' in info:
                for stream in info['streams']:
                    if stream.get('codec_type') == 'video':
                        print(f"📹 Video codec: {stream.get('codec_name')} (profile: {stream.get('profile')})")
                        print(f"   Resolution: {stream.get('width')}x{stream.get('height')}")
                        print(f"   Level: {stream.get('level')}")
                        print(f"   Is AVC: {stream.get('is_avc')}")
                        print(f"   Has B-frames: {stream.get('has_b_frames')}")
                        print(f"   Duration: {stream.get('duration', 'unknown')}s")
                        print(f"   Bitrate: {stream.get('bit_rate', 'unknown')} bps")

            return info
        else:
            error = result.stderr.decode('utf-8', errors='ignore')
            print(f"ffprobe error: {error}")
            return {}
    except Exception as e:
        print(f"Error getting video info: {e}")
        return {}


async def compress_video(video_file: UploadFile, quality: str = "medium") -> BytesIO:
    """
    Comprime un video usando ffmpeg.

    Args:
        video_file: Archivo de video a comprimir
        quality: Nivel de compresión (low, medium, high)

    Returns:
        BytesIO con el video comprimido
    """
    tmp_input_path = None
    tmp_output_path = None

    try:
        # Crear archivo temporal de entrada
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_input:
            video_content = await video_file.read()
            tmp_input.write(video_content)
            tmp_input_path = tmp_input.name

        # Obtener información del video
        video_info = await get_video_info(tmp_input_path)
        print(f"Input video info: {video_info}")

        # Crear archivo temporal de salida
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_output:
            tmp_output_path = tmp_output.name

        # Configurar parámetros de compresión según la calidad
        if quality == "low":
            crf = 28  # Lower quality, smaller file
        elif quality == "medium":
            crf = 23  # Medium quality
        else:  # high
            crf = 18  # Higher quality, larger file

        # Comando ffmpeg - versión robusta para manejar videos problemáticos
        # Intento 1: Comando directo sin bitstream filters (mejor compatibilidad)
        cmd = [
            'ffmpeg',
            '-loglevel', 'error',
            '-i', tmp_input_path,
            '-c:v', 'libx264',
            '-vf', 'scale=1280:-2',
            '-crf', str(crf),
            '-preset', 'faster',  # Preset más rápido para mejor compatibilidad
            '-x264-params', 'nal-hrd=cbr',  # Parámetros para mejor compatibilidad
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',
            tmp_output_path
        ]

        print(f"Running ffmpeg command (attempt 1): {' '.join(cmd)}")

        # Ejecutar ffmpeg con retry logic
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )

        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            print(f"FFmpeg error (attempt 1): {error_msg}")

            # Retry 2: Sin parámetros específicos de x264
            print("Retrying with simpler x264 parameters...")
            cmd_simple = [
                'ffmpeg',
                '-loglevel', 'error',
                '-i', tmp_input_path,
                '-c:v', 'libx264',
                '-vf', 'scale=1280:-2',
                '-crf', str(crf),
                '-preset', 'faster',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',
                tmp_output_path
            ]

            result = subprocess.run(
                cmd_simple,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300
            )

            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                print(f"FFmpeg error (attempt 2): {error_msg}")

                # Retry 3: Re-encode con libx265 (H.265) como alternativa
                print("Retrying with H.265 codec...")
                cmd_h265 = [
                    'ffmpeg',
                    '-loglevel', 'error',
                    '-i', tmp_input_path,
                    '-c:v', 'libx265',
                    '-vf', 'scale=1280:-2',
                    '-crf', str(crf),
                    '-preset', 'faster',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-y',
                    tmp_output_path
                ]

                result = subprocess.run(
                    cmd_h265,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=300
                )

                if result.returncode != 0:
                    error_msg = result.stderr.decode('utf-8', errors='ignore')
                    print(f"FFmpeg error (attempt 3): {error_msg}")

                    # Último intento: usar copy del video sin re-encoding
                    print("Retrying with video copy (no re-encoding)...")
                    cmd_copy = [
                        'ffmpeg',
                        '-loglevel', 'error',
                        '-i', tmp_input_path,
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        '-b:a', '128k',
                        '-movflags', '+faststart',
                        '-y',
                        tmp_output_path
                    ]

                    result = subprocess.run(
                        cmd_copy,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=300
                    )

                    if result.returncode != 0:
                        error_msg = result.stderr.decode('utf-8', errors='ignore')
                        print(f"FFmpeg error (attempt 4 - final): {error_msg}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Error processing video after all retries: {error_msg[:200]}",
                        )

        # Leer el archivo comprimido
        if not os.path.exists(tmp_output_path):
            print(f"ERROR: Output file does not exist at {tmp_output_path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating compressed video file",
            )

        # Validar que el archivo no esté vacío y tenga un tamaño razonable
        file_size = os.path.getsize(tmp_output_path)
        print(f"Output file size: {file_size} bytes")

        if file_size < 5000:  # Menos de 5KB probablemente sea un error
            print(f"ERROR: Output file too small ({file_size} bytes). FFmpeg conversion likely failed.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Compressed video file is too small. FFmpeg conversion may have failed.",
            )

        # Validar la integridad del archivo MP4
        try:
            with open(tmp_output_path, 'rb') as f:
                header = f.read(32)
                # Buscar 'ftyp' en los primeros 32 bytes
                if b'ftyp' in header:
                    print("✓ Valid MP4 header detected")
                else:
                    # Leer más bytes para buscar 'ftyp'
                    f.seek(0)
                    content = f.read(512)
                    if b'ftyp' in content:
                        print("✓ Valid MP4 header detected (at offset)")
                    else:
                        print(f"⚠ Warning: Standard MP4 header not found. Header bytes: {header[:16].hex()}")
        except Exception as e:
            print(f"Warning: Could not validate MP4 header: {e}")

        with open(tmp_output_path, 'rb') as f:
            compressed_data = f.read()

        print(f"✓ Successfully read {len(compressed_data)} bytes from output file")

        # Convertir a BytesIO
        compressed_video = BytesIO(compressed_data)
        compressed_video.seek(0)

        return compressed_video

    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video compression timed out (> 5 minutes)",
        )
    except Exception as e:
        print(f"Error compressing video: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error compressing video",
        )
    finally:
        # Limpiar archivos temporales
        for path in [tmp_input_path, tmp_output_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Warning: Could not delete temp file {path}: {e}")



async def upload_video_to_gcs(
        video_file: BytesIO,
        file_name: str,
        name_bucket: str = 'qwestar'
) -> str:
    """
    Sube un video a Google Cloud Storage.

    Args:
        video_file: BytesIO con el contenido del video
        file_name: Nombre del archivo en GCS
        name_bucket: Nombre del bucket de GCS

    Returns:
        URL pública del archivo subido
    """
    try:
        storage_client = storage.Client.from_service_account_json("credentials.json")
        bucket = storage_client.bucket(name_bucket)
        blob = bucket.blob(file_name)

        video_file.seek(0)
        blob.upload_from_file(video_file, content_type='video/mp4')

        return f"https://storage.googleapis.com/{name_bucket}/{file_name}"
    except Exception as e:
        print(f"Error uploading video to GCS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al subir el video",
        )


async def save_interaction_video_service(
        location_id: str,
        state: str,
        dialog_number: int,
        video_file: UploadFile,
        quality: str = "medium"
) -> dict:
    """
    Guarda un video de interacción en una location del state_glic.

    Args:
        location_id: ID de la location
        state: ID del state_game
        dialog_number: Número del diálogo
        video_file: Archivo de video a subir
        quality: Nivel de compresión del video

    Returns:
        Documento actualizado del state_glic
    """
    try:
        # Validar que el archivo sea un video
        if video_file.content_type not in ['video/mp4', 'video/quicktime', 'video/avi', 'video/x-msvideo']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se permiten videos (mp4, mov, avi)",
            )

        # Comprimir el video
        compressed_video = await compress_video(video_file, quality=quality)

        # Crear nombre único para el archivo
        file_name = f"location-interactions/{location_id}/state-{state}/dialog-{dialog_number}-{uuid4()}.mp4"

        # Subir el video comprimido a GCS
        video_url = await upload_video_to_gcs(compressed_video, file_name)

        # Buscar o crear el state_glic para esta location
        state_glic = await db["state_glic"].find_one({
            "element_id": location_id,
            "state": state
        })

        if not state_glic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="State GLIC not found for this location",
            )

        # Actualizar el documento state_glic con el video
        if "data" not in state_glic:
            state_glic["data"] = {}

        if "interaction_videos" not in state_glic["data"]:
            state_glic["data"]["interaction_videos"] = {}

        # Guardar el video en la estructura de datos
        state_glic["data"]["interaction_videos"] = {
            "url": video_url,
            "dialog_number": dialog_number,
            "compressed_quality": quality,
            "created_at": __import__('datetime').datetime.utcnow(),
            "file_name": file_name
        }

        # Actualizar en la base de datos
        updated_state = await db["state_glic"].find_one_and_update(
            {"_id": ObjectId(state_glic["_id"])},
            {"$set": {"data": state_glic["data"]}},
            return_document=True
        )

        updated_state["_id"] = str(updated_state["_id"])

        return {
            "message": "Video uploaded successfully",
            "video_url": video_url,
            "state_glic_id": updated_state["_id"],
            "dialog_number": dialog_number
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in save_interaction_video_service: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al guardar el video de interacción",
        )


async def get_interaction_video_service(
        location_id: str,
        state: str,
        dialog_number: int
) -> dict:
    """
    Obtiene la URL de un video de interacción.

    Args:
        location_id: ID de la location
        state: ID del state_game
        dialog_number: Número del diálogo

    Returns:
        Información del video
    """
    try:
        state_glic = await db["state_glic"].find_one({
            "element_id": location_id,
            "state": state
        })

        if not state_glic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="State GLIC not found",
            )

        video_data = state_glic.get("data", {}).get("interaction_videos", {}).get(str(dialog_number))

        if not video_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found for this dialog number",
            )

        return video_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_interaction_video_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al obtener el video",
        )


async def delete_interaction_video_service(
        location_id: str,
        state: str,
        dialog_number: int
) -> dict:
    """
    Elimina un video de interacción.

    Args:
        location_id: ID de la location
        state: ID del state_game
        dialog_number: Número del diálogo

    Returns:
        Mensaje de confirmación
    """
    try:
        state_glic = await db["state_glic"].find_one({
            "element_id": location_id,
            "state": state,
            "type_element": "location"
        })

        if not state_glic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="State GLIC not found",
            )

        # Verificar que existe data
        if "data" not in state_glic:
            state_glic["data"] = {}

        # Eliminar el video de interaction_videos
        if "interaction_videos" in state_glic["data"]:
            # interaction_videos es un objeto simple con propiedades
            # No es un diccionario con keys como "2", "3", etc.
            # Eliminamos todos los campos
            state_glic["data"]["interaction_videos"] = None

            # Actualizar en DB usando replace_one
            result = await db["state_glic"].replace_one(
                {"_id": ObjectId(state_glic["_id"])},
                state_glic
            )

            if result.modified_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to delete video",
                )

            return {"message": "Video deleted successfully"}

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found for this dialog number",
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in delete_interaction_video_service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al eliminar el video",
        )

