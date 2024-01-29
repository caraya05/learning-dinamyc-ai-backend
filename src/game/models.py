import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Text
from sqlalchemy import Boolean
from sqlalchemy import ARRAY
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


class Game(AbstractBaseModel):
    __tablename__ = "game"
    title: str = Column(String, index=False)
    description: str = Column(Text, nullable=False)
    summary: str = Column(Text, nullable=False)
    image: str = Column(String, nullable=True)
    is_active: bool = Column(Boolean, default=False)
    location: str = Column(Text, nullable=True)
    characters: str = Column(String, nullable=True)
    story_line = Column(Text, nullable=True)
    user_id: str = Column(String, nullable=False)
    is_multiverse: bool = Column(Boolean, default=False)
    multiverse = Column(ARRAY(String), nullable=True)
    is_future_travel: bool = Column(Boolean, default=False)
    is_past_travel: bool = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Game {self.title} - {self.user_id}>"
