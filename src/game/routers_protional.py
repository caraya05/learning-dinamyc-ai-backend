import asyncio
import base64
from io import BytesIO
from fastapi import Depends

import traceback
from datetime import datetime
from datetime import timedelta
from uuid import uuid4

import pytz
from bson import ObjectId
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status
from fastapi import Request
from fastapi.params import Form
from fastapi import UploadFile
from fastapi import File
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from core.database import db
from fastapi.security import HTTPAuthorizationCredentials
from auth.auth import auth
from auth.utils import auth_schema
from game.tasks_provisional_2 import create_game_structure, create_intermediate_events
from task.services import create_task_service

from utils import upload_file, send_email, upload_image

from slowapi.util import get_remote_address
from slowapi import Limiter

from celery.result import AsyncResult
from celery_worker import create_game_provisional_task, create_game_provisional_task_2, \
    generate_scene_interactions_task, celery, continue_create_game_provisional_2

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/game-provisional", tags=["Game Provisional"])
router_ws = APIRouter(prefix="/ws/game-provisional", tags=["WebSocket Game Provisional"])


# Clase para gestionar las conexiones WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append(websocket)

    def disconnect(self, websocket: WebSocket, game_id: str):
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                self.active_connections[game_id].remove(websocket)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as e:
            # Si hay error al enviar, desconectar el websocket
            print(f"Error enviando mensaje WebSocket: {str(e)}")
            # Buscar y remover esta conexión de todas las listas activas
            for game_id, connections in list(self.active_connections.items()):
                if websocket in connections:
                    connections.remove(websocket)
                    if not connections:
                        del self.active_connections[game_id]
                    break

    async def broadcast(self, message: dict, game_id: str):
        if game_id in self.active_connections:
            # Crear una copia de la lista para evitar modificaciones durante la iteración
            connections = self.active_connections[game_id].copy()
            for connection in connections:
                await self.send_personal_message(message, connection)


# Creamos una instancia del gestor de conexiones
manager = ConnectionManager()


@router.post("/", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute", error_message="Intentalo de nuevo más tarde")
async def create_game(
        request: Request,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        file: UploadFile = File(None),
        prompt_user: str = Form(...),
        template_type: str = Form(...),
):
    """
    This endpoint creates a new game.

    It requires the user to be authenticated and provides the following parameters:
    - `file`: An optional file upload.
    - `prompt_user`: A string representing the user's prompt.
    - `template_type`: A string representing the type of template to use.
    """

    try:

        url_file = upload_file(file=file)

        game_provisional_db = await db["game_provisional"].insert_one(
            {
                "prompt_user": prompt_user,
                "type_template": template_type,
                "created_at": datetime.now(pytz.utc),
                "updated_at": datetime.now(pytz.utc),
                "created_by": str(user["_id"]),
                "updated_by": str(user["_id"]),
                "state": "script_create",
                "num_scenes": 0,
                "scene_interactions": [],
                "file": url_file,
                "image": None,
                "title": None,
                "script": None,
                "user_name": None,
                "user_email": None,
                "level_process": 1,
            }
        )

        if not game_provisional_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating game provisional",
            )

        game_provisional_db = await db["game_provisional"].find_one(
            {"_id": game_provisional_db.inserted_id}
        )

        # tasks = create_game_provisional_task.delay(str(game_provisional_db["_id"]))
        tasks = create_game_provisional_task_2.delay(str(game_provisional_db["_id"]), str(user["_id"]))

        task_db = await create_task_service(
            _task_id=tasks.id,
            _user_id=str(user["_id"]),
            _task_data={},
            _element_id=str(game_provisional_db["_id"]),
            _element_type="game_provisional",
            _process="game_provisional_creation",
        )

        return {
            "_id": str(game_provisional_db["_id"]),
            "prompt_user": prompt_user,
            "template_type": template_type,
            "created_at": game_provisional_db["created_at"],
            "updated_at": game_provisional_db["updated_at"],
            "created_by": str(user["_id"]),
            "updated_by": str(user["_id"]),
            "state": "script_create",
            "num_scenes": 0,
            "scene_interactions": [],
            "task_id": str(tasks.id),
            "file": url_file,
            "image": None,
            "title": None,
            "script": None,
            "user_name": None,
            "user_email": None,
            "progress": 0,
            "progress_text": "Game provisional created successfully, waiting for processing.",
            "game_id": None,
            "category": None,
            "level_process": 1,
        }
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the game provisional: {str(e)}",
        )


