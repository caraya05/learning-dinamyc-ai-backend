from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from configuration.models import Configuration


def get_configuration_service(db: Session):
    return db.query(Configuration).first()