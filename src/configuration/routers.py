from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme

from configuration.services import get_configuration_service
from configuration.schemas import SchemaRetrieveConfiguration

router = APIRouter(prefix="/configuration", tags=["Configuration"])


# Dependency
def get_db(request: Request):
    return request.state.db


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveConfiguration)
async def get_configuration(db: Session = Depends(get_db),
                            Authorize: AuthJWT = Depends(),
                            Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                            ):
    try:
        Authorize.jwt_required()
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error Authorization", headers={"WWW-Authenticate": str(ex)}
        ) from ex
    return get_configuration_service(db)
