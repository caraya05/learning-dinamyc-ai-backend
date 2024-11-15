from uuid import uuid4

from bson import ObjectId

from gpt_ai.utils import openai_generator
from prompt.services import get_prompt_by_category_service
from task.services import update_task_service
from utils import upload_image

from core.database import db


async def generate_image_item(prompt_user: str, object_id: str, user_id: str):
    try:
        prompt_db_image_object = await get_prompt_by_category_service('image_object')
        prompt_object = prompt_db_image_object.get("description").replace("x_object", prompt_user)
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
        await db['item'].update_one({"_id": ObjectId(object_id)}, {"$set": {"image": image_object}})
        return True
    except Exception as e:
        print(f"Error in generate image: {str(e)}")
        return False


async def async_generate_item(item_id: str, _user_id: str, _task_id: str):
    await update_task_service(_id=_task_id, _status="pending")

    print(
        f"Generating image item for item_id: {item_id}, user_id: {_user_id}, task_id: {_task_id}"
    )

    item_db = await db['item'].find_one({"_id": ObjectId(item_id)})
    if not item_db:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Item not found {item_id}",
        )
        return f"Item not found {item_id}"
    image_item = await generate_image_item(item_db["prompt_user"], item_id, _user_id)

    if not image_item:
        await update_task_service(
            _id=_task_id,
            _status="failed",
            _message="Error in generate image item",
        )
        return f"Error in generate image item"

    return True