@router.get("/{id_game_provisional}", status_code=status.HTTP_200_OK)
@limiter.limit("20/minute", error_message="Intentalo de nuevo más tarde")
async def get_game_provisional(
        request: Request,
        id_game_provisional: str,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),

):
    """
    This endpoint retrieves a game provisional by its ID.

    It requires the user to be authenticated.
    """
    if not ObjectId.is_valid(id_game_provisional):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid game provisional ID",
        )

    game_provisional_db = await db["game_provisional"].find_one(
        {"_id": ObjectId(id_game_provisional)}
    )

    if not game_provisional_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game provisional not found",
        )

    events_plus = create_intermediate_events(game_provisional_db.get("interactions", []))

    # Normalizar y combinar events_plus y events; mover 'scene_start' al inicio si existe
    combined_events = []
    for e in game_provisional_db.get("events", []):
        combined_events.append(e.dict() if hasattr(e, "dict") else e)
    for e in events_plus:
        combined_events.append(e.dict() if hasattr(e, "dict") else e)

    return {
        "_id": str(game_provisional_db["_id"]),
        "prompt_user": game_provisional_db["prompt_user"],
        "template_type": game_provisional_db["type_template"],
        "created_at": game_provisional_db["created_at"],
        "updated_at": game_provisional_db["updated_at"],
        "file": game_provisional_db["file"],
        "image": game_provisional_db["image"],
        "title": game_provisional_db["title"],
        "script": game_provisional_db["script"],
        "progress": game_provisional_db.get("progress", 0),
        "progress_text": game_provisional_db.get("progress_text", ""),
        "state": game_provisional_db["state"],
        "user_name": game_provisional_db.get("user_name"),
        "user_email": game_provisional_db.get("user_email"),
        "category": game_provisional_db.get("category"),
        "characters": game_provisional_db.get("characters", []),
        "locations": game_provisional_db.get("locations", []),
        "events": combined_events,
        "interactions": game_provisional_db.get("interactions", []),
        "game_structure": create_game_structure(game_provisional_db.get("locations", []),game_provisional_db.get("events", []),game_provisional_db.get("interactions", []), game_provisional_db.get("characters", [])),
        "level_process": game_provisional_db.get("level_process", 1),
    }


@router.patch("/{id_game_provisional}", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute", error_message="Intentalo de nuevo más tarde")
async def update_game_provisional(
        request: Request,
        id_game_provisional: str,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
        image: str = Form(None),
        script: str = Form(None),
        title: str = Form(None),
        user_name: str = Form(None),
        user_email: str = Form(None),
        is_draft: bool = Form(False),
):
    """
    This endpoint updates a game provisional by its ID.

    It requires the user to be authenticated and provides the following parameters:
    - `file`: An optional file upload.
    - `prompt_user`: A string representing the user's prompt.
    - `time_game`: A string representing the time for the game.
    """

    if not ObjectId.is_valid(id_game_provisional):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid game provisional ID",
        )

    update_fields = {
        "updated_at": datetime.now(pytz.utc),
    }

    if script is not None:
        update_fields["script"] = script
    if title is not None:
        update_fields["title"] = title
    if image is not None and not image.startswith("https://"):
        # Asegurar el relleno correcto para la cadena Base64
        missing_padding = len(image) % 4
        if missing_padding:
            image += "=" * (4 - missing_padding)

        # Decodificar la imagen Base64
        try:
            image_data = base64.b64decode(image)
            img_byte_arr = BytesIO(image_data)
        except Exception as e:
            print(f"Error decoding Base64 image: {e}")

        # Subir la imagen
        update_fields["image"] = upload_image(
            img_byte_arr=img_byte_arr,
            file_name=f"game-provisional/{uuid4()}.jpg",
            size=(512, 896)
        )
    if user_name is not None:
        update_fields["user_name"] = user_name
    if user_email is not None:
        update_fields["user_email"] = user_email

    await db["game_provisional"].update_one(
        {"_id": ObjectId(id_game_provisional)},
        {"$set": update_fields}
    )

    game_provisional_db = await db["game_provisional"].find_one(
        {"_id": ObjectId(id_game_provisional)}
    )

    if not game_provisional_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game provisional not found",
        )

    if not is_draft:
        update_fields["state"] = "game_create"
        continue_create_game_provisional_2.delay(id_game_provisional=id_game_provisional, user_id=str(user["_id"]))
        game_provisional_db["state"] = "game_create"

    else:
        update_fields["state"] = "draft"
        game_provisional_db["state"] = "draft"

    update_fields["progress"] = 0
    update_fields["progress_text"] = "Game provisional is ready, waiting for processing."
    update_fields["level_process"] = 2

    await db["game_provisional"].update_one(
        {"_id": ObjectId(id_game_provisional)},
        {"$set": update_fields}
    )

    return {
        "_id": str(game_provisional_db["_id"]),
        "prompt_user": game_provisional_db["prompt_user"],
        "template_type": game_provisional_db["type_template"],
        "created_at": game_provisional_db["created_at"],
        "updated_at": game_provisional_db["updated_at"],
        "image": game_provisional_db["image"],
        "title": game_provisional_db["title"],
        "script": game_provisional_db["script"],
        "state": game_provisional_db["state"],
        "level_process": game_provisional_db.get("level_process", 1),
    }


