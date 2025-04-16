from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core.database import db

from state_glic.models import StateGLIC


async def create_state_glic(
        element_id: str, type_element: str, state: str, created_by: str, order: int, data: dict = None
) -> dict:
    state_glic = StateGLIC(
        element_id=element_id,
        type_element=type_element,
        state=state,
        data=data,
        order=order,
        created_at=datetime.utcnow(),
        created_by=created_by,
        updated_at=datetime.utcnow(),
        updated_by=created_by,
    ).dict()

    result = await db["state_glic"].insert_one(state_glic)
    state_glic["_id"] = str(result.inserted_id)
    return state_glic


async def get_state_glic_by_element_id(element_id: str, state: str) -> dict:
    state_glic = await db["state_glic"].find_one({"element_id": element_id, "state": state})
    if state_glic:
        state_glic["_id"] = str(state_glic["_id"])
        return state_glic
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StateGLIC not found")


async def updated_state_glic_by_element_id(element_id: str, state: str, data) -> dict:
    state_glic = await get_state_glic_by_element_id(element_id, state)
    if state_glic:
        state_glic_updated = await db["state_glic"].find_one_and_update(
            {"_id": ObjectId(state_glic["_id"]), "state": state_glic["state"]},
            {"$set": {"state": state, "updated_at": datetime.utcnow()}},
            return_document=True,
        )
        state_glic_updated["_id"] = str(state_glic_updated["_id"])
        return state_glic_updated
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StateGLIC not found")


import traceback


async def get_list_state_glic_by_element_id(element_id: str) -> list:
    try:
        state_glic = await db["state_glic"].find({"element_id": element_id}).to_list(None)
        for j in range(len(state_glic)):
            state_glic[j]["_id"] = str(state_glic[j]["_id"])
            if state_glic[j]["type_element"] in ["character", "location", "item"]:
                if state_glic[j]["data"].get("interaction", None):
                    for i in range(len(state_glic[j]["data"]["interaction"])):
                        print(state_glic[j]["data"]["interaction"][i])
                        if state_glic[j]["data"]["interaction"][i].get("type_conversation", None):
                            if state_glic[j]["data"]["interaction"][i]["type_conversation"] in ["one_way", "two_way"]:
                                event_db = await db["event"].find_one(
                                    {
                                        "game_id": state_glic[j]["data"]["game_id"],
                                        "character_id": state_glic[j]["element_id"],
                                        "state_game_init": state_glic[j]["state"],
                                        "location_state_game_init": state_glic[j]["data"]["interaction"][i][
                                            "location_id"],
                                        "type_conversation": state_glic[j]["data"]["interaction"][i][
                                            "type_conversation"],
                                    }
                                )
                                if event_db and event_db["type_conversation"] in ["one_way", "two_way"]:
                                    state_glic[j]["data"]["interaction"][i]["event_id"] = str(event_db["_id"])
                            if (state_glic[j]["data"]["interaction"][i]["type_conversation"] in ["open_question",
                                                                                                 "option_multiple"]):
                                for k in range(
                                        len(state_glic[j]["data"]["interaction"][i]["options_dialog"]["options"])
                                ):
                                    type_conversation = (
                                        state_glic[j]["data"]["interaction"][i]["conversation_type"]
                                        if state_glic[j]["data"]["interaction"][i].get(
                                            "conversation_type", None
                                        )
                                        else state_glic[j]["data"]["interaction"][i].get(
                                            "type_conversation", None
                                        )
                                    )
                                    event_db = await db["event"].find_one(
                                        {
                                            "game_id": state_glic[j]["data"]["game_id"],
                                            "character_id": state_glic[j]["element_id"],
                                            "state_game_init": state_glic[j]["state"],
                                            "location_state_game_init": state_glic[j]["data"][
                                                "interaction"][i]["location_id"], "option_number": k,
                                            "type_conversation": type_conversation,
                                        }
                                    )
                                    if event_db and event_db["type_conversation"] in [
                                        "open_question",
                                        "option_multiple",
                                    ]:
                                        state_glic[j]["data"]["interaction"][i]["options_dialog"]["options"][
                                            event_db["option_number"]]["event_id"] = str(event_db["_id"])
        return state_glic
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        pass
