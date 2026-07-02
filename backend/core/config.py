import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the absolute path to the root directory (ZenOpsV1)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(ROOT_DIR, ".env")

class Settings(BaseSettings):
    database_url: str
    discord_bot_token: str
    cognee_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        extra="ignore"
    )

settings = Settings()