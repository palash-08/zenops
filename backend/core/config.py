import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import sys

# Get the absolute path to the root directory (ZenOpsV1)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))from pathlib import Path
ENV_PATH = os.path.join(ROOT_DIR, ".env")

if ENV_PATH.exists():
    print(f"Found .env at {ENV_PATH}")
else:
    print(f"❌ Error: .env file not found at {ENV_PATH} - Please create one and enter the relevant details")
    sys.exit(1)

class Settings(BaseSettings):
    database_url: str
    discord_bot_token: str
    cognee_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        extra="ignore"
    )

settings = Settings()