from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from customize.schemas import SchemaRetrieveCustomize
from customize.services import get_customize_by_id_service

router = APIRouter(prefix='/customizes', tags=['Customizes'])


@router.get("/{customize_id}", response_model=SchemaRetrieveCustomize)
async def get_customize_by_id(
        customize_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    try:
        customize_db = await get_customize_by_id_service(customize_id)
        return customize_db
    except Exception as e:
        print(f"error in get customize by id: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customize not found",
        )
