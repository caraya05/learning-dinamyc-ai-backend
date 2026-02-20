import asyncio
import base64
from io import BytesIO
from typing import Optional

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
from pydantic import BaseModel

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
        files: list[UploadFile] = File(None),
        prompt_user: str = Form(...),
        template_type: str = Form(...),
        language: str = Form("es", description="Language code for the game"),
        series_id: str = Form(None, description="ID of the series to associate the game with")
):
    """
    This endpoint creates a new game.

    It requires the user to be authenticated and provides the following parameters:
    - `file`: An optional file upload.
    - `prompt_user`: A string representing the user's prompt.
    - `template_type`: A string representing the type of template to use.
    """

    try:

        if files:
            urls_files = []
            for file in files:
                url_file = upload_file(file=file)
                urls_files.append(url_file)
        else:
            urls_files = None

        order_previous = 0

        if series_id and ObjectId.is_valid(series_id):
                games_serie = await db["game"].find({"serie_id": series_id}).sort("order", -1).to_list(None)
                if games_serie and len(games_serie) > 0:
                    order_previous = games_serie[0].get("order", 0)


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
                "order": order_previous + 1,
                "scene_interactions": [],
                "reference_files": {
                    "characters": [],
                    "objects": [],
                    "scenarios": [],
                    "logos": [],
                    "uncategorized": urls_files
                },
                "image": None,
                "title": None,
                "script": None,
                "user_name": None,
                "user_email": None,
                "level_process": 1,
                "language": language,
                "serie_id": series_id,
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
            "language": language,
            "state": "script_create",
            "num_scenes": 0,
            "scene_interactions": [],
            "task_id": str(tasks.id),
            "reference_files": {
                "characters": [],
                "objects": [],
                "scenarios": [],
                "logos": [],
                "uncategorized": urls_files
            },
            "image": None,
            "title": None,
            "script": None,
            "user_name": None,
            "user_email": None,
            "progress": 0,
            "progress_text": "Game provisional created successfully, waiting for processing.",
            "game_id": None,
            "category": None,
            "serie_id": game_provisional_db["serie_id"],
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

    events_plus = create_intermediate_events(game_provisional_db.get("interactions"),
                                             game_provisional_db.get("characters"))

    # Normalizar y combinar events_plus y events; mover 'scene_start' al inicio si existe
    combined_events = []
    for e in game_provisional_db.get("events", []):
        combined_events.append(e.dict() if hasattr(e, "dict") else e)
    for e in events_plus:
        combined_events.append(e.dict() if hasattr(e, "dict") else e)

    has_scene_end = any(event.get("type") == "scene_end" for event in combined_events)

    # Crear evento scene_end en la última locación si no existe
    if not has_scene_end and game_provisional_db.get("locations"):
        last_location = game_provisional_db.get("locations")[-1]
        if hasattr(last_location, "dict"):
            last_location = last_location.dict()
        last_loc_id = last_location.get("id") if isinstance(last_location, dict) else last_location["id"]

        characters_in_last_loc = []
        for character in game_provisional_db.get("characters", []):
            char_data = character.dict() if hasattr(character, "dict") else character
            if char_data.get("id_location") == last_loc_id:
                characters_in_last_loc.append(char_data.get("id"))

        characters = game_provisional_db.get("characters", [])
        principal_char_id = None
        if characters:
            for char in characters:
                char_dict = char.dict() if hasattr(char, "dict") else char
                if str(char_dict.get("role", "")).lower() == "principal":
                    principal_char_id = char_dict.get("id")

        character_event = principal_char_id if principal_char_id else (
            characters_in_last_loc[0] if characters_in_last_loc else None)

        scene_end_event = {
            "id": "event_end",
            "description": "Evento final del juego",
            "visual_description": "Final de la aventura",
            "type": "scene_end",
            "id_characters": character_event,
            "order": 4,
            "id_location_start": last_loc_id,
            "id_location_end": last_loc_id,
        }
        combined_events.append(scene_end_event)

    # Recuperar imágenes de locaciones usando el mapeo de IDs
    locations_with_images = []
    id_map_locations_detailed = game_provisional_db.get("id_map_locations_detailed", {})

    for loc in game_provisional_db.get("locations", []):
        location_data = loc.dict() if hasattr(loc, "dict") else loc
        loc_provisional_id = location_data.get("id")

        if loc_provisional_id and loc_provisional_id in id_map_locations_detailed:
            loc_db_id = id_map_locations_detailed[loc_provisional_id].get("db_id")
            if loc_db_id:
                # Recuperar locación de la base de datos para obtener su imagen
                location_db = await db["location_glic"].find_one({"_id": ObjectId(loc_db_id)})
                if location_db:
                    location_data["image_url"] = location_db.get("image")
                    location_data["sound"] = location_db.get("sound")
                    location_data["sound_mp3"] = location_db.get("sound_mp3")

        locations_with_images.append(location_data)

    # Recuperar audios de conversaciones usando el mapeo de personajes
    interactions_with_audio = []
    id_map_characters_detailed = game_provisional_db.get("id_map_characters_detailed", {})

    for interaction in game_provisional_db.get("interactions", []):
        interaction_data = interaction.dict() if hasattr(interaction, "dict") else interaction
        id_characters = interaction_data.get("id_characters", [])

        # Enriquecer cada conversación con información de audio del personaje
        if "conversations" in interaction_data:
            for conversation in interaction_data["conversations"]:
                char_provisional_id = conversation.get("id_character")

                if char_provisional_id and char_provisional_id in id_map_characters_detailed:
                    char_db_id = id_map_characters_detailed[char_provisional_id].get("db_id")
                    if char_db_id:
                        # Recuperar personaje para obtener su voice_id
                        character_db = await db["character_glic"].find_one({"_id": ObjectId(char_db_id)})
                        if character_db:
                            conversation["voice_id"] = character_db.get("voice_id")
                            # Recuperar conversaciones asociadas si existen
                            if character_db.get("conversation"):
                                conversation["audio_data"] = character_db.get("conversation")

        interactions_with_audio.append(interaction_data)

    return {
        "_id": str(game_provisional_db["_id"]),
        "prompt_user": game_provisional_db["prompt_user"],
        "template_type": game_provisional_db["type_template"],
        "created_at": game_provisional_db["created_at"],
        "updated_at": game_provisional_db["updated_at"],
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
        "locations": locations_with_images,
        "events": combined_events,
        "interactions": interactions_with_audio,
        "game_structure": create_game_structure(game_provisional_db.get("locations", []),
                                                game_provisional_db.get("events", []),
                                                game_provisional_db.get("interactions", []),
                                                game_provisional_db.get("characters", [])),
        "level_process": game_provisional_db.get("level_process", 1),
        "game_id": str(game_provisional_db["game_id"]) if game_provisional_db.get("game_id") else None,
        "reference_files": game_provisional_db.get("reference_files", {
            "characters": [],
            "objects": [],
            "scenarios": [],
            "logos": [],
            "uncategorized": []
        }),
        # Diccionarios de mapeo
        "id_map_characters": game_provisional_db.get("id_map_characters", {}),
        "id_map_locations": game_provisional_db.get("id_map_locations", {}),
        "id_map_events": game_provisional_db.get("id_map_events", {}),
        "id_map_states": game_provisional_db.get("id_map_states", {}),
        # Diccionarios detallados con información de state_game
        "id_map_characters_detailed": game_provisional_db.get("id_map_characters_detailed", {}),
        "id_map_locations_detailed": game_provisional_db.get("id_map_locations_detailed", {}),
        "id_map_events_detailed": game_provisional_db.get("id_map_events_detailed", {}),
    }


