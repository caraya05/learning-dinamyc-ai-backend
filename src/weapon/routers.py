import json

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT

from sqlalchemy.orm import Session

from character.services import get_character_by_field
from config import auth_scheme
from game.services import get_game_by_field
from gpt_ai.utils import generate_image_dalle
from gpt_ai.utils import generate_gpt4_
from prompt.services import get_prompt_by_field
from utils import upload_image

from weapon.schemas import SchemaListWeapon
from weapon.schemas import SchemaCreateForType
from weapon.schemas import SchemaRetrieveWeapon
from weapon.schemas import SchemaCreateWeapon
from weapon.schemas import SchemaPartialUpdateWeapon

from weapon.services import get_weapons_service
from weapon.services import retrieve_weapon_service
from weapon.services import create_weapon_service
from weapon.services import partial_update_weapon_service

router = APIRouter(prefix="/weapon", tags=["Weapon"])


def get_db(request: Request):
    return request.state.db


@router.get("/", status_code=status.HTTP_200_OK, response_model=SchemaListWeapon)
def get_weapons(game_id: str,
                character_id: str = None,
                db: Session = Depends(get_db),
                Authorize: AuthJWT = Depends(),
                Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                ):
    """
    This endpoint retrieves all weapons.

    It returns a list of weapons.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    weapons_db = get_weapons_service(db, game_id, skip=0, limit=100, character_id=character_id)

    return weapons_db


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SchemaRetrieveWeapon)
def create_weapon(weapon: SchemaCreateForType,
                  db: Session = Depends(get_db),
                  Authorize: AuthJWT = Depends(),
                  Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                  ):
    """
    This endpoint creates a weapon.

    It expects a weapon in the request body.
    If the weapon is successfully created, it returns the weapon's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    game_db = get_game_by_field(db, "id", weapon.game_id)

    character_db = get_character_by_field(db, "id", weapon.character_id)

    if weapon.type == "long":
        prompt1 = ("Dame una idea y su respectiva descripción de un arma de impacto de corto alcance que utilizaria"
                   " el x_character en esta x_history.")
        prompt2 = ("Genera una imagen en arte pixel y vista frontal de una arma x_description, con fondo blanco, "
                   "en resolución 1024 x 1024")

    else:

        prompt1 = ("Dame una idea y su respectiva descripción de un arma que dispara algun tipo de proyectil que "
                   "utilizaria el x_character en esta x_history.")

        prompt2 = ("Genera una imagen en arte pixel y vista frontal de una arma x_description, con fondo blanco, "
                   "en resolución 1024 x 1024")

    prompt1 = prompt1.replace("x_character", character_db.description)

    prompt1 = prompt1.replace("x_history", game_db.synopsis)

    json_response = {
        "name": "string (name of the weapon)",
        "description": "string (description of the weapon)",
        "type": "string (type of the weapon) (short, long)",
        "extra_data": {
            "color_body": "string (color of the body of the weapon in format hexadecimal)",
            "color_tip": "string (color of the tip of the weapon in format hexadecimal)",
            "color_complement_1": "string (color of the complement 1 of the weapon in format hexadecimal)",
            "color_complement_2": "string (color of the complement 2 of the weapon in format hexadecimal)",
        }
    }

    prompt_content = [
        {
            "role": "system",
            "content": f"responde el prompt con la siguiente estructura JSON: {json_response}"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt1
                }
            ]
        }
    ]

    weapon_generated = generate_gpt4_(prompt_content)

    weapon_generated = json.loads(weapon_generated)

    prompt2 = prompt2.replace("x_description", weapon_generated['description'])

    image_generated = generate_image_dalle(prompt2,
                                           quality="hd",
                                           size="1024x1024")

    weapon_new = SchemaCreateWeapon(name=weapon_generated['name'],
                                    description=weapon_generated['description'],
                                    image=image_generated,
                                    type=weapon_generated['type'],
                                    script_id=weapon.script_id,
                                    game_id=weapon.game_id,
                                    character_id=weapon.character_id,
                                    extra_data=weapon_generated['extra_data'])

    weapon_db = create_weapon_service(db, weapon_new, current_user)

    return weapon_db


@router.get("/{weapon_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveWeapon)
def retrieve_weapon(weapon_id: str,
                    db: Session = Depends(get_db),
                    Authorize: AuthJWT = Depends(),
                    Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                    ):
    """
    This endpoint retrieves a weapon.

    It expects the weapon's id in the request path.
    If the weapon is successfully retrieved, it returns the weapon's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    weapon_db = retrieve_weapon_service(db, weapon_id)

    return weapon_db


@router.patch("/{weapon_id}", status_code=status.HTTP_200_OK, response_model=SchemaRetrieveWeapon)
def partial_update_weapon(weapon_id: str,
                          weapon: SchemaPartialUpdateWeapon,
                          db: Session = Depends(get_db),
                          Authorize: AuthJWT = Depends(),
                          Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                          ):
    """
    This endpoint updates a weapon.

    It expects the weapon's id in the request path and the new information in the request body.
    If the weapon is successfully updated, it returns the weapon's information.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    weapon_db = partial_update_weapon_service(db, weapon_id, weapon)

    return weapon_db


@router.get("/generate-image/{weapon_id}", status_code=status.HTTP_200_OK)
def generate_image(weapon_id: str,
                   db: Session = Depends(get_db),
                   Authorize: AuthJWT = Depends(),
                   Token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                   ):
    """
    This endpoint generates an image for a weapon.

    It expects the weapon's id in the request path.
    If the image is successfully generated, it returns a 200 status code.
    """

    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    weapon_db = retrieve_weapon_service(db, weapon_id)

    prompt_db_image_weapon = get_prompt_by_field(db, 'category', 'image_weapon')

    if weapon_db.type == "long":
        prompt_db_image_weapon.replace("x_type", "largo alcance")
    else:
        prompt_db_image_weapon.replace("x_type", "corto alcance")

    prompt_db_image_weapon = prompt_db_image_weapon + f" descripción: {weapon_db.description}"

    image_generated = generate_image_dalle(prompt_db_image_weapon,
                                           quality="hd",
                                           size="1024x1792")

    weapon_db.image = upload_image(image_generated, f"{weapon_db.game_id}/weapon/{weapon_db.name}.jpg")

    db.commit()
    db.refresh(weapon_db)

    return weapon_db
