from fastapi import APIRouter
from fastapi import Depends
from fastapi import UploadFile
from fastapi import File

from fastapi.security import HTTPAuthorizationCredentials

from uuid import uuid4

from auth.auth import auth_admin
from auth.utils import auth_schema

from utils import upload_image, upload_audio

from io import BytesIO
from pydub import AudioSegment
from PIL import Image

router = APIRouter(prefix="/configuration", tags=["Configuration"])


@router.post(
    "/upload-file/{section}/section/{format}/format/",
)
async def update_photo_user(
    section: str,
    format: str,
    file: UploadFile = File(...),
    user_db: dict = Depends(auth_admin),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    file_content = await file.read()
    image = Image.open(BytesIO(file_content))
    original_width, original_height = image.size

    if section in ["events", "games"]:
        new_width = 512
    elif section == "locations":
        new_width = 2436
    else:
        new_width = 512

    ratio = new_width / original_width
    new_height = int(original_height * ratio)
    size_image = (new_width, new_height)

    print(f"size_image: {size_image}")

    if format in ["jpg", "jpeg", "png"]:
        url = upload_image(
            image_content_type=file_content,
            file_name=f"{section}/{uuid4()}.{format}",
            size=size_image,
        )
    elif format in ["ogg", "mp3"]:
        audio_segment = AudioSegment.from_file(BytesIO(file_content), format=format)
        ogg_audio_in_memory = BytesIO()
        audio_segment.export(ogg_audio_in_memory, format="ogg")
        ogg_audio_in_memory.seek(0)

        url = upload_audio(
            audio_byte_arr=ogg_audio_in_memory,
            file_name=f"{section}/{uuid4()}.ogg",
        )
    else:
        url = None

    return {"url": url}
