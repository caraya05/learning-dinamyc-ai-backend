import traceback
import uuid
import jwt
import requests

from PIL import Image
from io import BytesIO

from boto3 import session

from fastapi import UploadFile
from fastapi import HTTPException
from fastapi import status

from google.cloud import storage

from config import settings

session = session.Session()


from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig
from starlette.responses import JSONResponse
from typing import List, Optional

def generate_uuid():
    return str(uuid.uuid4())


# def upload_image(
#     size: tuple[int, int],
#     file_name: str,
#     image_content_type: any = None,
#     url_image: str = None,
#     name_bucket: str = 'backend',
#     img_byte_arr: any = None,
# ):
#     try:
#         if not img_byte_arr:
#             if image_content_type and not url_image:
#                 img = Image.open(BytesIO(image_content_type))
#             else:
#                 image_url = requests.get(url_image)
#                 img = Image.open(BytesIO(image_url.content))
#             img = img.resize(size=size, reducing_gap=2.0)
#
#             # Save the image to a BytesIO object
#             img_byte_arr = BytesIO()
#             img.save(img_byte_arr, format='JPEG')
#             img_byte_arr = img_byte_arr.getvalue()
#         else:
#             img_byte_arr = img_byte_arr
#
#         client = session.client(
#             's3',
#             region_name='qwestar',
#             endpoint_url='https://qwestar.sfo3.digitaloceanspaces.com',
#             aws_access_key_id=settings.ACCESS_ID_DIGITAL_OCEAN,
#             aws_secret_access_key=settings.SECRET_KEY_DIGITAL_OCEAN,
#         )
#
#         response = client.put_object(
#             Bucket=name_bucket,
#             Key=file_name,
#             Body=img_byte_arr,
#             ACL='public-read',
#             ContentType='image/jpeg',
#         )
#         return f"{settings.URL_DIGITAL_OCEAN}{file_name}"
#     except Exception as e:
#         print(f"Error uploading image: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Error resizing image",
#         )


def upload_audio(*,
                 file_name: str,
                 name_bucket: str = 'qwestar',
                 audio_byte_arr: any = None):
    try:
        if not audio_byte_arr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron datos de audio.",
            )

        # Convertir a BytesIO si es necesario
        if isinstance(audio_byte_arr, bytes):
            audio_byte_arr = BytesIO(audio_byte_arr)
            audio_byte_arr.seek(0)

        # Determinar el content_type según la extensión
        if file_name.lower().endswith('.mp3'):
            content_type = 'audio/mpeg'
        elif file_name.lower().endswith('.ogg'):
            content_type = 'audio/ogg'
        else:
            content_type = 'application/octet-stream'  # valor por defecto

        # Subir el archivo a Google Cloud Storage
        storage_client = storage.Client.from_service_account_json("credentials.json")
        bucket = storage_client.bucket(name_bucket)
        blob = bucket.blob(file_name)
        blob.upload_from_file(audio_byte_arr, content_type=content_type)
        return f"https://storage.googleapis.com/{name_bucket}/{file_name}"
    except Exception as e:
        print(f"Error uploading audio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al subir el archivo de audio.",
        )


def upload_image(
        size: tuple[int, int],
        file_name: str,
        image_content_type: any = None,
        url_image: str = None,
        name_bucket: str = 'qwestar',
        img_byte_arr: any = None,
):
    try:
        if not img_byte_arr:
            if image_content_type and not url_image:
                img = Image.open(BytesIO(image_content_type))
            else:
                image_url = requests.get(url_image)
                img = Image.open(BytesIO(image_url.content))
            img = img.resize(size=size, reducing_gap=2.0)

            # Save the image to a BytesIO object
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)  # Reiniciar el puntero del archivo
        else:
            # Convertir a BytesIO si es un objeto de tipo bytes
            if isinstance(img_byte_arr, bytes):
                temp = BytesIO(img_byte_arr)
                temp.seek(0)
                img_byte_arr = temp

        # Subir la imagen a Google Cloud Storage
        storage_client = storage.Client.from_service_account_json("credentials.json")
        bucket = storage_client.bucket(name_bucket)
        blob = bucket.blob(file_name)
        blob.upload_from_file(img_byte_arr, content_type='image/jpeg')
        return f"https://storage.googleapis.com/{name_bucket}/{file_name}"
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error uploading file",
        )


