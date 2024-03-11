import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Text
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import PickleType
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


class Location(AbstractBaseModel):
    __tablename__ = "location"

    title: str = Column(String, index=False)
    description: str = Column(Text, nullable=False)
    image: str = Column(String, nullable=True)
    zoom: float = Column(Float, nullable=True)
    game_id: str = Column(String, nullable=False)
    attempts: int = Column(Integer, nullable=True)
    config: str = Column(PickleType, nullable=True)

    def __repr__(self):
        return f"<Location {self.title} - {self.game_id}>"
