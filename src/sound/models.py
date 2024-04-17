import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import ChoiceType

from fastapi_storages.integrations.sqlalchemy import FileType

from utils import storage
from utils import generate_uuid

Base = declarative_base()


class AbstractBaseModel(Base):
    __abstract__ = True
    id = Column(String, name="id", primary_key=True, default=generate_uuid, index=True)
    created_at: datetime = Column(DateTime, default=datetime.datetime.utcnow())
    created_by: str = Column(String, default="system")
    updated_at: datetime = Column(DateTime, default=datetime.datetime.utcnow())
    updated_by: str = Column(String, default="system")


class Sound(AbstractBaseModel):
    __tablename__ = "sound"

    TYPE_SOUND = [
        ("situational", "situational"),
        ("environment", "environment"),
    ]

    name: str = Column(String)
    description: str = Column(String)
    file = Column(FileType(storage), nullable=True)
    # user: str = Column(String)
    category: str = Column(String)
    type: str = Column(ChoiceType(TYPE_SOUND))
    is_active: bool = Column(Boolean, default=True)
    is_deleted: bool = Column(Boolean, default=False)
    sound: str = Column(String)

    def __repr__(self):
        return f"<Sound {self.name} - {self.user}>"
