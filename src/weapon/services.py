from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from weapon.models import Weapon

from weapon.schemas import SchemaRetrieveWeapon
from weapon.schemas import SchemaCreateWeapon
from weapon.schemas import SchemaPartialUpdateWeapon
from weapon.schemas import SchemaListWeapon

from utils import upload_image


def get_weapon_by_field(db: Session, field: str, value: str):
    """
    Get a weapon by a field.
    """
    weapon = db.query(Weapon).filter(getattr(Weapon, field) == value).first()
    if not weapon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Weapon with {field} {value} not found")
    return weapon


def get_weapons_service(db: Session, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of weapons.
    """
    weapons = db.query(Weapon).filter(Weapon.game_id == game_id).offset(skip).limit(limit).all()
    return weapons


def create_weapon_service(db: Session, weapon: SchemaCreateWeapon, user_id: str):
    """
    Create a new weapon.
    """
    db_weapon = Weapon(**weapon.dict())
    if weapon.image:
        db_weapon.image = upload_image(weapon.image, f"{weapon.game_id}/weapon/{weapon.name}.jpg")
    db_weapon.created_by = user_id
    db_weapon.updated_by = user_id
    db.add(db_weapon)
    db.commit()
    db.refresh(db_weapon)
    return db_weapon


def retrieve_weapon_service(db: Session, weapon_id: str):
    """
    Retrieve a weapon.
    """
    weapon = get_weapon_by_field(db, "id", weapon_id)
    return weapon


def partial_update_weapon_service(db: Session, weapon_id: str, weapon: SchemaPartialUpdateWeapon):
    """
    Partial update a weapon.
    """
    db_weapon = get_weapon_by_field(db, "id", weapon_id)
    for var, value in weapon:
        setattr(db_weapon, var, value)
    db.commit()
    db.refresh(db_weapon)
    return db_weapon
