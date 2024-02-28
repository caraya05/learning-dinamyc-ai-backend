import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import Text
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


class Customize(AbstractBaseModel):
    __tablename__ = "customize"

    GENDER_TYPE = [
        ("man", "man"),
        ("woman", "woman"),
        ("both", "both"),
        ("other", "other"),
    ]

    TYPE_CUSTOMIZE = [
        ("clothes", "clothes"),
        ("hair", "hair"),
        ("head", "head"),
        ("body", "body"),
        ("upper garment", "upper garment"),
        ("lower garment", "lower garment"),
        ("shoes", "shoes"),
        ("beard", "beard"),
        ("other", "other"),
    ]

    TYPE_CHARACTER = [
        ("human", "human"),
        ("animal", "animal"),
        ("other", "other"),
    ]

    type_character: str = Column(ChoiceType(TYPE_CHARACTER), nullable=False)
    reference_ui: str = Column(String, nullable=True)
    gender: str = Column(ChoiceType(GENDER_TYPE), nullable=False)
    # name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    type_customize: str = Column(ChoiceType(TYPE_CUSTOMIZE), nullable=False)

    def __repr__(self):
        return f"<Customize {self.type_character} - {self.gender} - {self.type_customize}>"
