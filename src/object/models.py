import datetime

from sqlalchemy import Column
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


class Object(AbstractBaseModel):
    __tablename__ = "object"
    name: str = Column(String, index=False, nullable=True)
    description: str = Column(Text, nullable=True)
    function: str = Column(String, nullable=True)
    image: str = Column(String, nullable=True)
    script_id: str = Column(String, nullable=False)
    game_id: str = Column(String, nullable=False)

    def __repr__(self):
        return f"<Object(title={self.name}, game_id={self.game_id})>"
