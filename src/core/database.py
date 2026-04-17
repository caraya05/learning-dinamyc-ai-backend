from botocore.vendored.requests import Timeout
from bson import ObjectId
from motor import motor_asyncio
from urllib3.util import SSLContext

from config import settings

client = motor_asyncio.AsyncIOMotorClient(settings.DATABASE_URL, serverSelectionTimeoutMS=10000)
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


async def create_indexes():

    await db["user"].drop_indexes()
    await db["game"].drop_indexes()

    await db["user"].create_index("username")
    await db["user"].create_index("email")
    await db["user"].create_index("team_id")

    await db["game"].create_index("title")
    await db["game"].create_index("category_id")


    # Visual Style indexes
    await db["visual_style"].create_index("user_id")
    await db["visual_style"].create_index("created_at")
    await db["visual_style"].create_index("is_active")
    await db["visual_style"].create_index([("user_id", 1), ("is_active", 1)])



