import asyncio

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
    await websocket.accept()
    valid_token = await is_token_valid(token)
    if not valid_token:
        await websocket.send_json({"detail": "Invalid token"})
        await websocket.close(reason="Invalid token")
        return None
    user_db = await db["user"].find_one({"_id": ObjectId(user_id)})
    if not user_db:
        await websocket.send_json({"detail": "User not found"})
        await websocket.close(reason="User not found")
        return None
    await websocket.send_json({"detail": "Connected to websocket"})
    try:
        while True:
            task_request = None
            try:
                task_request = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            await asyncio.sleep(1)
            if task_request:
                tasks = task_request.get("task", [])
                # if not isinstance(tasks, list):
                #     tasks = [tasks]
                for task_id in tasks:
                    task_db = await get_task_pending_service(user_id=user_id, ids=task_id)
                    if task_db:
                        if task_db.get("task_id", None):
                            task_celery = AsyncResult(task_db["task_id"], app=celery)
                            if task_celery.state == "SUCCESS":
                                if "Error" in task_celery.result:
                                    await websocket.send_json(
                                        {
                                            "detail": "Task failed",
                                            "task_id": str(task_db["_id"]),
                                            "error": task_celery.result,
                                            "element_id": str(task_db["element_id"]),
                                            "element_type": task_db["element_type"],
                                        }
                                    )
                                    await update_task_service(
                                        _id=str(task_db["_id"]),
                                        _status="failed",
                                        _was_notified=True,
                                    )
                                else:
                                    await websocket.send_json(
                                        {
                                            "detail": "Task completed",
                                            "task_id": str(task_db["_id"]),
                                            "element_id": str(task_db["element_id"]),
                                            "element_type": task_db["element_type"],
                                        }
                                    )
                                    await update_task_service(
                                        _id=str(task_db["_id"]),
                                        _status="completed",
                                        _was_notified=True,
                                    )
                            elif task_celery.state == "FAILURE":
                                await websocket.send_json(
                                    {
                                        "detail": "Task failed",
                                        "task_id": str(task_db["_id"]),
                                        "element_id": str(task_db["element_id"]),
                                        "element_type": task_db["element_type"],
                                        "error": task_celery.result,
                                    }
                                )
                                await update_task_service(
                                    _id=str(task_db["_id"]), _status="failed", _was_notified=True
                                )
            else:
                task_db = await get_task_pending_service(user_id)
                if task_db:
                    if task_db.get("task_id", None):
                        task_celery = AsyncResult(task_db["task_id"], app=celery)
                        if task_celery.state == "SUCCESS":
                            if "Error" in task_celery.result:
                                await websocket.send_json(
                                    {
                                        "detail": "Task failed",
                                        "task_id": str(task_db["_id"]),
                                        "error": task_celery.result,
                                        "element_id": str(task_db["element_id"]),
                                        "element_type": task_db["element_type"],
                                    }
                                )
                                await update_task_service(
                                    _id=str(task_db["_id"]), _status="failed", _was_notified=True
                                )
                            else:
                                await websocket.send_json(
                                    {
                                        "detail": "Task completed",
                                        "task_id": str(task_db["_id"]),
                                        "element_id": str(task_db["element_id"]),
                                        "element_type": task_db["element_type"],
                                    }
                                )
                                await update_task_service(
                                    _id=str(task_db["_id"]), _status="completed", _was_notified=True
                                )
                        elif task_celery.state == "FAILURE":
                            await websocket.send_json(
                                {
                                    "detail": "Task failed",
                                    "task_id": str(task_db["_id"]),
                                    "element_id": str(task_db["element_id"]),
                                    "element_type": task_db["element_type"],
                                    "error": task_celery.result,
                                }
                            )
                            await update_task_service(
                                _id=str(task_db["_id"]), _status="failed", _was_notified=True
                            )

    except WebSocketException as e:
        await websocket.send_json({"detail": "Error connecting to websocket"})
        await websocket.close(reason="Error connecting to websocket")
