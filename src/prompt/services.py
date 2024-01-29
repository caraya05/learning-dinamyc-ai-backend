from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from prompt.models import Prompt

from prompt.schemas import SchemaRetrievePrompt
from prompt.schemas import SchemaCreatePrompt
from prompt.schemas import SchemaPartialUpdatePrompt
from prompt.schemas import SchemaListPrompt


def get_prompt_by_field(db: Session, field: str, value: str):
    """
    Get a prompt by a field.
    """
    prompt = db.query(Prompt).filter(getattr(Prompt, field) == value).first()
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prompt with {field} {value} not found")
    return prompt


def get_prompts_service(db: Session, skip: int = 0, limit: int = 100):
    """
    Get a list of prompts.
    """
    prompts = db.query(Prompt).offset(skip).limit(limit).all()
    return SchemaListPrompt(results=prompts, count=len(prompts))


def get_prompt_service(db: Session, prompt_id: str):
    """
    Get a prompt.
    """
    prompt = get_prompt_by_field(db, "id", prompt_id)
    return SchemaRetrievePrompt.from_orm(prompt)


def create_prompt_service(db: Session, schema: SchemaCreatePrompt):
    """
    Create a prompt.
    """
    prompt = Prompt(**schema.dict())
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return SchemaRetrievePrompt.from_orm(prompt)


def partial_update_prompt_service(db: Session, prompt_id: str, schema: SchemaPartialUpdatePrompt):
    """
    Partially update a prompt.
    """
    prompt = get_prompt_by_field(db, "id", prompt_id)
    for field, value in schema:
        setattr(prompt, field, value)
    db.commit()
    db.refresh(prompt)
    return SchemaRetrievePrompt.from_orm(prompt)