@router.get("/in-progress/", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute", error_message="Intentalo de nuevo más tarde")
async def get_games_in_progress(request: Request, user: dict = Depends(auth),
                                Token: HTTPAuthorizationCredentials = Depends(auth_schema)):
    """
    Devuelve un listado de juegos provisionales en progreso (no draft, sin game_id, y no más de 2 días de antigüedad).
    """
    now = datetime.now(pytz.utc)
    two_days_ago = now - timedelta(days=2)
    query = {
        "state": {"$in": ["script_create", "game_create"]},
        "created_by": str(user["_id"]),
        "created_at": {"$gte": two_days_ago}
    }
    games_cursor = await db["game_provisional"].find(query).to_list(None)
    games = []
    for game in games_cursor:
        games.append({
            "_id": str(game["_id"]),
            "title": game.get("title"),
            "state": game.get("state"),
            "created_at": game.get("created_at"),
            "updated_at": game.get("updated_at"),
            "progress": game.get("progress", 0),
            "progress_text": game.get("progress_text", ""),
            "game_id": game.get("game_id"),
            "user_name": game.get("user_name"),
            "user_email": game.get("user_email"),
        })
    return {"games_in_progress": games}


@router_ws.websocket("/{game_id}")
async def websocket_game_provisional(websocket: WebSocket, game_id: str, token: str = None):
    """
    Endpoint WebSocket para monitorear el progreso de las tareas de un juego provisional.

    Permite al cliente conectarse y recibir actualizaciones en tiempo real sobre el estado
    de las tareas relacionadas con la creación y procesamiento del juego provisional.

    Args:
        websocket: La conexión WebSocket establecida con el cliente
        game_id: ID del juego provisional a monitorear
        token: Token de autenticación (query parameter)
    """
    try:
        if not ObjectId.is_valid(game_id):
            await websocket.close(code=1008, reason="ID de juego inválido")
            return

        # Verificar autenticación si se proporciona token
        user = None

        game_provisional_db = await db["game_provisional"].find_one(
            {"_id": ObjectId(game_id)}
        )

        if not game_provisional_db:
            await websocket.close(code=1008, reason="Juego provisional no encontrado")
            return

        # Verificar que el usuario tenga permisos para acceder a este juego
        if user and str(game_provisional_db.get("created_by")) != str(user.get("_id")):
            await websocket.close(code=1008, reason="No tienes permisos para acceder a este juego")
            return

        await manager.connect(websocket, game_id)

        # Mensaje inicial de conexión establecida
        await manager.send_personal_message(
            {"status": "connected", "message": "Conexión establecida", "game_id": game_id},
            websocket
        )

        # Bucle principal para monitorear el progreso de las tareas
        try:
            while True:
                # Esperar mensajes del cliente (pueden ser solicitudes de estado o comandos)
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                    if data.get("action") == "check_status":
                        # El cliente solicita explícitamente un estado actualizado
                        await send_task_status_update(websocket, game_id)
                except asyncio.TimeoutError:
                    # No se recibieron mensajes, seguimos con la verificación periódica
                    pass

                # Verificar y enviar actualizaciones de estado periódicamente
                await send_task_status_update(websocket, game_id)

                # Esperar antes de la próxima verificación para evitar sobrecarga
                await asyncio.sleep(2.0)

        except WebSocketDisconnect:
            manager.disconnect(websocket, game_id)

    except Exception as e:
        print(f"Error en WebSocket para game_id {game_id}: {str(e)}")
        print(traceback.format_exc())
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=1011, reason="Error interno del servidor")
        except:
            pass


