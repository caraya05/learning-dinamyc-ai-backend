"""
Tarea para monitorear y actualizar el estado de tareas asincrónicas después de que
las tareas `create_game_provisional_2` y `async_continue_create_game_provisional_2`
terminen sus ejecuciones.

Extrae la lógica del WebSocket de búsqueda y actualización de tareas.
"""

import traceback
import logging
import asyncio
import nest_asyncio
from datetime import datetime, timedelta
from bson import ObjectId
from celery.result import AsyncResult
from celery import current_app as celery

from core.database import db
from task.services import get_task_pending_service, update_task_service
from celery import shared_task

# Permitir event loops anidados en tareas Celery
nest_asyncio.apply()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def monitor_and_update_tasks_for_game(
    user_id: str,
    game_provisional_id: str,
    max_attempts: int = 60,  # 60 intentos * 10 segundos = 10 minutos
    attempt_interval: int = 10  # segundos
) -> dict:
    """
    Monitorea y actualiza todas las tareas asociadas a un juego provisional.

    Esta función busca todas las tareas pendientes del usuario, obtiene su estado
    de Celery, y actualiza su estado en la BD hasta que todas se completen.

    Args:
        user_id (str): ID del usuario propietario de las tareas
        game_provisional_id (str): ID del juego provisional
        max_attempts (int): Número máximo de intentos antes de timeout
        attempt_interval (int): Segundos entre intentos

    Returns:
        dict: Resumen de tareas procesadas con estadísticas
    """
    try:
        import asyncio

        tasks_summary = {
            "completed": [],
            "failed": [],
            "timeout": [],
            "total_processed": 0,
            "game_provisional_id": game_provisional_id,
            "user_id": user_id
        }

        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            logger.info(f"[Attempt {attempt}/{max_attempts}] Buscando tareas pendientes...")

            # Obtener todas las tareas pendientes del usuario
            tasks_db = await get_task_pending_service(user_id=user_id, is_list=True)

            if not tasks_db:
                logger.info(f"No hay tareas pendientes para el usuario {user_id}")
                break

            all_completed = True

            for task_db in tasks_db:
                task_id = str(task_db["_id"])
                element_id = str(task_db["element_id"])
                element_type = task_db["element_type"]
                process_name = task_db.get("process", "unknown")
                celery_task_id = task_db.get("task_id")
                created_at = task_db.get("created_at")

                logger.info(f"Procesando tarea {task_id}: {process_name} (elemento: {element_id})")

                # Validar timeout de 6 minutos
                if created_at:
                    time_elapsed = datetime.utcnow() - created_at
                    if time_elapsed > timedelta(minutes=6):
                        logger.warning(f"Tarea {task_id} excedió timeout de 6 minutos, tiempo de dificultad: {time_elapsed}")

                        await update_task_service(
                            _id=task_id,
                            _status="failed",
                            _was_notified=True,
                            _message="Task timeout after 6 minutes"
                        )

                        tasks_summary["timeout"].append({
                            "task_id": task_id,
                            "element_id": element_id,
                            "element_type": element_type,
                            "process": process_name
                        })

                        continue

                # Si hay task_id de Celery, verificar estado
                if celery_task_id:
                    try:
                        task_celery = AsyncResult(celery_task_id, app=celery)
                        celery_state = task_celery.state
                        celery_result = task_celery.result

                        logger.info(f"Estado Celery para {task_id}: {celery_state}")

                        if celery_state == "SUCCESS":
                            # Verificar si hay error en el resultado
                            if celery_result and "Error" in str(celery_result):
                                logger.error(f"Tarea {task_id} falló con error: {celery_result}")

                                await update_task_service(
                                    _id=task_id,
                                    _status="failed",
                                    _was_notified=True,
                                    _message=str(celery_result)
                                )

                                tasks_summary["failed"].append({
                                    "task_id": task_id,
                                    "element_id": element_id,
                                    "element_type": element_type,
                                    "process": process_name,
                                    "error": str(celery_result)
                                })
                            else:
                                logger.info(f"Tarea {task_id} completada exitosamente")

                                await update_task_service(
                                    _id=task_id,
                                    _status="completed",
                                    _was_notified=True,
                                    _message="Task completed successfully"
                                )

                                tasks_summary["completed"].append({
                                    "task_id": task_id,
                                    "element_id": element_id,
                                    "element_type": element_type,
                                    "process": process_name,
                                    "result": str(celery_result) if celery_result else "Success"
                                })

                        elif celery_state == "FAILURE":
                            logger.error(f"Tarea {task_id} falló en Celery: {celery_result}")

                            await update_task_service(
                                _id=task_id,
                                _status="failed",
                                _was_notified=True,
                                _message=str(celery_result)
                            )

                            tasks_summary["failed"].append({
                                "task_id": task_id,
                                "element_id": element_id,
                                "element_type": element_type,
                                "process": process_name,
                                "error": str(celery_result)
                            })

                        else:
                            # Estado aún no terminal (PENDING, STARTED, etc.)
                            logger.info(f"Tarea {task_id} aún en progreso (estado: {celery_state})")
                            all_completed = False

                    except Exception as e:
                        logger.error(f"Error verificando estado de Celery para {task_id}: {e}")
                        all_completed = False

                else:
                    # Sin task_id de Celery, verificar estado en BD
                    task_status = task_db.get("status")

                    if task_status == "completed":
                        logger.info(f"Tarea {task_id} completada (en BD)")

                        await update_task_service(
                            _id=task_id,
                            _status="completed",
                            _was_notified=True
                        )

                        tasks_summary["completed"].append({
                            "task_id": task_id,
                            "element_id": element_id,
                            "element_type": element_type,
                            "process": process_name
                        })

                    elif task_status == "failed":
                        logger.warning(f"Tarea {task_id} falló (en BD)")

                        await update_task_service(
                            _id=task_id,
                            _status="failed",
                            _was_notified=True
                        )

                        tasks_summary["failed"].append({
                            "task_id": task_id,
                            "element_id": element_id,
                            "element_type": element_type,
                            "process": process_name,
                            "error": task_db.get("message", "Unknown error")
                        })

                    else:
                        logger.info(f"Tarea {task_id} aún pendiente (en BD)")
                        all_completed = False

            tasks_summary["total_processed"] = len(tasks_db)

            if all_completed:
                logger.info("Todas las tareas han sido procesadas")
                break

            # Esperar antes del próximo intento
            await asyncio.sleep(attempt_interval)

        logger.info(f"Resumen final: {tasks_summary}")
        return tasks_summary

    except Exception as e:
        logger.error(f"Error en monitor_and_update_tasks_for_game: {traceback.format_exc()}")
        return {
            "error": str(e),
            "game_provisional_id": game_provisional_id,
            "user_id": user_id
        }


