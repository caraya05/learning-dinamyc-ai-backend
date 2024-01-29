import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Text
from sqlalchemy import Integer
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

class Scene(AbstractBaseModel):
    __tablename__ = "scene"
    order: int = Column(Integer, unique=True, index=False)
    title: str = Column(String, unique=True, index=False)
    description: str = Column(Text, nullable=False)
    script_id: str = Column(String, nullable=False)
    location_id: str = Column(String, nullable=False)
    characters_id: str = Column(String, nullable=False)