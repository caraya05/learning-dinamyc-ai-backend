from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from customize.models import Customize



def get_customize_by_field(db: Session, field: str, value: str):
    try:
        return db.query(Customize).filter(getattr(Customize, field) == value).first()
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customize not found",
        )


def get_customize_by_type_character_service(db: Session, type_character: str):
    try:
        return db.query(Customize).filter(Customize.type_character == type_character).all()
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customize not found",
        )
