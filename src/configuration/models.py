import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Integer
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


class Configuration(AbstractBaseModel):
    __tablename__ = "configuration"

    featured_games: list = Column(PickleType)
    popular_games: list = Column(PickleType)
    games_by_category: dict = Column(PickleType)

    stars_news_users: int = Column(Integer, default=0,nullable=True)
    stars_by_game: int = Column(Integer, default=0,nullable=True)

    def __repr__(self):
        return f"<Configuration {self.id}>"
