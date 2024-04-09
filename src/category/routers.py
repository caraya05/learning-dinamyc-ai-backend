from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme

from category.schemas import SchemaListCategory

from category.services import get_categories_active_service

router = APIRouter(prefix="/category", tags=["Category"])


# Dependency
def get_db(request: Request):
    return request.state.db


@router.get("/", response_model=SchemaListCategory)
def get_categories(db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint retrieves a list of categories.

    It expects the category's id in the request path.
    If the category is successfully retrieved, it returns the category's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return get_categories_active_service(db)