import json
from uuid import uuid4
from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema
from character.services import get_character_service
from core.database import db
from game.services import get_game_service
from gpt_ai.utils import generate_image_dalle
from gpt_ai.utils import generate_gpt4_
from prompt.services import get_prompt_by_category_service
from utils import upload_image

from weapon.schemas import SchemaListWeapon
from weapon.schemas import SchemaRetrieveWeapon
from weapon.schemas import SchemaCreateWeapon
from weapon.schemas import SchemaPartialUpdateWeapon

from weapon.services import get_weapons_service
from weapon.services import retrieve_weapon_service
from weapon.services import create_weapon_service
from weapon.services import partial_update_weapon_service

router = APIRouter(prefix="/weapon", tags=["Weapon"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListWeapon)
async def get_weapons(
        game_id: str,
        character_id: str = None,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves all weapons.

    It returns a list of weapons.
    """

    weapons_db, counts_weapon = await get_weapons_service(game_id, skip=0, limit=1000, character_id=character_id)

    for weapon in weapons_db:
        weapon['_id'] = str(weapon['_id'])

    return SchemaListWeapon(results=weapons_db, count=counts_weapon)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveWeapon)
async def create_weapon(
        weapon: SchemaCreateWeapon,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a weapon.

    It expects a weapon in the request body.
    If the weapon is successfully created, it returns the weapon's information.
    """
    prompt_weapon = await get_prompt_by_category_service("weapon")
    prompt_imagen_weapon = await get_prompt_by_category_service("image_weapon")

    game_db = await get_game_service(weapon.game_id)

    character_db = await get_character_service(weapon.character_id)

    if weapon.type == "long":
        # prompt1 = ("Dame una idea y su respectiva descripción de un arma de impacto de corto alcance que utilizaria"
        #            " el x_character en esta x_history.")
        prompt1 = prompt_weapon['description'].replace("x_weapon", "de impacto de corto alcance")
        prompt2 = prompt_imagen_weapon['description']

    else:

        # prompt1 = ("Dame una idea y su respectiva descripción de un arma que dispara algun tipo de proyectil que "
        #            "utilizaria el x_character en esta x_history.")
        prompt1 = prompt_weapon['description'].replace(
            "x_weapon", "que dispara algun tipo de proyectil"
        )
        prompt2 = prompt_imagen_weapon['description']

    prompt1 = prompt1.replace("x_character", character_db['description'])

    prompt1 = prompt1.replace("x_history", game_db['synopsis'])

    json_response = {
        "name": "string (name of the weapon)",
        "description": "string (description of the weapon)",
        "type": "string (type of the weapon) (short, long)",
        "extra_data": {
            "color_body": "string (color of the body of the weapon in format hexadecimal)",
            "color_tip": "string (color of the tip of the weapon in format hexadecimal)",
            "color_complement_1": "string (color of the complement 1 of the weapon in format hexadecimal)",
            "color_complement_2": "string (color of the complement 2 of the weapon in format hexadecimal)",
        },
    }

    prompt_content = [
        {
            "role": "system",
            "content": f"responde el prompt con la siguiente estructura JSON: {json_response}",
        },
        {"role": "user", "content": [{"type": "text", "text": prompt1}]},
    ]

    weapon_generated = generate_gpt4_(prompt_content)

    weapon_generated = json.loads(weapon_generated)

    # prompt2 = prompt2.replace("x_description", weapon_generated['description'])

    # image_generated = generate_image_dalle(prompt2, quality="hd", size="1024x1024")

    weapon_new = SchemaCreateWeapon(
        name=weapon_generated['name'],
        description=weapon_generated['description'],
        image="",
        type=weapon_generated['type'],
        script_id=weapon.script_id,
        game_id=weapon.game_id,
        character_id=weapon.character_id,
        extra_data=weapon_generated['extra_data'],
    )

    weapon_db = await create_weapon_service(weapon_new, str(user_db['_id']))

    return weapon_db


@router.get("/{weapon_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveWeapon)
async def retrieve_weapon(
        weapon_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a weapon.

    It expects the weapon's id in the request path.
    If the weapon is successfully retrieved, it returns the weapon's information.
    """

    weapon_db = await retrieve_weapon_service(weapon_id)
    return weapon_db


@router.patch("/{weapon_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveWeapon)
async def partial_update_weapon(
        weapon_id: str,
        weapon: SchemaPartialUpdateWeapon,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint updates a weapon.

    It expects the weapon's id in the request path and the new information in the request body.
    If the weapon is successfully updated, it returns the weapon's information.
    """

    weapon_db = await partial_update_weapon_service(weapon_id, weapon)
    return weapon_db


@router.get("/generate-image/{weapon_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveWeapon)
async def generate_image(
        weapon_id: str,
        user_db: dict = Depends(auth),
        Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint generates an image for a weapon.

    It expects the weapon's id in the request path.
    If the image is successfully generated, it returns a 200 status code.
    """

    weapon_db = await retrieve_weapon_service(weapon_id)

    prompt_db_image_weapon = await get_prompt_by_category_service('image_weapon')

    description_prompt_db_image_weapon = prompt_db_image_weapon['description']

    if weapon_db['type'] == "long":
        description_prompt_db_image_weapon.replace("x_type", "largo alcance")
    else:
        description_prompt_db_image_weapon.replace("x_type", "corto alcance")

    prompt_db_image_weapon = description_prompt_db_image_weapon + f" descripción: {weapon_db['description']}"

    image_generated = generate_image_dalle(prompt_db_image_weapon, quality="hd", size="1024x1792")

    weapon_db['image'] = upload_image(
        url_image=image_generated,
        file_name=f"weapon/{uuid4()}.jpg",
        size=(512, 512),
    )

    await db["weapon"].update_one({"_id": weapon_db['_id']}, {"$set": weapon_db})

    return await db["weapon"].find_one({"_id": weapon_db['_id']})
