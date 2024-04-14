import os
from fastapi.security import HTTPBearer
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = '.envs/.env'
        env_file_encoding = 'utf-8'

    sentry_token: str = "018d1592-9d44-78e1-87ec-7050e109eebc"
    authjwt_secret_key: str = None
    authjwt_access_token_expires: int = 60 * 5  # 5 minutes
    authjwt_refresh_token_expires: int = 60 * 60 * 24 * 30  # 30 days
    authjwt_denylist_enabled: bool = True
    authjwt_denylist_token_checks: set = {"access", "refresh"}
    authjwt_decode_algorithm: set = {"HS384", "HS512"}
    admin_session_time: int = 60 * 60 * 24  # 24 hours
    OPENAI_API_KEY: str = "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"
    OPENAI_API_ORG_ID: str = "org-TPRbRbkdbEC7IBXXKoVsCC5p"
    # redis_url: str = "redis://localhost:6379/0"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    admin_superuser: str = None
    admin_superuser_password: str = None
    ACCESS_ID_DIGITAL_OCEAN: str = None
    SECRET_KEY_DIGITAL_OCEAN: str = None
    URL_DIGITAL_OCEAN: str = None


# callback to get your configuration
@AuthJWT.load_config
def get_config():
    return Settings()


settings = Settings()

auth_scheme = HTTPBearer()
