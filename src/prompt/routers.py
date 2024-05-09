from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.utils import auth_schema

from auth.auth import auth
from auth.auth import auth_admin

from prompt.models import Prompt

from prompt.schemas import SchemaListPrompt
from prompt.schemas import SchemaRetrievePrompt
from prompt.schemas import SchemaCreatePrompt
from prompt.schemas import SchemaPartialUpdatePrompt

from prompt.services import get_prompts_service
from prompt.services import get_prompt_service
from prompt.services import create_prompt_service
from prompt.services import update_prompt_service
from prompt.services import delete_prompt_service

router = APIRouter(prefix="/prompt", tags=["Prompt"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListPrompt)
async def get_prompts(
        limit: int = 100,
        skip: int = 0,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema)
):
    """
    This endpoint retrieves all prompts.

    It returns a list of prompts.
    """
    try:
        prompts_db, count = await get_prompts_service(skip=skip, limit=limit)
        for prompt in prompts_db:
            prompt["_id"] = str(prompt["_id"])

        return SchemaListPrompt(results=prompts_db, count=count)
    except Exception as e:
        print(f"Error getting prompts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompts not found",
        )


@router.get("/{prompt_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrievePrompt)
async def get_prompt(
        prompt_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a single prompt.

    It returns a single prompt.
    """
    try:
        prompt_db = await get_prompt_service(_id=prompt_id)
        return prompt_db
    except Exception as e:
        print(f"Error get prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrievePrompt)
async def create_prompt(
        prompt: SchemaCreatePrompt,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a prompt.

    It returns a single prompt.
    """
    try:
        prompt_created = Prompt(**prompt.dict(),
                                created_by=str(user_db.get("_id")),
                                updated_by=str(user_db.get("_id")))

        prompt_db = await create_prompt_service(schema=prompt_created)

        return prompt_db
    except Exception as e:
        print(f"Error create prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt not created",
        )


@router.put("/{prompt_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrievePrompt)
async def update_prompt(
        prompt_id: str,
        prompt: SchemaPartialUpdatePrompt,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint partially updates a prompt.

    It returns a single prompt.
    """
    try:
        return await update_prompt_service(_id=prompt_id, schema=prompt)
    except Exception as e:
        print(f"Error update prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
        prompt_id: str,
        user_db: dict = Depends(auth_admin),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint deletes a prompt.

    It returns a single prompt.
    """
    try:
        return await delete_prompt_service(_id=prompt_id)
    except Exception as e:
        print(f"Error delete prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )
