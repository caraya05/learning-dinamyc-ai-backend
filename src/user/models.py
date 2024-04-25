# import datetime
# from html import escape
#
# from mongoengine import Document
# from mongoengine import StringField
# from mongoengine import DateTimeField
# from mongoengine import BooleanField
# from mongoengine import IntField
# from mongoengine import ImageField
# from fastapi import Request
#
#
# class User(Document):
#     username = StringField(required=True, unique=True)
#     email = StringField(required=True, unique=True)
#     photo = ImageField(thumbnail_size=(200, 200, True))
#     uid = StringField(required=True, unique=True)
#     provider = StringField(default="local")
#     password = StringField(required=True, min_length=8)
#     is_active = BooleanField(default=False)
#     is_superuser = BooleanField(default=False)
#     is_staff = BooleanField(default=False)
#     stars = IntField(default=0)
#     number_of_creation_attempts = IntField(default=0)
#     attempt_to_create = BooleanField(default=False)
#     created_at = DateTimeField(default=datetime.datetime.utcnow)
#     created_by = StringField(default="system")
#     updated_at = DateTimeField(default=datetime.datetime.utcnow)
#     updated_by = StringField(default="system")
#
#     def __repr__(self):
#         return f"<User {self.email} - {self.uid}>"
#
#     def __str__(self):
#         return f"<User {self.email} - {self.uid}>"
#
#     async def __admin_select2_repr__(self, request: Request) -> str:
#         return f'<div><img src="{escape(self.photo)}"><span>{escape(self.username)}</span></div>'

from enum import Enum
from typing import List, Optional

from odmantic import EmbeddedModel, Field, Model, Reference
from pydantic import EmailStr
from starlette.requests import Request
#
#
# from enum import Enum
# from typing import List, Optional
#
# from odmantic import EmbeddedModel, Field, Model, Reference
# from pydantic import EmailStr
# from starlette.requests import Request
#
#
# class Address(EmbeddedModel):
#     street: str = Field(min_length=3)
#     city: str = Field(min_length=3)
#     state: Optional[str]
#     zipcode: Optional[str]
#
#
# class Author(Model):
#     first_name: str = Field(min_length=3)
#     last_name: str = Field(min_length=3)
#     email: Optional[EmailStr]
#     addresses: List[Address] = Field(default_factory=list)
#
#     async def __admin_repr__(self, request: Request):
#         return f"{self.last_name} {self.first_name}"
#
#
# class BookFormat(str, Enum):
#     Hardcover = "hardcover"
#     Graphic = "graphic"
#     Paperback = "paperback"
#     Mass_market_paperback = "mass_market_paperback"
#
#
# class Book(Model):
#     title: str = Field(min_length=5)
#     format: BookFormat
#     year: int = Field(ge=1900, le=2022)
#     awards: List[str] = Field(default_factory=list, min_length=3)
#     author: Author = Reference()

from datetime import datetime
from enum import Enum
from starlette.requests import Request
import mongoengine as me


class Unit(str, Enum):
    m = "m"
    cm = "cm"
    mm = "mm"


class Dimension(me.EmbeddedDocument):
    width = me.IntField(min_value=10, max_value=100)
    height = me.IntField(min_value=10, max_value=100)
    unit = me.EnumField(Unit)


class Product(me.Document):
    title = me.StringField(min_length=3)
    description = me.StringField()
    price = me.DecimalField(min_value=0.01)
    dimension = me.EmbeddedDocumentField(Dimension)
    image = me.ImageField(thumbnail_size=(128, 128))
    manual = me.FileField()
    created_at = me.DateTimeField(default=datetime.utcnow)
    category = me.ReferenceField("Category")


class Category(me.Document):
    name = me.StringField(min_length=3, unique=True)

    def __admin_repr__(self, request: Request):
        return self.name