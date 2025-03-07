import asyncio
import traceback
from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends
from fastapi import WebSocket, WebSocketException, WebSocketDisconnect
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.services import is_token_valid
from auth.utils import auth_schema
from core.database import db
from task.services import get_task_pending_service, update_task_service

from celery.result import AsyncResult
from celery_worker import celery

# from celery_worker import background_task

router = APIRouter(prefix="/ws/user", tags=["User"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


# @router.post("/create-task")
# async def create_task_endpoint(
#         user_db: dict = Depends(auth),
#         Token: HTTPAuthorizationCredentials = Depends(auth_schema),
# ):
#     try:
#
#         task_record = {
#             "task_id": None,
#             "status": None,
#             "user_id": str(user_db["_id"]),
#             "task_data": None,
#             "was_notified": False
#         }
#         task_db = await create_task_service(task_record)
#
#         task = background_task.delay(str(task_db["_id"]))
#
#         await db["task"].update_one(
#             {"_id": task_db["_id"]},
#             {"$set": {"task_id": str(task), "task_data": None, "status": "pending"}}
#         )
#
#         return {"detail": "Task created", "task_id": str(task)}
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: str,
):
    try:
        await manager.connect(websocket)
        valid_token = await is_token_valid(token)
        if not valid_token:
            await manager.send_personal_message({"detail": "Invalid token"}, websocket)
            manager.disconnect(websocket)
            return None
        user_db = await db["user"].find_one({"_id": ObjectId(user_id)})
        if not user_db:
            await manager.send_personal_message({"detail": "User not found"}, websocket)
            manager.disconnect(websocket)
            return None
        await websocket.send_json({"detail": "Connected to websocket"})
        while True:
            task_request = None
            try:
                task_request = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break
            await asyncio.sleep(0.5)
            if task_request:
                tasks = task_request.get("task", [])
                for task_id in tasks:
                    task_db = await get_task_pending_service(user_id=user_id, ids=task_id)
                    if task_db:
                        if task_db.get("task_id", None):
                            task_celery = AsyncResult(task_db["task_id"], app=celery)
                            if task_celery.state == "SUCCESS":
                                if "Error" in task_celery.result:
                                    await manager.send_personal_message(
                                        {
                                            "detail": "Task failed",
                                            "task_id": str(task_db["_id"]),
                                            "error": task_celery.result,
                                            "element_id": str(task_db["element_id"]),
                                            "element_type": task_db["element_type"],
                                            "status_updated": task_db["status_updated"],
                                            "status": 3,
                                        },
                                        websocket,
                                    )
                                    await update_task_service(
                                        _id=str(task_db["_id"]),
                                        _status="failed",
                                        _was_notified=True,
                                    )
                                else:
                                    await manager.send_personal_message(
                                        {
                                            "detail": "Task completed",
                                            "task_id": str(task_db["_id"]),
                                            "element_id": str(task_db["element_id"]),
                                            "element_type": task_db["element_type"],
                                            "status_updated": task_db["status_updated"],
                                            "status": 2,
                                        },
                                        websocket,
                                    )
                                    await update_task_service(
                                        _id=str(task_db["_id"]),
                                        _status="completed",
                                        _was_notified=True,
                                    )
                            elif task_celery.state == "FAILURE":
                                await manager.send_personal_message(
                                    {
                                        "detail": "Task failed",
                                        "task_id": str(task_db["_id"]),
                                        "element_id": str(task_db["element_id"]),
                                        "element_type": task_db["element_type"],
                                        "error": task_celery.result,
                                        "status_updated": task_db["status_updated"],
                                        "status": 3,
                                    },
                                    websocket,
                                )
                                await update_task_service(
                                    _id=str(task_db["_id"]), _status="failed", _was_notified=True
                                )
            else:
                task_db = await get_task_pending_service(user_id)
                if task_db:
                    created_at = task_db.get("created_at")
                    if created_at:
                        if datetime.utcnow() - created_at > timedelta(minutes=6):
                            task_celery = AsyncResult(task_db["task_id"], app=celery)
                            if (task_celery.state and task_celery.state == "SUCCESS") or (task_db["message"] and task_db["status"] == "completed"):
                                if (task_celery.result and "Error" in task_celery.result) or (task_db["message"] and "error" in task_db["message"]):
                                    await manager.send_personal_message(
                                        {
                                            "detail": "Task failed, notified out of time",
                                            "task_id": str(task_db["_id"]),
                                            "error": task_celery.result,
                                            "element_id": str(task_db["element_id"]),
                                            "element_type": task_db["element_type"],
                                            "status_updated": task_db["status_updated"],
                                            "status": 3,
                                        },
                                        websocket,
                                    )
                                    await update_task_service(
                                        _id=str(task_db["_id"]),
                                        _status="failed",
                                        _was_notified=True,
                                    )
                                    continue  # Skip further processing for this task
                                else:
                                    await manager.send_personal_message(
                                        {
                                            "detail": "Task completed, notified out of time",
                                            "task_id": str(task_db["_id"]),
                                            "element_id": str(task_db["element_id"]),
                                            "element_type": task_db["element_type"],
                                            "status_updated": task_db["status_updated"],
                                            "status": 2,
                                        },
                                        websocket,
                                    )
                                    await update_task_service(
                                        _id=str(task_db["_id"]),
                                        _status="completed",
                                        _was_notified=True,
                                    )
                                    continue  # Skip further processing for this task
                            else:
                                await manager.send_personal_message(
                                    {
                                        "detail": "Task failed due to timeout",
                                        "task_id": str(task_db["_id"]),
                                        "element_id": str(task_db["element_id"]),
                                        "element_type": task_db["element_type"],
                                        "status_updated": task_db.get("status_updated", 0),
                                        "status": 3,
                                    },
                                    websocket,
                                )
                                await update_task_service(
                                    _id=str(task_db["_id"]), _status="failed", _was_notified=True
                                )
                                continue  # Skip further processing for this task
                            continue  # Skip further processing for this task
                    if task_db.get("task_id", None):
                        task_celery = AsyncResult(task_db["task_id"], app=celery)
                        if task_celery.state == "SUCCESS":
                            if "Error" in task_celery.result:
                                await manager.send_personal_message(
                                    {
                                        "detail": "Task failed",
                                        "task_id": str(task_db["_id"]),
                                        "error": task_celery.result,
                                        "element_id": str(task_db["element_id"]),
                                        "element_type": task_db["element_type"],
                                        "status_updated": task_db["status_updated"],
                                        "status": 3,
                                    },
                                    websocket,
                                )
                                await update_task_service(
                                    _id=str(task_db["_id"]), _status="failed", _was_notified=True
                                )
                            else:
                                await manager.send_personal_message(
                                    {
                                        "detail": "Task completed",
                                        "task_id": str(task_db["_id"]),
                                        "element_id": str(task_db["element_id"]),
                                        "element_type": task_db["element_type"],
                                        "status_updated": task_db["status_updated"],
                                        "status": 2,
                                    },
                                    websocket,
                                )
                                await update_task_service(
                                    _id=str(task_db["_id"]), _status="completed", _was_notified=True
                                )
                        elif task_celery.state == "FAILURE":
                            await manager.send_personal_message(
                                {
                                    "detail": "Task failed",
                                    "task_id": str(task_db["_id"]),
                                    "element_id": str(task_db["element_id"]),
                                    "element_type": task_db["element_type"],
                                    "error": task_celery.result,
                                    "status_updated": task_db["status_updated"],
                                    "status": 3,
                                },
                                websocket,
                            )
                            await update_task_service(
                                _id=str(task_db["_id"]), _status="failed", _was_notified=True
                            )
                        else:
                            if task_db["status"] == "completed":
                                await manager.send_personal_message(
                                    {
                                        "detail": "Task completed",
                                        "task_id": str(task_db["_id"]),
                                        "element_id": str(task_db["element_id"]),
                                        "element_type": task_db["element_type"],
                                        "status_updated": task_db["status_updated"],
                                        "status": 2,
                                    },
                                    websocket,
                                )
                                await update_task_service(
                                    _id=str(task_db["_id"]), _status="completed", _was_notified=True
                                )
                            elif task_db["status"] == "failed":
                                await manager.send_personal_message(
                                    {
                                        "detail": "Task failed",
                                        "task_id": str(task_db["_id"]),
                                        "element_id": str(task_db["element_id"]),
                                        "element_type": task_db["element_type"],
                                        "status_updated": task_db["status_updated"],
                                        "status": 3,
                                    },
                                    websocket,
                                )
                                await update_task_service(
                                    _id=str(task_db["_id"]), _status="failed", _was_notified=True
                                )

    except WebSocketException as e:
        print(traceback.format_exc())
        await manager.send_personal_message({"detail": "WebSocket error"}, websocket)
        manager.disconnect(websocket)
    except WebSocketDisconnect as e:
        print(traceback.format_exc())
        manager.disconnect(websocket)
