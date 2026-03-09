import traceback

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi import UploadFile
from fastapi import File
from fastapi.security import HTTPAuthorizationCredentials
from uuid import uuid4

from utils import upload_image

from user.services import get_user_by_id_service, joint_user_waitlist_service
from user.services import create_user_service
from user.services import update_photo_service
from user.services import update_attempt_to_create_service

from user.schemas import SchemaRetrieveUser
from user.schemas import SchemaUser

from auth.utils import auth_schema
from auth.auth import auth
from PIL import Image
from io import BytesIO

router = APIRouter(prefix="/user", tags=["User"])


@router.post(
    "/",
    response_model=SchemaRetrieveUser,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_user(user: SchemaUser):
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
    db_user = await create_user_service(user=user)
    if db_user:
        return db_user
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered",
        )


@router.get("/current-user", response_model=SchemaRetrieveUser)
async def get_current_user(
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
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
        return user_db
    except Exception as ex:
        # If there is an error, raise an HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
        ) from ex


@router.get("/{user_id}", response_model=SchemaRetrieveUser)
async def get_user(
        user_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
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
        # Authorize.jwt_required()

        # Retrieve the current user's information
        return await get_user_by_id_service(user_id=str(user_id))
    except Exception as ex:
        # If there is an error, raise an HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
        ) from ex


