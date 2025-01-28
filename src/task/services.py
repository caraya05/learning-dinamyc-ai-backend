import traceback
from datetime import datetime

from pytz import timezone

from bson import ObjectId

from fastapi import HTTPException
from fastapi import status

from core.database import db


async def create_task_service(
        _task_id: str,
        _user_id: str,
        _task_data: dict,
        _element_id: str,
        _element_type: str,
        _process: str,
):
    try:
        date_now = datetime.now(timezone('UTC'))
        new_task = await db["task"].insert_one(
            {
                "task_id": _task_id,
                "user_id": _user_id,
                "element_id": _element_id,
                "element_type": _element_type,
                "process": _process,
                "status": "pending",
                "data": _task_data,
                "created_at": date_now.astimezone(timezone('America/Bogota')),
                "reported_at": None,
                "was_notified": False,
                "status_updated": 0,
            }
        )
        await db[_element_type].update_one({"_id": ObjectId(_element_id)}, {"$set": {"status": 1}})
        task_db = await db["task"].find_one({"_id": new_task.inserted_id})
        return task_db

    except Exception as e:
        print("Error in create task", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task not created {e}")


async def update_task_service(
        _id: str,
        _task_id: str = None,
        _status: str = None,
        _data: dict = None,
        _message: str = None,
        _was_notified: bool = False,
        _status_updated: int = 0,
):
    try:
        update_fields = {}
        if _task_id is not None:
            update_fields["task_id"] = _task_id
        if _status is not None:
            update_fields["status"] = _status
        if _data is not None:
            update_fields["data"] = _data
        if _was_notified:
            update_fields["was_notified"] = _was_notified
            update_fields["reported_at"] = datetime.now(timezone('UTC')).astimezone(
                timezone('America/Bogota')
            )
        if _status_updated != 0:
            update_fields["status_updated"] = _status_updated
        if _message:
            update_fields["message"] = _message
        if update_fields:
            await db["task"].update_one({"_id": ObjectId(_id)}, {"$set": update_fields})
        task_db = await db["task"].find_one({"_id": ObjectId(_id)})
        element_db = await db[task_db["element_type"]].find_one(
            {"_id": ObjectId(task_db["element_id"])}
        )
        _query = {}
        if _status == "completed":
            _query["status"] = 2
            if isinstance(element_db.get("tasks_notified", None), list):
                element_db["tasks_notified"].append(_id)
                _query["tasks_notified"] = element_db["tasks_notified"]
        elif _status == "failed":
            _query["status"] = 3
            if isinstance(element_db.get("tasks_notified", None), list):
                element_db["tasks_notified"].append(_id)
                _query["tasks_notified"] = element_db["tasks_notified"]
        if _query != {}:
            await db[task_db["element_type"]].update_one(
                {"_id": ObjectId(task_db["element_id"])}, {"$set": _query}
            )
        return await db["task"].find_one({"_id": ObjectId(_id)})
    except Exception as e:
        traceback.print_exc()
        print("Error in update task", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task not updated {str(e)}")


async def get_task_pending_service(user_id: str, ids: str = None, is_list: bool = False):
    try:
        query = {"was_notified": False, "user_id": user_id}
        if ids:
            query["_id"] = ObjectId(ids)

        cursor = db["task"].find(query).sort("created_at", 1)
        task = await cursor.to_list(None if is_list else 1)

        return task if is_list else (task[0] if task else None)
    except Exception as e:
        print("Error in get task pending", e)
        return None
