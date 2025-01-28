from uuid import uuid4
import traceback
from bson import ObjectId
from pydantic import BaseModel, Field

from character.tasks import generate_language_detection
from gpt_ai.utils import openai_generator
from prompt.services import get_prompt_by_category_service
from task.services import update_task_service
from utils import upload_image

from core.database import db


async def generate_image_item(prompt_user: str, object_id: str, user_id: str, state_game_id: str):
    try:
        prompt_db_image_object = await get_prompt_by_category_service('image_object')
        prompt_object = prompt_db_image_object.get("description").replace("x_object", prompt_user)

        validate_prompt = await openai_generator.moderation_text(
            text=prompt_object
        )

        if validate_prompt:
            return False, "Prompt not allowed"

        image_item = await openai_generator.generate_image(
            prompt=prompt_object,
            quality="hd",
            size="1024x1024",
            user_id=user_id,
            type_generation="image_item",
        )
        image_object = upload_image(
            url_image=image_item,
            file_name=f"item/{uuid4()}.jpg",
            size=(512, 512),
        )
        # await db['item'].update_one({"_id": ObjectId(object_id)}, {"$set": {"image": image_object}})
        element_state_db = await db['state_glic'].find_one({"element_id": object_id, "state": state_game_id})

        element_state_db["data"]["image"] = image_object

        await db['state_glic'].update_one({
            "_id": element_state_db["_id"]
        }, {
            "$set": {
                "data": element_state_db["data"]
            }
        })

        return True, "Image item generated successfully"
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generate image: {str(e)}")
        return False , "Error in generate image item"


class SchemaCharacterConversation(BaseModel):
    id_item: str = Field(..., example="id_item", description="id of the item")
    dialog: str = Field(..., example="dialog", description="dialog of the item.")


class SchemaCharacterConversations(BaseModel):
    conversation: list[SchemaCharacterConversation] = Field(
        ..., example=[{"key": "value"}], description="conversation of the item"
    )


async def generate_conversation_item(prompt_user_dialog: str, object_id: str, user_id: str, state_game_id: str,
                                     location_id: str):
    try:

        language_detection = await generate_language_detection(prompt_user_dialog, user_id)

        element_state_db = await db['state_glic'].find_one({"element_id": object_id, "state": state_game_id})

        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f" You are a character dialogue " +
                               " conversation according to the json schema and the data provided by the user, and "
                               f"correct the spelling of the dialogue text in the {language_detection} language.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Item id: {object_id}",
                        },
                        {
                            "type": "text",
                            "text": f"Conversation item: {prompt_user_dialog}",
                        },
                    ],
                },
            ],
            model="gpt-4o-mini-2024-07-18",
            max_tokens=4096,
            response_format=SchemaCharacterConversations,
            user_id=user_id,
            type_generation="create_conversation_item",
        )
        conversation_ = [{"id_character": dialog.id_item, "dialog": dialog.dialog, "audio": None} for dialog
                         in response.conversation]

        # await db["item"].update_one(
        #     {"_id": ObjectId(object_id)},
        #     {
        #         "$set": {
        #             "conversation": conversation_,
        #         }
        #     },
        # )

        if element_state_db["data"].get("locations_id"):
            locations_array = element_state_db["data"]["locations_id"]
            locations_array.append(location_id)
            element_state_db["data"]["locations_id"] = locations_array
        else:
            element_state_db["data"]["locations_id"] = [location_id]

        interaction_exists = False

        if "interaction" not in element_state_db["data"]:
            element_state_db["data"]["interaction"] = []

        for interaction in element_state_db["data"]["interaction"]:
            if interaction["location_id"] == location_id and interaction["state_game"] == state_game_id:
                interaction["conversation"] = conversation_
                interaction_exists = True
                break

        if not interaction_exists:
            element_state_db["data"]["interaction"].append({
                "location_id": location_id,
                "state_game": state_game_id,
                "conversation": conversation_,
            })

        await db['state_glic'].update_one({
            "_id": element_state_db["_id"]
        }, {
            "$set": {
                "data": element_state_db["data"]
            }
        })

        return True
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in generate conversation: {str(e)}")
        return False


async def async_generate_item(item_id: str, _user_id: str, _task_id: str, _location_id: str, _state_game_id: str,
                              _game_id: str):
    await update_task_service(_id=_task_id, _status="pending")

    item_db = await db['item'].find_one({"_id": ObjectId(item_id)})

    element_state_db = await db['state_glic'].find_one({"element_id": item_id, "state": _state_game_id})

    if not item_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Item not found {item_id}",
        )
        return f"Item not found {item_id}"
    image_item, message = await generate_image_item(element_state_db["data"]["prompt_user"], item_id, _user_id, _state_game_id)

    if not image_item:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message=message,
            _status_updated=1,
        )
        return message

    conversation_item = await generate_conversation_item(element_state_db["data"]["prompt_user_dialog"], item_id,
                                                         _user_id, _state_game_id, _location_id)
    if not conversation_item:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Error in generate conversation item",
        )
        return f"Error in generate conversation item"

    await update_task_service(
        _id=_task_id, _status="completed", _message="Item generated successfully"
    )
    return "Item generated successfully"


async def async_updated_item(item_id: str, _user_id: str, _task_id: str, updated_prompt_user: bool,
                             updated_dialog: bool, state_game_id: str, _location_id: str):
    await update_task_service(_id=_task_id, _status="pending")

    item_db = await db['item'].find_one({"_id": ObjectId(item_id)})
    if not item_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Item not found {item_id}",
        )
        return f"Item not found {item_id}"
    if updated_prompt_user:

        image_item, message = await generate_image_item(item_db["prompt_user"], item_id, _user_id,state_game_id)

        if not image_item:
            await update_task_service(
                _id=_task_id,
                _status="failed",
                _message=message,
                _status_updated=1,
            )
            return message

    if updated_dialog:
        conversation_item = await generate_conversation_item(item_db["prompt_user_dialog"], item_id, _user_id, state_game_id, _location_id)
        if not conversation_item:
            await update_task_service(
                _id=_task_id,
                _status="failed",
                _message="Error in generate conversation item",
            )
            return f"Error in generate conversation item"

    await update_task_service(
        _id=_task_id, _status="completed", _message="Item generated successfully"
    )
    return "Item generated successfully"


async def async_generate_new_interaction_item(_task_id: str, _item_id: str, _prompt_user_dialog, _state_game_id: str,
                                              location_id: str,
                                              _user_id: str):

    await update_task_service(_id=_task_id, _status="pending")

    item_db = await db['item'].find_one({"_id": ObjectId(_item_id)})
    if not item_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Item not found {_item_id}",
        )
        return f"Item not found {_item_id}"
    conversation_item = await generate_conversation_item(_prompt_user_dialog, _item_id, _user_id, _state_game_id,
                                                         location_id)
    if not conversation_item:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Error in generate conversation item",
        )
        return f"Error in generate conversation item"
    await update_task_service(
        _id=_task_id, _status="completed", _message="Item generated successfully"
    )
    return "Item generated successfully"