# Función que registra la tarea en Celery (evita importación circular)
def create_monitor_task():
    """
    Crea la tarea de Celery dinámicamente para evitar importación circular.
    """

    @shared_task(name='monitor_and_update_game_tasks')
    def monitor_and_update_game_tasks_task(
        user_id: str,
        game_provisional_id: str,
        max_attempts: int = 60,
        attempt_interval: int = 10
    ):
        """
        Tarea de Celery que ejecuta el monitoreo y actualización de tareas.
        Se puede lanzar después de que `create_game_provisional_2` y
        `async_continue_create_game_provisional_2` terminen.

        Uso:
            # Como tarea encadenada (recomendado con Celery chains)
            from celery import chain
            from game.tasks_provisional_2 import create_game_provisional_2, async_continue_create_game_provisional_2

            chain(
                create_game_provisional_2.s(game_id, user_id),
                async_continue_create_game_provisional_2.s(game_id, user_id),
                monitor_and_update_game_tasks_task.s(user_id, game_id)
            ).apply_async()

        Args:
            user_id (str): ID del usuario
            game_provisional_id (str): ID del juego provisional
            max_attempts (int): Máximo número de intentos
            attempt_interval (int): Segundos entre intentos
        """
        try:
            # Obtener o crear event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Ejecutar la función async
            result = loop.run_until_complete(
                monitor_and_update_tasks_for_game(
                    user_id=user_id,
                    game_provisional_id=game_provisional_id,
                    max_attempts=max_attempts,
                    attempt_interval=attempt_interval
                )
            )

            return result

        except Exception as e:
            logger.error(f"Error en celery task monitor_and_update_game_tasks: {traceback.format_exc()}")
            return {
                "error": str(e),
                "game_provisional_id": game_provisional_id,
                "user_id": user_id
            }

    return monitor_and_update_game_tasks_task


# Crear la tarea al importar el módulo
monitor_and_update_game_tasks_task = create_monitor_task()



