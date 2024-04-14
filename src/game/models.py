import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import Boolean
from sqlalchemy.ext.declarative import declarative_base

from utils import generate_uuid

Base = declarative_base()


class AbstractBaseModel(Base):
    __abstract__ = True
    id = Column(String, name="id", primary_key=True, default=generate_uuid, index=True)
    created_at: datetime = Column(Date, default=datetime.datetime.today())
    created_by: str = Column(String, default="system")
    updated_at: datetime = Column(Date, default=datetime.datetime.today())
    updated_by: str = Column(String, default="system")


class Game(AbstractBaseModel):
    __tablename__ = "game"
    title: str = Column(String, index=False, nullable=True)
    synopsis: str = Column(Text, nullable=True)
    history: str = Column(Text, nullable=True)
    image: str = Column(String, nullable=True)
    image_background: str = Column(String, nullable=True)
    prompt_image: str = Column(String, nullable=True)
    summary: str = Column(String, nullable=True)
    # is_active: bool = Column(Boolean, default=False)
    story_line = Column(Text, nullable=False)
    user_id: str = Column(String, nullable=False)
    attempts: int = Column(Integer, nullable=True)
    first_script: bool = Column(Boolean, nullable=True)
    count_scripts: int = Column(Integer, nullable=True)
    category: str = Column(String, nullable=True)
    response_error: str = Column(Text, nullable=True)
    is_wrong: bool = Column(Boolean, nullable=True)

    def __repr__(self):
        return f"<Game {self.title} - {self.user_id}>"
