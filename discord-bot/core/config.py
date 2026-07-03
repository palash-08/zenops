from pathlib import Path
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"

if not ENV_PATH.exists():
    print(f"Error: .env file not found at {ENV_PATH}")
    sys.exit(1)

class Settings(BaseSettings):
    discord_bot_token: str
    backend_url: str = "http://127.0.0.1:8000"
    bot_activity_type: str = "playing"
    bot_activity_text: str = "Managing your infrastructure"

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        extra="ignore",
    )

settings = Settings()
