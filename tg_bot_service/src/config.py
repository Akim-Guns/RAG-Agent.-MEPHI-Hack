import os

from dotenv import load_dotenv, find_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

load_dotenv(find_dotenv(".env.bot"))


class Settings(BaseSettings):
    # Telegram Bot
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    
    # Agent Service
    AGENT_SERVICE_URL: str = os.getenv("AGENT_SERVICE_UR", "http://agent-service:8000")
    
    # Session configuration
    SESSION_TIMEOUT: int = Field(
        default=3600,
        description="Session timeout in seconds (for information only)"
    )

settings = Settings()