@router.get("/validate-stars/", status_code=status.HTTP_200_OK)
async def validate_stars(
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    if user_db['stars'] is None or user_db['stars'] <= 0:
        await update_attempt_to_create_service(str(user_db['_id']))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough stars")
    return {"message": "Stars are enough"}


# update photo user
@router.post("/update-photo/", response_model=SchemaRetrieveUser)
async def update_photo_user(
        photo: UploadFile = File(...),
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    photo_content = await photo.read()

    url_photo = upload_image(
        # name_bucket="users",
        image_content_type=photo_content,
        file_name=f"user/{uuid4()}.jpg",
        size=(512, 512),
    )

    return await update_photo_service(user_id=str(user_db['_id']), photo=url_photo)


@router.post(
    "/joint-waitlist/wait",
    response_model=SchemaRetrieveUser,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_user(user: SchemaUser):
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
    user.password = user.email
    db_user = await joint_user_waitlist_service(user=user)
    if db_user:
        return db_user
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered",
        )

# @router.put("/{id}", response_model=SchemaRetrieveUser)
# async def update_user(id: str,
#                       user: SchemaUpdateUser,
#                       db: Session = Depends(get_db),
#                       Authorize: AuthJWT = Depends(),
#                       Token: HTTPAuthorizationCredentials = Depends(auth_scheme)
#                       ):
#     """
#     This endpoint updates a user's information.
#
#     It uses JWT for authentication. The JWT token is expected to be provided in the Authorization header.
#     The user's updated information is expected in the request body.
#
#     Parameters:
#     id (str): The id of the user to be updated.
#     user (SchemaUpdateUser): The updated user's information.
#     db (Session): Database session for executing queries.
#     Authorize (AuthJWT): An instance of AuthJWT for handling JWT operations.
#     Token (HTTPAuthorizationCredentials): The JWT token from the Authorization header.
#
#     Returns:
#     SchemaRetrieveUser: The updated user's information.
#
#     Raises:
#     HTTPException: If there is an error in updating the user's information or if the user id does not match the id in the JWT token, an HTTPException is raised with status code 400.
#     """
#     try:
#         # Check if the JWT token is valid
#         Authorize.jwt_required()
#
#         # Retrieve the current user's information
#         user_current = get_current_user_service(db, Authorize.get_raw_jwt())
#
#         # Check if the user id matches the id in the JWT token
#         if not user_current.id == id:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
#             )
#
#         # Update the user's information
#         return update_user_service(db=db, user_id=id, user_update=user)
#     except Exception as ex:
#         # If there is an error, raise an HTTPException
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
#         ) from ex


# @router.patch("/{id}", response_model=SchemaRetrieveUser)
# async def partial_update_user(id: str,
#                               user: SchemaPartialUpdateUser,
#                               db: Session = Depends(get_db),
#                               Authorize: AuthJWT = Depends(),
#                               Token: HTTPAuthorizationCredentials = Depends(auth_scheme)
#                               ):
#     """
#     This endpoint partially updates a user's information.
#
#     It uses JWT for authentication. The JWT token is expected to be provided in the Authorization header.
#     The user's updated information is expected in the request body.
#
#     Parameters:
#     id (str): The id of the user to be updated.
#     user (SchemaPartialUpdateUser): The updated user's information.
#     db (Session): Database session for executing queries.
#     Authorize (AuthJWT): An instance of AuthJWT for handling JWT operations.
#     Token (HTTPAuthorizationCredentials): The JWT token from the Authorization header.
#
#     Returns:
#     SchemaRetrieveUser: The updated user's information.
#
#     Raises:
#     HTTPException: If there is an error in updating the user's information or if the user id does not match the id in the JWT token, an HTTPException is raised with status code 400.
#     """
#     try:
#         # Check if the JWT token is valid
#         Authorize.jwt_required()
#
#         # Retrieve the current user's information
#         user_current = get_current_user_service(db, Authorize.get_raw_jwt())
#
#         # Check if the user id matches the id in the JWT token
#         if not user_current.id == id:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
#             )
#
#         # Partially update the user's information
#         return partial_update_user_service(db=db, user_id=id, user_update=user)
#     except Exception as ex:
#         # If there is an error, raise an HTTPException
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Error in the getting user"
#         ) from ex


# @router.post("/update-password", response_model=SchemaRetrieveUser)
# async def update_password(change_password: SchemaUpdatePassword,
#                           db: Session = Depends(get_db),
#                           ):
#     """
#     This endpoint updates a user's password.
#
#     It expects the user's new password in the request body. If the password is successfully updated, it returns the user's information.
#     If there is an error in updating the password, it raises an HTTPException with status code 400.
#
#     Parameters:
#     change_password (SchemaUpdatePassword): The user's new password.
#     db (Session): Database session for executing queries.
#
#     Returns:
#     SchemaRetrieveUser: The user's information after the password update.
#
#     Raises:
#     HTTPException: If there is an error in updating the password, an HTTPException is raised with status code 400.
#     """
#     try:
#         return update_password_service(db=db, change_password=change_password)
#     except Exception as ex:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Error in updating the password"
#         ) from ex

#
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr
from starlette.responses import JSONResponse
from typing import List


class EmailSchema(BaseModel):
    email: List[str]


conf = ConnectionConfig(
    MAIL_USERNAME="soporte.varios.proyectos@gmail.com",
    MAIL_PASSWORD="popjtzxkeygvjmuv",
    MAIL_FROM="soporte.varios.proyectos@gmail.com",
    MAIL_PORT=465,  # Puerto para SSL
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


@router.post("/email")
async def simple_send(
        email: List[EmailStr],
        request_body: str,
        file: UploadFile = File(None),
) -> JSONResponse:
    try:
        attachments = [file] if file else None

        html = f"""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xmlns="http://www.w3.org/1999/xhtml" style="color-scheme: light dark; supported-color-schemes: light dark;">
          <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <meta name="x-apple-disable-message-reformatting" />
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
            <meta name="color-scheme" content="light dark" />
            <meta name="supported-color-schemes" content="light dark" />
            <title></title>
            <style>
              body {{
                background-color: #f3f4f6;
                color: #1f2937;
                font-family: Arial, sans-serif;
              }}
              .container {{
                max-width: 640px;
                margin: 0 auto;
                padding: 24px;
                background-color: #ffffff;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-radius: 8px;
              }}
              .header {{
                text-align: center;
                padding: 24px 0;
              }}
              .header h1 {{
                font-size: 1.5rem;
                font-weight: bold;
                color: #ffffff;
                background-color: #ec4899;
                padding: 8px;
                border-radius: 4px;
                display: inline-block;
              }}
              .title {{
                font-size: 1.125rem;
                font-weight: 600;
                color: #4b5563;
              }}
              .text {{
                margin-top: 16px;
                font-size: 0.875rem;
                color: #374151;
              }}
              .text span {{
                font-family: monospace;
                color: #6b7280;
              }}
            </style>
          </head>
        <body>
        <div class="container">
            <div class="header">
                <h1>Qwestar</h1>
            </div>
            <h2 class="title">Solicitud de Creación de Juego</h2>
            <p class="text">
                La siguiente empresa ha solicitado la creación de un juego con la siguiente información:
            </p>
            <p class="text">Contacto: <span>{request_body}</span></p>
            <p class="text">Descripción de la solicitud: <span>{request_body}</span></p>
            <p class="text">Archivo: <span>{file.filename if file else "No se proporcionó archivo"}</span></p>
        </div>
        </body>
        </html>
        """

        message = MessageSchema(
            subject="!Nueva Solicitud de Creación de Juego!",
            recipients=email,
            body=html,
            subtype=MessageType.html,
            attachments=attachments
        )

        fm = FastMail(conf)
        await fm.send_message(message)
        return JSONResponse(status_code=200, content={"message": "email has been sent"})
    except Exception as e:
        print(traceback.print_exc())
        return JSONResponse(status_code=500, content={"message": str(e)})