class GameUpdateRequest(BaseModel):
    image: Optional[str] = None
    script: Optional[str] = None
    title: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    is_draft: bool = False
    characters: Optional[list] = None
    locations: Optional[list] = None
    interactions: Optional[list] = None
    events: Optional[list] = None


@router.patch("/{id_game_provisional}", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute", error_message="Intentalo de nuevo más tarde")
async def update_game_provisional(
        request: Request,
        id_game_provisional: str,
        data: GameUpdateRequest,
        user: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),

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

    print("data",data.interactions)

    if data.script is not None:
        update_fields["script"] = data.script
    if data.title is not None:
        update_fields["title"] = data.title
    if data.characters is not None:
        update_fields["characters"] = data.characters
    if data.locations is not None:
        update_fields["locations"] = data.locations
    if data.interactions is not None:
        update_fields["interactions"] = data.interactions
    if data.events is not None:
        update_fields["events"] = data.events
    # if data.image is not None and not data.image.startswith("https://"):
    #     # Asegurar el relleno correcto para la cadena Base64
    #     missing_padding = len(data.image) % 4
    #     if missing_padding:
    #         data.image += "=" * (4 - missing_padding)
    #
    #     # Decodificar la imagen Base64
    #     try:
    #         image_data = base64.b64decode(data.image)
    #         img_byte_arr = BytesIO(image_data)
    #     except Exception as e:
    #         print(f"Error decoding Base64 image: {e}")
    #
    #     # Subir la imagen
    #     update_fields["image"] = upload_image(
    #         img_byte_arr=img_byte_arr,
    #         file_name=f"game-provisional/{uuid4()}.jpg",
    #         size=(512, 896)
    #     )
    if data.user_name is not None:
        update_fields["user_name"] = data.user_name
    if data.user_email is not None:
        update_fields["user_email"] = data.user_email

    await db["game_provisional"].update_one(
        {"_id": ObjectId(id_game_provisional)},
        {"$set": update_fields}
    )
    # print("Updating game provisional with fields:", update_fields)

    if not data.is_draft:
        update_fields["state"] = "game_create"
        continue_create_game_provisional_2.delay(id_game_provisional=id_game_provisional, user_id=str(user["_id"]))

    else:
        update_fields["state"] = "draft"

    update_fields["progress"] = 0
    update_fields["progress_text"] = "Game provisional is ready, waiting for processing."
    update_fields["level_process"] = 2

    # print("Updating game provisional with fields:", update_fields)

    await db["game_provisional"].update_one(
        {"_id": ObjectId(id_game_provisional)},
        {"$set": update_fields}
    )
    game_provisional_db = await db["game_provisional"].find_one(
        {"_id": ObjectId(id_game_provisional)}
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
                        try:
                            await send_task_status_update(websocket, game_id)
                        except Exception as e:
                            print(
                                f"Error al enviar actualización de estado solicitada para game_id {game_id}: {str(e)}")
                            print(traceback.format_exc())
                            # Cerrar la conexión WebSocket cuando ocurra un error
                            try:
                                if websocket.client_state == WebSocketState.CONNECTED:
                                    await websocket.close(code=1011, reason=f"Error: {str(e)}")
                            except:
                                pass
                            manager.disconnect(websocket, game_id)
                            return
                except asyncio.TimeoutError:
                    # No se recibieron mensajes, seguimos con la verificación periódica
                    pass

                # Verificar y enviar actualizaciones de estado periódicamente
                try:
                    await send_task_status_update(websocket, game_id)
                except Exception as e:
                    print(f"Error al enviar actualización de estado para game_id {game_id}: {str(e)}")
                    print(traceback.format_exc())
                    # Cerrar la conexión WebSocket cuando ocurra un error
                    try:
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.close(code=1011, reason=f"Error: {str(e)}")
                    except:
                        pass
                    manager.disconnect(websocket, game_id)
                    return

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
            "created_at": game_provisional_db.get("created_at").isoformat() if game_provisional_db.get(
                "created_at") else None,
            "updated_at": game_provisional_db.get("updated_at").isoformat() if game_provisional_db.get(
                "updated_at") else None,
            "game_id": str(game_provisional_db.get("game_id")) if game_provisional_db.get("game_id") else None,
            "series_id": str(game_provisional_db.get("serie_id")) if game_provisional_db.get("serie_id") else None,
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
        # Enviar mensaje de error antes de lanzar la excepción
        try:
            await manager.send_personal_message(
                {"status": "error", "message": f"Error al procesar el estado: {str(e)}"},
                websocket
            )
        except:
            pass
        # Lanzar la excepción para que sea capturada en el nivel superior
        raise

