from bson import ObjectId
from motor import motor_asyncio

from config import settings

client = motor_asyncio.AsyncIOMotorClient(
    settings.DATABASE_URL, serverSelectionTimeoutMS=30000
)
db = client.get_database(settings.DATABASE_NAME)


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


async def create_index():
    await db["user"].create_index("username")
    await db["user"].create_index("email")

    await db["game"].create_index("title")
    await db["game"].create_index("category_id")

    await db["category"].create_index("name")

    await db["prompt"].create_index("category")
