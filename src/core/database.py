import asyncio
import logging
from bson import ObjectId
from motor import motor_asyncio
from pymongo.errors import (
    AutoReconnect,
    ConfigurationError,
    OperationFailure,
    ServerSelectionTimeoutError,
)

from config import settings

logger = logging.getLogger(__name__)

client = motor_asyncio.AsyncIOMotorClient(settings.DATABASE_URL, serverSelectionTimeoutMS=20000)
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


async def _wait_for_mongodb(max_retries: int = 3, base_delay: float = 2.0) -> bool:
    """Wait for MongoDB availability with bounded retries."""
    for attempt in range(1, max_retries + 1):
        try:
            await db.command("ping")
            return True
        except (ServerSelectionTimeoutError, AutoReconnect) as exc:
            if attempt == max_retries:
                logger.warning(
                    "MongoDB is not reachable after %s attempts: %s",
                    max_retries,
                    exc,
                )
                return False

            sleep_seconds = base_delay * attempt
            logger.warning(
                "MongoDB unavailable (attempt %s/%s). Retrying in %.1fs...",
                attempt,
                max_retries,
                sleep_seconds,
            )
            await asyncio.sleep(sleep_seconds)

    return False


async def create_indexes() -> bool:
    """Create indexes idempotently. Returns False on transient DB unavailability."""
    try:
        is_available = await _wait_for_mongodb()
        if not is_available:
            return False

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
        return True
    except (ConfigurationError, OperationFailure) as exc:
        logger.error("Critical MongoDB configuration/auth error: %s", exc, exc_info=True)
        raise