def upload_image_from_url(
        file_name: str,
        url_image: str,
        name_bucket: str = 'qwestar',
):
    try:
        # Descargar la imagen desde la URL
        response = requests.get(url_image)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo descargar la imagen desde la URL.",
            )

        # Convertir el contenido descargado a un objeto BytesIO
        img_byte_arr = BytesIO(response.content)
        img_byte_arr.seek(0)  # Reiniciar el puntero del archivo

        # Subir la imagen a Google Cloud Storage
        storage_client = storage.Client.from_service_account_json("credentials.json")
        bucket = storage_client.bucket(name_bucket)
        blob = bucket.blob(file_name)
        blob.upload_from_file(img_byte_arr, content_type='image/jpeg')
        return f"https://storage.googleapis.com/{name_bucket}/{file_name}"
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error uploading file",
        )


def get_sub_token(token: str):
    try:
        return jwt.decode(token, settings.authjwt_secret_key, algorithms="HS512")["sub"]
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error decoding token",
        )


def resize_image(image: UploadFile, size: tuple[int, int]) -> UploadFile:
    img = Image.open(BytesIO(image.file.read()))
    img = img.resize(size)
    img = img.convert("RGB")  # Convert image to RGB
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)  # Reset the file pointer to the beginning
    return UploadFile(file=img_byte_arr, filename=image.filename)


def delete_image(file_name: str, name_bucket: str = 'backend'):
    try:
        client = session.client(
            's3',
            region_name='qwestar',
            endpoint_url='https://qwestar.sfo3.digitaloceanspaces.com',
            aws_access_key_id=settings.ACCESS_ID_DIGITAL_OCEAN,
            aws_secret_access_key=settings.SECRET_KEY_DIGITAL_OCEAN,
        )

        response = client.delete_object(
            Bucket=name_bucket,
            Key=file_name.split(f'{name_bucket}/')[-1],
        )
        print("delete_image", response)
        return True
    except Exception as e:
        print(f"Error deleting image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error deleting image",
        )


def update_nested_dict(target, source):
    for key, value in source.items():
        if isinstance(value, dict):
            target[key] = update_nested_dict(target.get(key, {}), value)
        elif isinstance(value, list):
            if key not in target:
                target[key] = []
            target[key] = [
                (
                    update_nested_dict(target[key][i] if i < len(target[key]) else {}, item)
                    if isinstance(item, dict)
                    else item
                )
                for i, item in enumerate(value)
            ]
        else:
            target[key] = value
    return target


def upload_file(file: UploadFile, name_bucket: str = 'qwestar'):
    try:
        # Leer el contenido del archivo
        file_content = file.file.read()
        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío."
            )

        # Convertir el contenido a BytesIO
        file_byte_arr = BytesIO(file_content)
        file_byte_arr.seek(0)

        # Subir el archivo a Google Cloud Storage
        storage_client = storage.Client.from_service_account_json("credentials.json")
        bucket = storage_client.bucket(name_bucket)
        blob = bucket.blob(f"files-provisional/{file.filename}")
        blob.upload_from_file(file_byte_arr, content_type=file.content_type)

        return f"https://storage.googleapis.com/{name_bucket}/files-provisional/{file.filename}"
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error al subir el archivo."
        )

conf = ConnectionConfig(
    MAIL_USERNAME="cm@qwestar.ai",
    MAIL_PASSWORD="jeuoplfvazuyfvwt",
    MAIL_FROM="cm@qwestar.ai",
    MAIL_PORT=465,  # Puerto para SSL
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


async def send_email(
    subject: str,
    recipients: List[str],
    body: str,
) -> JSONResponse:
    """
    Método reutilizable para enviar correos electrónicos.

    Parameters:
    - subject (str): Asunto del correo.
    - recipients (List[str]): Lista de destinatarios.
    - body (str): Contenido HTML del correo.
    - attachments (Optional[List[UploadFile]]): Archivos adjuntos opcionales.

    Returns:
    - JSONResponse: Respuesta indicando el estado del envío.
    """
    try:
        # Procesar los archivos adjuntos si existen

        # Crear el mensaje
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype=MessageType.html
        )

        # Enviar el correo
        fm = FastMail(conf)
        await fm.send_message(message)
        return JSONResponse(status_code=200, content={"message": "email has been sent"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})