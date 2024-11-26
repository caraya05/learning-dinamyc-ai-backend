from bson import ObjectId
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from task.services import get_task_pending_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/pending")
async def get_tasks(
    user: dict = Depends(auth), Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    tasks_db = await get_task_pending_service(user_id=str(user["_id"]), is_list=True)

    results_tasks = []
    for task in tasks_db:
        task["_id"] = str(task["_id"])
        results_tasks.append(task["_id"])

    return {"results": tasks_db, "tasks": results_tasks}