async def send_task_status_update(websocket: WebSocket, game_id: str):
    """
    Verifica el estado de las tareas asociadas al juego provisional y envía actualizaciones.

    Args:
        websocket: La conexión WebSocket con el cliente
        game_id: ID del juego provisional
    """
    try:
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(game_id)})
        if not game_provisional_db:
            await manager.send_personal_message({"status": "error", "message": "Juego no encontrado"}, websocket)
            return

        tasks = await db["task"].find({"element_id": game_id, "element_type": "game_provisional"}).to_list(length=10)

        game_info = {
            "id": game_id,
            "title": game_provisional_db.get("title"),
            "state": game_provisional_db.get("state", "pending"),
            "progress": game_provisional_db.get("progress", 0),
            "progress_text": game_provisional_db.get("progress_text", "Waiting for processing"),
            "has_script": bool(game_provisional_db.get("script")),
            "has_image": bool(game_provisional_db.get("image")),
            "num_scenes": game_provisional_db.get("num_scenes", 0),
            "has_scene_interactions": bool(game_provisional_db.get("scene_interactions")),
            "has_locations": bool(game_provisional_db.get("locations")),
            "created_at": game_provisional_db.get("created_at").isoformat() if game_provisional_db.get("created_at") else None,
            "updated_at": game_provisional_db.get("updated_at").isoformat() if game_provisional_db.get("updated_at") else None,
            "game_id": str(game_provisional_db.get("game_id")) if game_provisional_db.get("game_id") else None,
        }

        task_states = []
        all_success = True
        for task_db in tasks:
            task_id = task_db.get("task_id")
            if task_id:
                task_celery = AsyncResult(task_id, app=celery)
                task_info = {
                    "id": str(task_db["_id"]),
                    "task_id": task_id,
                    "status": task_celery.state,
                    "type": task_db.get("element_type_detail", "unknown"),
                    "created_at": task_db.get("created_at").isoformat() if task_db.get("created_at") else None,
                }
                if task_celery.state == "SUCCESS":
                    task_info["result"] = task_celery.result
                    task_info["completed"] = True
                elif task_celery.state == "FAILURE":
                    task_info["error"] = str(task_celery.result)
                    task_info["completed"] = True
                    all_success = False
                else:
                    task_info["completed"] = False
                    all_success = False
                task_states.append(task_info)

        current_progress = game_provisional_db.get("progress", 0)
        updated_to_100 = False
        # Si el progreso es 70 y todas las tareas están en SUCCESS, actualizar a 100%
        if current_progress == 70 and all_success and tasks:
            progress_text = "Progreso actualizado a 100%"
            entry = {
                "timestamp": datetime.utcnow(),
                "task": None,
                "status": "progress_update",
                "percent": 100,
                "message": progress_text
            }
            await db["game_provisional"].update_one(
                {"_id": ObjectId(game_id)},
                {"$set": {"progress": 100, "progress_text": progress_text}, "$push": {"history": entry}}
            )
            game_info["progress"] = 100
            game_info["progress_text"] = progress_text
            updated_to_100 = True

        overall_status = game_provisional_db.get("state", "pending")
        status_mapping = {
            "pending": "pending",
            "ready": "ready",
            "processing": "processing",
            "generating_scenes": "generating_scenes",
            "extracting_locations": "extracting_locations",
            "extracting_characters": "extracting_characters",
            "creating_game": "creating_game",
            "completed": "completed",
            "error": "error",
            "draft": "draft"
        }
        mapped_status = status_mapping.get(overall_status, overall_status)
        await manager.send_personal_message(
            {
                "status": "update",
                "game": game_info,
                "tasks": task_states,
                "overall_status": mapped_status,
                "timestamp": datetime.now(pytz.utc).isoformat()
            },
            websocket
        )
    except Exception as e:
        print(f"Error al enviar actualización de estado: {str(e)}")
        print(traceback.format_exc())
        await manager.send_personal_message(
            {"status": "error", "message": f"Error al procesar el estado: {str(e)}"},
            websocket
        )
