import datetime
from enum import Enum

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Text
from sqlalchemy import Boolean
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy_utils import ChoiceType

from utils import generate_uuid

Base = declarative_base()


class AbstractBaseModel(Base):
    __abstract__ = True
    id = Column(String, name="id", primary_key=True, default=generate_uuid, index=True)
    created_at: datetime = Column(Date, default=datetime.datetime.utcnow())
    created_by: str = Column(String, default="system")
    updated_at: datetime = Column(Date, default=datetime.datetime.utcnow())
    updated_by: str = Column(String, default="system")


class Prompt(AbstractBaseModel):
    CATEGORY = [
        ("character", "character"),
        ("characters_principal", "characters_principal"),
        ("location", "location"),
        ("scene", "scene"),
        ("weapon", "weapon"),
        ("cover", "cover"),
        ("history", "history"),
        ("synopsis", "synopsis"),
        ("character_image", "character_image"),
        ("location_image", "location_image"),
        ("script", "script"),
        ("image_background", "image_background"),
        ("image_weapon", "image_weapon"),
        ("image_object", "image_object"),
        ("image_introduction", "image_introduction"),
        ("text_introduction", "text_introduction"),
        ("category_game", "category_game"),
        ("imagen_scene_cero", "imagen_scene_cero"),
        ("text_introduction_scene_cero", "text_introduction_scene_cero"),
        ("before_battle", "before_battle"),
        ("finish_chapter", "finish_chapter"),
    ]
    __tablename__ = "prompt"
    title: str = Column(String, unique=True, index=False)
    description: str = Column(Text, nullable=False)
    prompt_system: str = Column(Text, nullable=True)
    category: str = Column(ChoiceType(CATEGORY), nullable=False)
    is_active: bool = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Prompt {self.title} - {self.category}>"
