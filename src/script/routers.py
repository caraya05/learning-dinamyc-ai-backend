from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme

from script.schemas import SchemaListScript
from script.schemas import SchemaRetrieveScript
from script.schemas import SchemaCreateScript
from script.schemas import SchemaPartialUpdateScript

from script.services import get_scripts_service
from script.services import get_script_service
from script.services import create_script_service
from script.services import partial_update_script_service

router = APIRouter(prefix="/script", tags=["Script"])


# Dependency
def get_db(request: Request):
    return request.state.db


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListScript)
def get_scripts(db: Session = Depends(get_db),
                Authorize: AuthJWT = Depends(),
                Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                ):
    """
    This endpoint retrieves all scripts.

    It returns a list of scripts.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    scripts_db = get_scripts_service(db, skip=0, limit=100)

    return SchemaListScript(results=scripts_db, count=len(scripts_db))


@router.get("/{script_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScript)
def get_script(script_id: str,
               db: Session = Depends(get_db),
               Authorize: AuthJWT = Depends(),
               Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
               ):
    """
    This endpoint retrieves a script.

    It returns a script.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    script_db = get_script_service(db, script_id=script_id)

    return SchemaRetrieveScript(**script_db)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveScript)
def create_script(script: SchemaCreateScript,
                  db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint creates a script.

    It expects a script in the request body.
    If the script is successfully created, it returns the script's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    script_db = create_script_service(db, schema=script)

    return SchemaRetrieveScript(**script_db)


@router.patch("/{script_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveScript)
def partial_update_script(script_id: str,
                          schema: SchemaPartialUpdateScript,
                          db: Session = Depends(get_db),
                          Authorize: AuthJWT = Depends(),
                          Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                          ):
    """
    This endpoint partially updates a script.

    It expects a script in the request body.
    If the script is successfully updated, it returns the script's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    script_db = partial_update_script_service(db, script_id=script_id, schema=schema)

    return SchemaRetrieveScript(**script_db)
