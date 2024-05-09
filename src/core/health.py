from pymongo.errors import ConnectionFailure

from core.database import client


async def mongodb_health() -> bool:
    try:
        await client.admin.command("ping")
        return True
    except ConnectionFailure:
        return False
