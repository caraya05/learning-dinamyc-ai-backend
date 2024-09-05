import requests

from bson import ObjectId

from fastapi import Request
from fastapi import Depends
from fastapi import APIRouter
from fastapi import status
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from PIL import Image
from io import BytesIO


from config import settings

from core.database import db

from auth.auth import auth
from auth.utils import auth_schema

from configuration.services import get_configurations_service

from game.services import get_game_service

from utils import upload_image

router = APIRouter(prefix="/share", tags=["Share"])

routerAPP = APIRouter(prefix="/share", tags=["Share"])

templates = Jinja2Templates(directory="templates")


@router.get("/{game_id}", status_code=200)
async def share_game(game_id: str,
                     user_db: dict = Depends(auth),
                     Token: HTTPAuthorizationCredentials = Depends(auth_schema),
                     ):
    """
    This endpoint shares a game.
    """
    game_db = await get_game_service(game_id)
    configuration_db = await get_configurations_service()

    if not game_db['summary'] or not game_db['category_id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="it is possible that the game is not published",
        )

    message_completed = configuration_db["share_message"]
    message_completed = message_completed.replace("{{name_game}}", game_db["title"])
    message_completed = message_completed.replace("{{summary_game}}", game_db["summary"])
    message_completed = message_completed.replace("{{category_game}}", game_db["category_id"])

    message_share = "Error when sharing a game"

    if not game_db.get("image_share", None):
        url = game_db["image"]
        response = requests.get(url)
        image = Image.open(BytesIO(response.content))
        width = min(image.width, image.height * 3.7 / 4)
        height = width * 4 / 3.7
        center_x = image.width / 2
        center_y = image.height / 2
        left = center_x - width / 2
        top = center_y - height / 2
        right = center_x + width / 2
        bottom = center_y + height / 2
        cropped_image = image.crop((left, top, right, bottom))
        gradient = Image.new('L', (cropped_image.width, 350))
        for x in range(cropped_image.width):
            for y in range(350):
                gradient.putpixel((x, y), int(255 * (y / 350)))
        gradient = gradient.convert('RGBA')
        datas = gradient.getdata()
        newData = []
        for item in datas:
            newData.append((0, 0, 0, item[0]))
        gradient.putdata(newData)
        cropped_image.paste(gradient, (0, cropped_image.height - gradient.height), gradient)
        url_overlay = "https://qwestar.sfo3.cdn.digitaloceanspaces.com/backend/screen/9f11f70d-53cd-464c-b762-86a888573b10.png"
        response_overlay = requests.get(url_overlay)
        image_overlay = Image.open(BytesIO(response_overlay.content))
        image_overlay = image_overlay.convert("RGBA")
        image_overlay = image_overlay.resize((450, 150))
        x = int((cropped_image.width - image_overlay.width) / 2)
        y = cropped_image.height - image_overlay.height
        cropped_image.paste(image_overlay, (x, y), image_overlay)
        img_byte_arr = BytesIO()
        cropped_image.save(img_byte_arr, "JPEG")
        img_byte_arr.seek(0)  # Reset the file pointer to the beginning
        image_url = upload_image(
            size=(430, 464),
            image_content_type=img_byte_arr.getvalue(),
            file_name=f"share/{game_id}.jpg",
            name_bucket="backend",
        )

        await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {"image_share": image_url}})

        message_share = f"{message_completed} {settings.URL_API}/share/app/{game_id}"

        message_share = message_share.replace("\n", "")

    return message_share


@routerAPP.get("/app/{game_id}", response_class=HTMLResponse)
async def share_app(game_id: str,
                    request: Request):
    """
    This endpoint shares an app.
    """
    if not game_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game ID is required",
        )

    configuration_db = await get_configurations_service()

    game_db = await get_game_service(game_id)

    return templates.TemplateResponse(
        name="share.html",
        context={"request": request,
                 "url": f"{settings.URL_API}/share/app/{game_id}",
                 "name": game_db["title"],
                 "game_id": game_id,
                 "summary": game_db["summary"][0:50],
                 "image": game_db["image_share"],
                 "url_form": configuration_db["url_form"]},
    )
