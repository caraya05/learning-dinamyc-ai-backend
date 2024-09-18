from uuid import uuid4

from bson import ObjectId

from pydantic import BaseModel
from pydantic import Field

from core.database import db

from gpt_ai.utils import openai_generator

from prompt.services import get_prompt_by_category_service

from task.services import update_task_service

from utils import upload_image

async def async_generate_description_location_task(location_id: str):
    """
    Generate a description for a location.
    """
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
            prompt_db_location_place = await get_prompt_by_category_service("location_place")
            prompt_db_location_place["description"] = prompt_db_location_place["description"].replace(
                "{{PromptUserLocation}}", location_db["prompt_user"])
            json_description = {
                "description": "string (general description of the place, theme, appearance, max 50 words)",
                "description_floor": "string (detailed description of the apartment next to a wall, min 80 words and max 100 words)",
            }
            prompt_content = [
                {"role": "system",
                 "content": f"responde el prompt con la siguiente estructura JSON: {json_description}", },
                {"role": "user", "content": f"{prompt_db_location_place['description']}"},
            ]
            prompt_description = openai_generator.generate_gpt(
                content_prompt=prompt_content, type_text="scene cero", max_tokens=4096
            )
            response_prompt = json.loads(prompt_description)
            location_db["description"] = f"{response_prompt['description']} // {response_prompt['description_floor']}"

            sound_identification = await identify_by_location_service(description=response_prompt["description"])
            location_db["sound_id"] = sound_identification["id"]

            await db['location'].update_one({"_id": ObjectId(location_id)}, {"$set": location_db})
    except Exception as e:
        print(f"Error in generate description location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Description not generated.")