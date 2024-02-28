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
async def get_customize_by_id(customize_id: str, db: Session = Depends(get_db)):
    customize_db = get_customize_by_field(db, 'id', customize_id)
    return customize_db
