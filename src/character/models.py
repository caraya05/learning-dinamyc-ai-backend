import datetime
import enum

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import ChoiceType

from utils import generate_uuid

Base = declarative_base()


class TypeCharacterEnum(enum.Enum):
    leading_role = "leading role"
    enemy = "enemy"
    antagonist = "antagonist"
    other = "other"

class AbstractBaseModel(Base):
    __abstract__ = True
    id = Column(String, name="id", primary_key=True, default=generate_uuid, index=True)
    created_at: datetime = Column(Date, default=datetime.datetime.utcnow())
    created_by: str = Column(String, default="system")
    updated_at: datetime = Column(Date, default=datetime.datetime.utcnow())
    updated_by: str = Column(String, default="system")


class Character(AbstractBaseModel):
    TYPE_CHARACTER = [
        ("leading role", "leading role"),
        ("enemy", "enemy"),
        ("antagonist", "antagonist"),
        ("other", "other"),
    ]

    __tablename__ = "character"
    name: str = Column(String, index=False)
    type: str = Column(ChoiceType(TYPE_CHARACTER), nullable=False)
    description: str = Column(Text, nullable=False)
    image: str = Column(String, nullable=True)
    genre: str = Column(String, nullable=True)
    game_id: str = Column(String, nullable=False)
    attempts: int = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Character {self.name} - {self.type}>"
