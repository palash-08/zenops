from pathlib import Path
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

# Root of the repository (ZenOpsV1/)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Path to the .env file
ENV_PATH = ROOT_DIR / ".env"

if not ENV_PATH.exists():
    print(f"❌ Error: .env file not found at {ENV_PATH}")
    print("Please create a .env file in the project root.")
    sys.exit(1)

print(f"✅ Found .env at {ENV_PATH}")


class Settings(BaseSettings):
    database_url: str
    discord_bot_token: str
    cognee_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        extra="ignore",
    )


settings = Settings()