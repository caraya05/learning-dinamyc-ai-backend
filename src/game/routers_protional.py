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

from utils import upload_file, send_email, upload_image

from slowapi.util import get_remote_address
from slowapi import Limiter

from celery.result import AsyncResult
from celery_worker import create_game_provisional_task, generate_scene_interactions_task, celery

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
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(message)

    async def broadcast(self, message: dict, game_id: str):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id]:
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
        time_game: str = Form(...),
):
    """
    This endpoint creates a new game.

    It requires the user to be authenticated and provides the following parameters:
    - `file`: An optional file upload.
    - `prompt_user`: A string representing the user's prompt.
    - `time_game`: A string representing the time for the game.
    """

    try:

        url_file = upload_file(file=file)

        game_provisional_db = await db["game_provisional"].insert_one(
            {
                "prompt_user": prompt_user,
                "time_game": time_game,
                "created_at": datetime.now(pytz.utc),
                "updated_at": datetime.now(pytz.utc),
                "created_by": str(user["_id"]),
                "updated_by": str(user["_id"]),
                "state": "pending",
                "num_scenes": 0,
                "scene_interactions": [],
                "file": url_file,
                "image": None,
                "title": None,
                "script": None,
                "user_name": None,
                "user_email": None
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

        tasks = create_game_provisional_task.delay(str(game_provisional_db["_id"]))

        return {
            "_id": str(game_provisional_db["_id"]),
            "prompt_user": prompt_user,
            "time_game": time_game,
            "created_at": game_provisional_db["created_at"],
            "updated_at": game_provisional_db["updated_at"],
            "created_by": str(user["_id"]),
            "updated_by": str(user["_id"]),
            "state": "pending",
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

    return {
        "_id": str(game_provisional_db["_id"]),
        "prompt_user": game_provisional_db["prompt_user"],
        "time_game": game_provisional_db["time_game"],
        "created_at": game_provisional_db["created_at"],
        "updated_at": game_provisional_db["updated_at"],
        "file": game_provisional_db["file"],
        "image": game_provisional_db["image"],
        "title": game_provisional_db["title"],
        "script": game_provisional_db["script"],
        "user_name": game_provisional_db.get("user_name"),
        "user_email": game_provisional_db.get("user_email"),
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

    if game_provisional_db["user_name"] and game_provisional_db["user_email"]:
        html = f"""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns="http://www.w3.org/1999/xhtml"
      style="color-scheme: light dark; supported-color-schemes: light dark;">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <meta name="x-apple-disable-message-reformatting"/>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    <meta name="color-scheme" content="light dark"/>
    <meta name="supported-color-schemes" content="light dark"/>
    <title></title>

    <style>
        body {{
            background-color: #f3f4f6;
            color: #1f2937;
            font-family: Arial, sans-serif;
        }}

        .container {{
            max-width: 640px;
            margin: 0 auto;
            padding: 24px;
            background-color: #ffffff;
        }}

        .header {{
            text-align: center;
            padding: 24px 0;
        }}

        .header h1 {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #ffffff;
            background-color: #ec4899;
            padding: 8px;
            display: inline-block;
        }}

        .title {{
            font-size: 1.125rem;
            font-weight: 600;
            color: #4b5563;
        }}

        .text {{
            margin-top: 16px;
            font-size: 0.875rem;
            color: #374151;
        }}

        .text span {{
            font-family: monospace;
            color: #6b7280;
        }}
    </style>

</head>
<body>
  
<div class="container">
    <div class="header"
         style="position:relative; text-align:center; padding:12px 0; background-color:#ec4899; border-radius:4px;">
    
        <h1 style="position:relative; z-index:1; font-size:1.5rem; font-weight:700; color:#ffffff; margin:0; padding:8px;">
            Qwestar
         </h1>
    </div>
    <h2 class="title">Game Creation Request</h2>
    <p class="text">
        The following company has requested the creation of a game with the following information:
    </p>
   <div style="padding:24px; margin:24px auto; box-shadow:0 2px 8px #0001;">
     <div style="display:flex; align-items:center; gap:16px; margin-bottom:16px;">
 <div style="background:#fff; padding:8px; display:flex; justify-content:center; align-items:center;">
   <img src="{game_provisional_db["image"]}" alt="Example image" style="object-fit:contain; width:200px; height:280px;" />
 </div>
       <div style="margin-left:8px;">
         <div style="font-size:1.1rem; font-weight:700; color:#ec4899;">{game_provisional_db["title"]}</div>
            <span style="color:#6b7280;">Game time: {game_provisional_db["time_game"]}</span>
              <div style="margin-bottom:8px; margin-top:4px; ">
       <span style="font-weight:600; color:#374151;">Description:</span>
       <span style="color:#6b7280;">{game_provisional_db["prompt_user"]}</span>
     </div>
              <div style="margin-bottom:8px;">
       <span style="font-weight:600; color:#374151;">Company:</span>
       <span style="color:#6b7280;">{game_provisional_db["user_name"]}</span>
     </div>
     <div style="margin-bottom:8px;">
       <span style="font-weight:600; color:#374151;">Email:</span>
       <span style="color:#6b7280;">{game_provisional_db["user_email"]}</span>
     </div>
    <div style="margin-top:12px;">
       <a href="{game_provisional_db["file"]}" download style="color:#ec4899; text-decoration:underline; font-weight:600;">
         Download file
       </a>
     </div>
       </div>
     </div>
   
    <div style="margin-bottom:8px;">
       <span style="font-weight:600; color:#374151; display:block; margin-bottom:4px;">Script:</span>
       <div style=" padding:10px 12px; color:#6b7280; font-size:0.95rem; text-align:justify;">
         {game_provisional_db["script"] if game_provisional_db["script"] else "No script provided."}
       </div>
     </div>
    
   </div>
</div>
</body>
</html>
        """
        # TODO: Uncomment the following line to send the email
        # response = await send_email(
        #     recipients=["jn@qwestar.ai"],
        #     subject=f"Game Provisional Updated: {game_provisional_db['title']}",
        #     body=html
        # )
    if not is_draft:
        update_fields["state"] = "ready"
        generate_scene_interactions_task.delay(id_game_provisional=id_game_provisional)
        game_provisional_db["state"] = "ready"

    else:
        update_fields["state"] = "draft"
        game_provisional_db["state"] = "draft"

    update_fields["progress"] = 0
    update_fields["progress_text"] = "Game provisional is ready, waiting for processing."

    await db["game_provisional"].update_one(
        {"_id": ObjectId(id_game_provisional)},
        {"$set": update_fields}
    )

    return {
        "_id": str(game_provisional_db["_id"]),
        "prompt_user": game_provisional_db["prompt_user"],
        "time_game": game_provisional_db["time_game"],
        "created_at": game_provisional_db["created_at"],
        "updated_at": game_provisional_db["updated_at"],
        "image": game_provisional_db["image"],
        "title": game_provisional_db["title"],
        "script": game_provisional_db["script"],
        "state": game_provisional_db["state"]
    }


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
        # Obtener la información más reciente del juego provisional
        game_provisional_db = await db["game_provisional"].find_one(
            {"_id": ObjectId(game_id)}
        )

        if not game_provisional_db:
            await manager.send_personal_message(
                {"status": "error", "message": "Juego no encontrado"},
                websocket
            )
            return

        # Buscar tareas relacionadas con este juego
        tasks = await db["task"].find(
            {"element_id": game_id, "element_type": "game_provisional"}
        ).to_list(length=10)

        # Información del juego con estado y progreso
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
        }

        # Estado de las tareas
        task_states = []
        for task_db in tasks:
            task_id = task_db.get("task_id")
            if task_id:
                # Verificar el estado real de la tarea en Celery
                task_celery = AsyncResult(task_id, app=celery)
                task_info = {
                    "id": str(task_db["_id"]),
                    "task_id": task_id,
                    "status": task_celery.state,
                    "type": task_db.get("element_type_detail", "unknown"),
                    "created_at": task_db.get("created_at").isoformat() if task_db.get("created_at") else None,
                }

                # Si la tarea está completada o falló, incluir más detalles
                if task_celery.state == "SUCCESS":
                    task_info["result"] = task_celery.result
                    task_info["completed"] = True
                elif task_celery.state == "FAILURE":
                    task_info["error"] = str(task_celery.result)
                    task_info["completed"] = True

                task_states.append(task_info)

        # Determinar el estado general basado en el estado del juego provisional
        overall_status = game_provisional_db.get("state", "pending")

        # Mapear estados específicos para mejor comprensión del frontend
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

        # Enviar la actualización al cliente
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
