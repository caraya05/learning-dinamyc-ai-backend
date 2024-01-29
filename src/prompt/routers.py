from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme

from prompt.schemas import SchemaListPrompt
from prompt.schemas import SchemaRetrievePrompt
from prompt.schemas import SchemaCreatePrompt
from prompt.schemas import SchemaPartialUpdatePrompt

from prompt.services import get_prompts_service
from prompt.services import get_prompt_service
from prompt.services import create_prompt_service
from prompt.services import partial_update_prompt_service

router = APIRouter(prefix="/prompt", tags=["Prompt"])


# Dependency
def get_db(request: Request):
    return request.state.db


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListPrompt)
def get_prompts(db: Session = Depends(get_db),
                Authorize: AuthJWT = Depends(),
                Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                ):
    """
    This endpoint retrieves all prompts.

    It returns a list of prompts.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    prompts_db = get_prompts_service(db, skip=0, limit=100)

    return SchemaListPrompt(results=prompts_db, count=len(prompts_db))


@router.get("/{prompt_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrievePrompt)
def get_prompt(prompt_id: str,
               db: Session = Depends(get_db),
               Authorize: AuthJWT = Depends(),
               Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
               ):
    """
    This endpoint retrieves a single prompt.

    It returns a single prompt.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    prompt_db = get_prompt_service(db, prompt_id=prompt_id)

    return SchemaRetrievePrompt(**prompt_db)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrievePrompt)
def create_prompt(prompt: SchemaCreatePrompt,
                  db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint creates a prompt.

    It returns a single prompt.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    prompt_db = create_prompt_service(db, schema=prompt)

    return SchemaRetrievePrompt(**prompt_db)


@router.patch("/{prompt_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrievePrompt)
def partial_update_prompt(prompt_id: str,
                          prompt: SchemaPartialUpdatePrompt,
                          db: Session = Depends(get_db),
                          Authorize: AuthJWT = Depends(),
                          Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                          ):
    """
    This endpoint partially updates a prompt.

    It returns a single prompt.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    prompt_db = partial_update_prompt_service(db, prompt_id=prompt_id, schema=prompt)

    return SchemaRetrievePrompt(**prompt_db)
