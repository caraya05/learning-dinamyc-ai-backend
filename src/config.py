from pydantic import BaseSettings
import os


class Settings(BaseSettings):
    DATABASE_URL: str = os.environ["DATABASE_URL"]
    DATABASE_NAME: str = os.environ["DATABASE_NAME"]
    # MONGO_INITDB_DATABASE: str = os.environ["MONGO_INITDB_DATABASE"]

    JWT_SECRET_KEY: str = os.environ["JWT_SECRET_KEY"]
    REFRESH_TOKEN_EXPIRES_IN: int = os.environ["REFRESH_TOKEN_EXPIRES_IN"]
    ACCESS_TOKEN_EXPIRES_IN: int = os.environ["ACCESS_TOKEN_EXPIRES_IN"]
    JWT_ALGORITHM: str = os.environ["JWT_ALGORITHM"]
    ACCESS_ID_DIGITAL_OCEAN: str = os.environ["ACCESS_ID_DIGITAL_OCEAN"]
    SECRET_KEY_DIGITAL_OCEAN: str = os.environ["SECRET_KEY_DIGITAL_OCEAN"]

    URL_DIGITAL_OCEAN: str = os.environ["URL_DIGITAL_OCEAN"]

    OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]
    OPENAI_API_ORG_ID: str = os.environ["OPENAI_API_ORG_ID"]

    URL_API: str = os.environ["URL_API"]

    NAME_ENV: str = os.environ["NAME_ENV"]

    ELEVENLABS_API_KEY: str = os.environ["ELEVENLABS_API_KEY"]

    MODE_TEST: bool = os.environ.get("MODE_TEST", "False").lower() in ("true", "1", "yes")


settings = Settings()
