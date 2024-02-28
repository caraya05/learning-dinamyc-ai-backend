import json

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme

from customize.schemas import SchemaRetrieveCustomize
from customize.services import get_customize_by_field

router = APIRouter(prefix='/customizes', tags=['Customizes'])


def get_db(request: Request):
    return request.state.db


@router.get("/customize/{customize_id}", response_model=SchemaRetrieveCustomize)
async def get_customize_by_id(customize_id: str,
                              db: Session = Depends(get_db),
                              Authorize: AuthJWT = Depends(),
                              Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                              ):
    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    customize_db = get_customize_by_field(db, 'id', customize_id)
    return customize_db
