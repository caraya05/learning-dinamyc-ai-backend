import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import DateTime

from sqlalchemy.ext.declarative import declarative_base

from utils import generate_uuid

Base = declarative_base()


class AbstractBaseModel(Base):
    __abstract__ = True
    id = Column(String, name="id", primary_key=True, default=generate_uuid, index=True)
    created_at: datetime = Column(DateTime, default=datetime.datetime.utcnow())
    created_by: str = Column(String, default="system")
    updated_at: datetime = Column(DateTime, default=datetime.datetime.utcnow())
    updated_by: str = Column(String, default="system")


class DailyRecord(AbstractBaseModel):
    __tablename__ = "daily_records"

    user: str = Column(String)
    balance: int = Column(Integer)
    expenses: int = Column(Integer)
    games_created: int = Column(Integer)
    sets_with_errors: int = Column(Integer)
    attempts_to_create_without_balance: int = Column(Integer)

    # user = relationship("User", back_populates="daily_records")

    def __repr__(self):
        return f"<RecordDaily {self.user_id} - {self.balance}>"
