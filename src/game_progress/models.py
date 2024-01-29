import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Date
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


class GameProgress(AbstractBaseModel):
    __tablename__ = "game_progress"
    user_id: str = Column(String, nullable=False)
    scene_id: str = Column(String, nullable=False)
    game_id: str = Column(String, nullable=False)
    is_complete: bool = Column(String, nullable=False, default=False)

    def __repr__(self):
        return f"<GameProgress {self.user_id} - {self.game_id}>"
