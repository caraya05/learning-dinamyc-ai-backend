import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Integer
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


class Game(AbstractBaseModel):
    __tablename__ = "game"
    title: str = Column(String, index=False, nullable=True)
    synopsis: str = Column(Text, nullable=True)
    history: str = Column(Text, nullable=True)
    image: str = Column(String, nullable=True)
    image_background: str = Column(String, nullable=True)
    prompt_image: str = Column(String, nullable=True)
    # is_active: bool = Column(Boolean, default=False)
    # location: str = Column(Text, nullable=True)
    # characters: str = Column(String, nullable=True)
    story_line = Column(Text, nullable=False)
    user_id: str = Column(String, nullable=False)
    attempts: int = Column(Integer, nullable=True)
    # is_multiverse: bool = Column(Boolean, default=False)
    # multiverse = Column(ARRAY(String), nullable=True)
    # is_future_travel: bool = Column(Boolean, default=False)
    # is_past_travel: bool = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Game {self.title} - {self.user_id}>"
