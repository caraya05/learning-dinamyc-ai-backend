from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from config import auth_scheme

from .services import get_current_user_service
from .services import create_user_service
from .services import update_user_service
from .services import partial_update_user_service
from .services import update_password_service

from .schemas import SchemaRetrieveUser
from .schemas import SchemaUser
from .schemas import SchemaUpdateUser
from .schemas import SchemaPartialUpdateUser
from .schemas import SchemaUpdatePassword

router = APIRouter(prefix="/user", tags=["User"])


# Dependency
def get_db(request: Request):
    return request.state.db


@router.post("/", response_model=SchemaRetrieveUser, status_code=status.HTTP_201_CREATED)
async def create_user(user: SchemaUser, db: Session = Depends(get_db)):
    """
    This endpoint creates a new user.

    It expects the user's information in the request body. If the user is successfully created, it returns the user's information.
    If the user already exists, it raises an HTTPException with status code 400.

    Parameters:
    user (SchemaUser): The user's information to be created.
    db (Session): Database session for executing queries.

    Returns:
    SchemaRetrieveUser: The created user's information.

    Raises:
    HTTPException: If the user already exists, an HTTPException is raised with status code 400.
    """
    db_user = create_user_service(db=db, user=user)
    if db_user:
        return db_user
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered",
        )

@router.get("/current-user", response_model=SchemaRetrieveUser)
async def get_current_user(
        db: Session = Depends(get_db),
        Authorize: AuthJWT = Depends(),
        Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """
    This endpoint retrieves the current user's information.

    It uses JWT for authentication. The JWT token is expected to be provided in the Authorization header.

    Parameters:
    db (Session): Database session for executing queries.
    Authorize (AuthJWT): An instance of AuthJWT for handling JWT operations.
    Token (HTTPAuthorizationCredentials): The JWT token from the Authorization header.

    Returns:
    SchemaRetrieveUser: The current user's information.

    Raises:
    HTTPException: If there is an error in getting the user's information, an HTTPException is raised with status code 400.
    """

    try:
        # Check if the JWT token is valid
        Authorize.jwt_required()

        # Retrieve the current user's information
        return get_current_user_service(db, Authorize.get_raw_jwt())
    except Exception as ex:
        # If there is an error, raise an HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
        ) from ex


@router.put("/{id}", response_model=SchemaRetrieveUser)
async def update_user(id: str,
                      user: SchemaUpdateUser,
                      db: Session = Depends(get_db),
                      Authorize: AuthJWT = Depends(),
                      Token: HTTPAuthorizationCredentials = Depends(auth_scheme)
                      ):
    """
    This endpoint updates a user's information.

    It uses JWT for authentication. The JWT token is expected to be provided in the Authorization header.
    The user's updated information is expected in the request body.

    Parameters:
    id (str): The id of the user to be updated.
    user (SchemaUpdateUser): The updated user's information.
    db (Session): Database session for executing queries.
    Authorize (AuthJWT): An instance of AuthJWT for handling JWT operations.
    Token (HTTPAuthorizationCredentials): The JWT token from the Authorization header.

    Returns:
    SchemaRetrieveUser: The updated user's information.

    Raises:
    HTTPException: If there is an error in updating the user's information or if the user id does not match the id in the JWT token, an HTTPException is raised with status code 400.
    """
    try:
        # Check if the JWT token is valid
        Authorize.jwt_required()

        # Retrieve the current user's information
        user_current = get_current_user_service(db, Authorize.get_raw_jwt())

        # Check if the user id matches the id in the JWT token
        if not user_current.id == id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
            )

        # Update the user's information
        return update_user_service(db=db, user_id=id, user_update=user)
    except Exception as ex:
        # If there is an error, raise an HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
        ) from ex


@router.patch("/{id}", response_model=SchemaRetrieveUser)
async def partial_update_user(id: str,
                              user: SchemaPartialUpdateUser,
                              db: Session = Depends(get_db),
                              Authorize: AuthJWT = Depends(),
                              Token: HTTPAuthorizationCredentials = Depends(auth_scheme)
                              ):
    """
    This endpoint partially updates a user's information.

    It uses JWT for authentication. The JWT token is expected to be provided in the Authorization header.
    The user's updated information is expected in the request body.

    Parameters:
    id (str): The id of the user to be updated.
    user (SchemaPartialUpdateUser): The updated user's information.
    db (Session): Database session for executing queries.
    Authorize (AuthJWT): An instance of AuthJWT for handling JWT operations.
    Token (HTTPAuthorizationCredentials): The JWT token from the Authorization header.

    Returns:
    SchemaRetrieveUser: The updated user's information.

    Raises:
    HTTPException: If there is an error in updating the user's information or if the user id does not match the id in the JWT token, an HTTPException is raised with status code 400.
    """
    try:
        # Check if the JWT token is valid
        Authorize.jwt_required()

        # Retrieve the current user's information
        user_current = get_current_user_service(db, Authorize.get_raw_jwt())

        # Check if the user id matches the id in the JWT token
        if not user_current.id == id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
            )

        # Partially update the user's information
        return partial_update_user_service(db=db, user_id=id, user_update=user)
    except Exception as ex:
        # If there is an error, raise an HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
        ) from ex


@router.post("/update-password", response_model=SchemaRetrieveUser)
async def update_password(change_password: SchemaUpdatePassword,
                          db: Session = Depends(get_db),
                          ):
    """
    This endpoint updates a user's password.

    It expects the user's new password in the request body. If the password is successfully updated, it returns the user's information.
    If there is an error in updating the password, it raises an HTTPException with status code 400.

    Parameters:
    change_password (SchemaUpdatePassword): The user's new password.
    db (Session): Database session for executing queries.

    Returns:
    SchemaRetrieveUser: The user's information after the password update.

    Raises:
    HTTPException: If there is an error in updating the password, an HTTPException is raised with status code 400.
    """
    try:
        return update_password_service(db=db, change_password=change_password)
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error in updating the password"
        ) from ex


from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr
from starlette.responses import JSONResponse


class EmailSchema(BaseModel):
    email: list[EmailStr]


conf = ConnectionConfig(
    MAIL_USERNAME="soporte.varios.proyectos@gmail.com",
    MAIL_PASSWORD="popjtzxkeygvjmuv",
    MAIL_FROM="soporte.varios.proyectos@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

html = """
<html>
<head>
<style>
body {
    color: gray;
}
h1 {
    color: blue;
}
p {
    color: orange;
}
</style>
</head>
<body>
<h1>Bienvenido a Prospero</h1>
<p>Estamos encantados de tenerle con nosotros. Esperamos que disfrute de nuestros servicios.</p>
</body>
</html>
"""


@router.post("/email")
async def simple_send(email: EmailSchema) -> JSONResponse:
    message = MessageSchema(
        subject="Fastapi-Mail module",
        recipients=email.dict().get("email"),
        body=html,
        subtype=MessageType.html)

    fm = FastMail(conf)
    await fm.send_message(message)
    return JSONResponse(status_code=200, content={"message": "email has been sent"})
