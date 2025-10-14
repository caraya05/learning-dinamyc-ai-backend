from bson import ObjectId
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from task.services import get_task_pending_service
from task.services import revoke_task
from task.schemas import TaskRevokeResponse

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


@router.post("/{task_id}/revoke", response_model=TaskRevokeResponse)
async def revoke_task_endpoint(task_id: str, terminate: bool = True):
    """
    Revoca o termina una tarea en ejecución.

    Args:
        task_id: ID de la tarea a revocar
        terminate: Si es True, termina la tarea forzosamente
    """
    result = await revoke_task(task_id, terminate)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result
