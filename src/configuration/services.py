from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from configuration.models import Configuration


def get_configuration_service(db: Session):
    try:
        return db.query(Configuration).first()
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error getting configuration"
        ) from ex
