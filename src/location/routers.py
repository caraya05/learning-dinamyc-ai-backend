from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme

from location.schemas import SchemaListLocation
from location.schemas import SchemaRetrieveLocation
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation

from location.services import get_locations_service, get_location_by_field
from location.services import get_location_service
from location.services import create_location_service
from location.services import partial_update_location_service

router = APIRouter(prefix="/location", tags=["Location"])


# Dependency
def get_db(request: Request):
    return request.state.db


@router.get("/by-field/", response_model=SchemaRetrieveLocation)
def get_locations(value: str,
                  field: str,
                  db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint retrieves a location.

    It expects the location's id in the request path.
    If the location is successfully retrieved, it returns the location's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    location_db = get_location_by_field(db, field, value)

    return location_db

@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListLocation)
def get_locations(game_id: str,
                  db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint retrieves all locations.

    It returns a list of locations.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    locations_db = get_locations_service(db, skip=0, limit=100,game_id=game_id)

    return locations_db


@router.get("/{location_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveLocation)
def get_location(location_id: str,
                 db: Session = Depends(get_db),
                 Authorize: AuthJWT = Depends(),
                 Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                 ):
    """
    This endpoint retrieves a location.

    It expects the location's id in the request path.
    If the location is successfully retrieved, it returns the location's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    location_db = get_location_service(db, location_id)

    return location_db


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveLocation)
def create_location(schema: SchemaCreateLocation,
                    db: Session = Depends(get_db),
                    Authorize: AuthJWT = Depends(),
                    Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                    ):
    """
    This endpoint creates a location.

    It expects the location's information in the request body.
    If the location is successfully created, it returns the location's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    location_db = create_location_service(db, schema, current_user)

    return location_db


@router.patch("/{location_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveLocation)
def partial_update_location(location_id: str,
                            schema: SchemaPartialUpdateLocation,
                            db: Session = Depends(get_db),
                            Authorize: AuthJWT = Depends(),
                            Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                            ):
    """
    This endpoint partially updates a location.

    It expects the location's id in the request path.
    It expects the location's information in the request body.
    If the location is successfully updated, it returns the location's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    location_db = partial_update_location_service(db, location_id, schema)

    return location_db
