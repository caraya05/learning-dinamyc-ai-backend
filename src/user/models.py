import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Integer
from sqlalchemy import Boolean
from sqlalchemy.ext.declarative import declarative_base

from pydantic import constr
from pydantic import EmailStr

from fastapi_storages.integrations.sqlalchemy import FileType

from utils import storage
from utils import generate_uuid

Base = declarative_base()


class AbstractBaseModel(Base):
    __abstract__ = True
    id = Column(String, name="id", primary_key=True, default=generate_uuid, index=True)
    created_at: datetime = Column(Date, default=datetime.datetime.utcnow())
    created_by: str = Column(String, default="system")
    updated_at: datetime = Column(Date, default=datetime.datetime.utcnow())
    updated_by: str = Column(String, default="system")


class User(AbstractBaseModel):
    __tablename__ = "user"
    username: str = Column(String, unique=True, index=True)
    phone_number: str = Column(String, nullable=True)
    email: EmailStr = Column(String, unique=True, index=True)
    photo: str = Column(String, nullable=True)
    uid: str = Column(String, unique=True, index=True)
    provider: str = Column(String, nullable=False, default="local")
    password: constr(min_length=8) = Column(String, nullable=False)
    last_access: datetime = Column(Date, default=datetime.datetime.utcnow())
    is_active: bool = Column(Boolean, default=False)
    is_superuser: bool = Column(Boolean, default=False)
    is_staff: bool = Column(Boolean, default=False)
    stars: int = Column(Integer, default=0, nullable=True)
    number_of_creation_attempts: int = Column(Integer, default=0, nullable=True)
    attempt_to_create: bool = Column(Boolean, default=False, nullable=True)
    file = Column(FileType(storage), nullable=True)

    def __repr__(self):
        return f"<User {self.email} - {self.uid}>"
