import datetime

from sqlalchemy import Column
from sqlalchemy import PickleType
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Text
from sqlalchemy import Boolean
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

    order: int = Column(Integer, index=False)
    title: str = Column(String, index=False)
    description: str = Column(Text, nullable=True)
    script_id: str = Column(String, nullable=False)
    game_id: str = Column(String, nullable=True)
    location_id: str = Column(String, nullable=True)
    characters_id = Column(PickleType, nullable=True)
    start_dialogues = Column(PickleType, nullable=True)
    end_dialogues = Column(PickleType, nullable=True)
    questions = Column(PickleType, nullable=True)
    dynamic: str = Column(String, nullable=True)
    content: str = Column(String, nullable=True)
    reward: str = Column(String, nullable=True)
    count_enemies: int = Column(Integer, nullable=True)
    enemy_id: str = Column(String, nullable=True)
    is_subtractable: bool = Column(Boolean, nullable=True)
    start_content: str = Column(String, nullable=True)
    start_image: str = Column(String, nullable=True)
    object_id: str = Column(String, nullable=True)
    delivery_location_id: str = Column(String, nullable=True)
    delivery_character_id: str = Column(String, nullable=True)
    image_defeat: str = Column(String, nullable=True)
    sound_id: str = Column(String, nullable=True)
