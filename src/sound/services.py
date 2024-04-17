from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from sound.models import Sound


def get_sound_by_field(db: Session, field: str, value: str):
    """
    Get a sound by a field.
    """
    sound = db.query(Sound).filter(getattr(Sound, field) == value).first()
    if not sound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sound with {field} {value} not found")
    return sound
