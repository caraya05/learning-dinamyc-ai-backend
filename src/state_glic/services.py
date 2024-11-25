from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core.database import db

from state_glic.models import StateGLIC


async def create_state_glic(element_id: str,
                            type_element: str,
                            state: str,
                            created_by: str,
                            order: int,
                            data: dict = None) -> dict:
    state_glic = StateGLIC(
        element_id=element_id,
        type_element=type_element,
        state=state,
        data=data,
        order=order,
        created_at=datetime.utcnow(),
        created_by=created_by,
        updated_at=datetime.utcnow(),
        updated_by=created_by
    ).dict()

    result = await db["state_glic"].insert_one(state_glic)
    state_glic["_id"] = str(result.inserted_id)
    return state_glic


async def get_state_glic_by_element_id(element_id: str, state: str) -> dict:
    state_glic = await db["state_glic"].find_one({"element_id": element_id, "state": state})
    if state_glic:
        state_glic["_id"] = str(state_glic["_id"])
        return state_glic
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="StateGLIC not found"
    )


async def updated_state_glic_by_element_id(element_id: str, state: str, data) -> dict:
    state_glic = await get_state_glic_by_element_id(element_id, state)
    if state_glic:
        state_glic_updated = await db["state_glic"].find_one_and_update(
            {"_id": ObjectId(state_glic["_id"]), "state": state_glic["state"]},
            {"$set": {"state": state, "updated_at": datetime.utcnow()}},
            return_document=True
        )
        state_glic_updated["_id"] = str(state_glic_updated["_id"])
        return state_glic_updated
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="StateGLIC not found"
    )


async def get_list_state_glic_by_element_id(element_id: str) -> list:
    state_glic = await db["state_glic"].find({"element_id": element_id}).to_list(length=1000)
    for state in state_glic:
        state["_id"] = str(state["_id"])
    return state_glic