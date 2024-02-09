import datetime
from enum import Enum

from sqlalchemy import Column, Integer
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Text
from sqlalchemy.ext.declarative import declarative_base

from utils import generate_uuid

Base = declarative_base()


class AbstractBaseModel(Base):
    __abstract__ = True
    id = Column(String, name="id", primary_key=True, default=generate_uuid, index=True)
    created_at: datetime = Column(Date, default=datetime.datetime.utcnow())
    created_by: str = Column(String, default="system")
    updated_at: datetime = Column(Date, default=datetime.datetime.utcnow())
    updated_by: str = Column(String, default="system")


class Script(AbstractBaseModel):
    __tablename__ = "script"
    title: str = Column(String, index=True)
    description: str = Column(Text, nullable=True)
    game_id: str = Column(String, nullable=False)
    order: int = Column(Integer, nullable=True)
    status: int = Column(Integer, nullable=True)
    status_character: int = Column(Integer, nullable=True)
    status_location: int = Column(Integer, nullable=True)
    status_scene: int = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Script {self.title} - {self.game_id}>"
