import uuid
import jwt
import requests

from boto3 import session
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, Path
from fastapi import status
from fastapi_storages import S3Storage

from config import settings

from PIL import Image
from io import BytesIO

session = session.Session()


def generate_uuid():
    return str(uuid.uuid4())


#
# def upload_image(url_image: str, file_name: str ):
#     # Initiate session
#     image_request = requests.get(url_image, stream=True)
#
#     image_buffer = image_request.raw.read()
#
#     image_buffer = bytes(image_buffer)
#
#     image_buffer = bytearray(image_buffer)
#
#     client = session.client('s3',
#                             region_name='qwestar',
#                             endpoint_url='https://qwestar.sfo3.digitaloceanspaces.com',
#                             aws_access_key_id=settings.ACCESS_ID_DIGITAL_OCEAN,
#                             aws_secret_access_key=settings.SECRET_KEY_DIGITAL_OCEAN)
#
#     # Upload a file to your Space
#     # client.upload_file('test.html', 'hello-spaces', 'new-folder/new_file_name.html')
#
#     try:
#         response = client.put_object(Bucket='backend',
#                                      Key=file_name,
#                                      Body=image_buffer,
#                                      ACL='public-read',
#                                      ContentType='image/jpeg')
#
#         return f"https://qwestar.sfo3.digitaloceanspaces.com/backend/{file_name}"
#
#     except Exception as e:
#         print(e)
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Error uploading image",
#         )


def upload_image(size: tuple[int, int], file_name: str, image_content_type: any = None, url_image: str = None,
                 name_bucket: str = 'backend'):
    try:
        if image_content_type and not url_image:
            img = Image.open(BytesIO(image_content_type))
        else:
            image_url = requests.get(url_image)
            img = Image.open(BytesIO(image_url.content))
        img = img.resize(size)

        # Save the image to a BytesIO object
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        client = session.client('s3',
                                region_name='qwestar',
                                endpoint_url='https://qwestar.sfo3.digitaloceanspaces.com',
                                aws_access_key_id=settings.ACCESS_ID_DIGITAL_OCEAN,
                                aws_secret_access_key=settings.SECRET_KEY_DIGITAL_OCEAN)

        response = client.put_object(Bucket=name_bucket,
                                     Key=file_name,
                                     Body=img_byte_arr,
                                     ACL='public-read',
                                     ContentType='image/jpeg')
        return f"{settings.URL_DIGITAL_OCEAN}{file_name}"
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error resizing image",
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

class PublicAssetS3Storage(S3Storage):
    AWS_ACCESS_KEY_ID = settings.ACCESS_ID_DIGITAL_OCEAN
    AWS_SECRET_ACCESS_KEY = settings.SECRET_KEY_DIGITAL_OCEAN
    AWS_S3_BUCKET_NAME = "backend"
    AWS_S3_ENDPOINT_URL = "qwestar.sfo3.digitaloceanspaces.com"
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_USE_SSL = True

    def __set_name__(self, name):
        super().__init__()
        self.AWS_S3_BUCKET_NAME = name
        self._bucket = self._s3.Bucket(name=self.AWS_S3_BUCKET_NAME)
        self._http_scheme = "https" if self.AWS_S3_USE_SSL else "http"
        self._url = f"{self._http_scheme}://{self.AWS_S3_ENDPOINT_URL}"
        return self.AWS_S3_BUCKET_NAME

    def get_path(self, name: str) -> str:
        key = self.get_name(name)
        if self.AWS_S3_CUSTOM_DOMAIN:
            return "{}://{}/{}".format(
                self._http_scheme,
                self.AWS_S3_CUSTOM_DOMAIN,
                key,
            )
        if self.AWS_QUERYSTRING_AUTH:
            params = {"Bucket": self._bucket.name, "Key": key}
            return self._s3.meta.client.generate_presigned_url(
                "get_object", Params=params
            )
        return "{}://{}/{}/{}".format(
            self._http_scheme,
            self.AWS_S3_ENDPOINT_URL,
            self.AWS_S3_BUCKET_NAME,
            key,
        )


storage = PublicAssetS3Storage()
