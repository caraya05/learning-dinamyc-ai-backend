#!/usr/bin/env python3
"""
Script de ejemplo para subir videos y monitorear su progreso.

Uso:
    python monitor_video_upload.py --file video.mp4 --location-id loc_123 --state state_456
"""

import requests
import time
import argparse
import json
from pathlib import Path


class VideoUploadMonitor:
    def __init__(self, api_url: str, auth_token: str):
        self.api_url = api_url.rstrip('/')
        self.headers = {"Authorization": f"Bearer {auth_token}"}

    def upload_video(
        self,
        file_path: str,
        location_id: str,
        state: str,
        dialog_number: int = 1,
        quality: str = "medium"
    ) -> str:
        """
        Sube un video y retorna el task_id.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        print(f"📤 Subiendo video: {file_path.name}")

        with open(file_path, 'rb') as f:
            files = {'video_file': f}
            data = {
                'location_id': location_id,
                'state': state,
                'dialog_number': dialog_number,
                'quality': quality
            }

            response = requests.post(
                f"{self.api_url}/location/interaction-video/upload",
                files=files,
                data=data,
                headers=self.headers
            )

        if response.status_code != 202:
            raise Exception(f"Error en subida: {response.status_code} - {response.text}")

        result = response.json()
        task_id = result['task_id']
        print(f"✅ Video en cola para procesamiento")
        print(f"📋 Task ID: {task_id}")

        return task_id

    def check_status(self, task_id: str) -> dict:
        """
        Consulta el estado del procesamiento.
        """
        response = requests.get(
            f"{self.api_url}/location/interaction-video/status/{task_id}",
            headers=self.headers
        )

        if response.status_code != 200:
            raise Exception(f"Error obteniendo estado: {response.status_code}")

        return response.json()

    def monitor_upload(
        self,
        task_id: str,
        poll_interval: int = 5,
        max_wait: int = 600
    ) -> dict:
        """
        Monitorea el progreso de la carga.

        Args:
            task_id: ID de la tarea
            poll_interval: Segundos entre consultas
            max_wait: Máximo tiempo de espera en segundos
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"Excedido tiempo máximo de espera: {max_wait}s")

            status = self.check_status(task_id)

            # Mostrar progreso
            state = status['status']
            progress = status.get('progress', 0)
            message = status.get('message', '')

            print(f"\r⏳ [{progress:3d}%] {state:10s} - {message[:40]:40s}", end='', flush=True)

            # Verificar si terminó
            if state == 'SUCCESS':
                print()
                print("\n✨ Video procesado exitosamente!")
                result = status.get('result', {})
                print(f"   URL: {result.get('video_url', 'N/A')}")
                print(f"   State GLIC ID: {result.get('state_glic_id', 'N/A')}")
                return status

            elif state == 'FAILURE':
                print()
                print(f"\n❌ Error procesando video:")
                print(f"   {status.get('error', 'Error desconocido')}")
                return status

            elif state == 'RETRY':
                print()
                print(f"⚠️  Reintentando... ({status.get('retry_count', '?')} intento(s))")

            time.sleep(poll_interval)

    def upload_and_monitor(
        self,
        file_path: str,
        location_id: str,
        state: str,
        dialog_number: int = 1,
        quality: str = "medium",
        poll_interval: int = 5,
        max_wait: int = 600
    ) -> dict:
        """
        Sube un video y monitorea su progreso automáticamente.
        """
        # Subir
        task_id = self.upload_video(
            file_path=file_path,
            location_id=location_id,
            state=state,
            dialog_number=dialog_number,
            quality=quality
        )

        print()

        # Monitorear
        return self.monitor_upload(
            task_id=task_id,
            poll_interval=poll_interval,
            max_wait=max_wait
        )


def main():
    parser = argparse.ArgumentParser(
        description="Monitorea la subida y procesamiento de videos"
    )
    parser.add_argument(
        "--file", "-f",
        required=True,
        help="Ruta del archivo de video"
    )
    parser.add_argument(
        "--location-id", "-l",
        required=True,
        help="ID de la location"
    )
    parser.add_argument(
        "--state", "-s",
        required=True,
        help="ID del state/state_game"
    )
    parser.add_argument(
        "--dialog-number", "-d",
        type=int,
        default=1,
        help="Número del diálogo (default: 1)"
    )
    parser.add_argument(
        "--quality", "-q",
        choices=["low", "medium", "high"],
        default="medium",
        help="Calidad de compresión (default: medium)"
    )
    parser.add_argument(
        "--api-url", "-u",
        default="http://localhost:8000",
        help="URL base de la API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--token", "-t",
        required=True,
        help="Token JWT para autenticación"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Intervalo entre consultas en segundos (default: 5)"
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=600,
        help="Máximo tiempo de espera en segundos (default: 600)"
    )
    parser.add_argument(
        "--task-id",
        help="Si se proporciona, solo monitorea un task_id existente sin subir"
    )

    args = parser.parse_args()

    monitor = VideoUploadMonitor(args.api_url, args.token)

    try:
        if args.task_id:
            # Solo monitorear
            print(f"📋 Monitoreando task: {args.task_id}")
            result = monitor.monitor_upload(
                task_id=args.task_id,
                poll_interval=args.poll_interval,
                max_wait=args.max_wait
            )
        else:
            # Subir y monitorear
            result = monitor.upload_and_monitor(
                file_path=args.file,
                location_id=args.location_id,
                state=args.state,
                dialog_number=args.dialog_number,
                quality=args.quality,
                poll_interval=args.poll_interval,
                max_wait=args.max_wait
            )

        print("\n" + "="*50)
        print("Resultado Final:")
        print(json.dumps(result, indent=2, default=str))

    except KeyboardInterrupt:
        print("\n⚠️  Operación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()

