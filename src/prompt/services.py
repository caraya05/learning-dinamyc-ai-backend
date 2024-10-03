from fastapi import HTTPException
from fastapi import status

from core.database import db

from bson import ObjectId

from prompt.models import Prompt
from prompt.schemas import SchemaPartialUpdatePrompt
from prompt.enums import PromptType


async def get_prompts_service(skip: int = 1, limit: int = 100):
    """
    Get a list of prompts.
    """
    if prompts_db := await db["prompt"].find().to_list(None):
        counts_prompts = len(prompts_db)
        if prompts_db := await db["prompt"].find().skip(skip).limit(limit).to_list(None):
            return prompts_db, counts_prompts

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Prompts not found",
    )


async def get_prompt_service(_id: str):
    """
    Get a prompt.
    """
    if prompt_db := await db["prompt"].find_one({"_id": ObjectId(_id)}):
        return prompt_db
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Prompt not found",
    )


async def get_prompt_by_category_service(category: str):
    """
    Get a prompt by category.
    """
    if prompt_db := await db["prompt"].find_one({"category": category}):
        return prompt_db
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Prompt not found",
    )


async def create_prompt_service(schema: Prompt):
    """
    Create a prompt.
    """
    if schema.category not in [category.value for category in PromptType]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category",
        )

    try:
        if prompt_created := await db["prompt"].insert_one(schema.dict()):
            if prompt_created.inserted_id:
                prompt_db = await db["prompt"].find_one({"_id": prompt_created.inserted_id})
                return prompt_db
    except Exception as e:
        print(f"Error creating prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt not created",
        )


async def update_prompt_service(_id: str, schema: SchemaPartialUpdatePrompt):
    """
    Partially update a prompt.
    """
    try:
        if prompt_updated := await db["prompt"].update_one(
            {"_id": ObjectId(_id)}, {"$set": schema.dict()}
        ):
            if prompt_updated.modified_count:
                prompt_db = await db["prompt"].find_one({"_id": ObjectId(_id)})
                return prompt_db
    except Exception as e:
        print(f"Error updating prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt not updated",
        )


async def delete_prompt_service(_id: str):
    """
    Delete a prompt.
    """
    try:
        if prompt_deleted := await db["prompt"].delete_one({"_id": ObjectId(_id)}):
            if prompt_deleted.deleted_count:
                return True
    except Exception as e:
        print(f"Error deleting prompt: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Prompt not found",
    )
