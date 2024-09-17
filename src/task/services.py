from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core.database import db


async def create_task_service(_task_id: str,
                              _user_id: str,
                              _task_data: dict,
                              _element_id: str,
                              _element_type: str,
                              _process: str):
    try:
        new_task = await db["task"].insert_one({
            "task_id": _task_id,
            "user_id": _user_id,
            "element_id": _element_id,
            "element_type": _element_type,
            "process": _process,
            "status": "pending",
            "data": _task_data,
        })
        task_db = await db["task"].find_one({"_id": new_task.inserted_id})
        return task_db

    except Exception as e:
        print("Error in create task", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task not created {e}"
        )


async def update_task_service(_id: str,
                              _task_id: str,
                              _status: str):
    try:
        await db["task"].update_one({"_id": ObjectId(_id)}, {"$set": {"status": status, "task_id": _task_id}})
        return await db["task"].find_one({"_id": ObjectId(_id)})
    except Exception as e:
        print("Error in update task", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task not updated {e}"
        )


async def get_task_pending_service(user_id: str):
    try:
        task = await db["task"].find({"status": "pending", "user_id": user_id}).sort("created_at", 1).limit(1).to_list(
            None)
        return task[0] if task else None
    except Exception as e:
        print("Error in get task pending", e)
        return None
