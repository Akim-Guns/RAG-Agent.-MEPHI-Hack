from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Telegram Bot
    TELEGRAM_TOKEN: str = Field(..., description="Telegram Bot Token")
    
    # Agent Service
    AGENT_SERVICE_URL: str = Field(
        default="http://localhost:8000",
        description="URL of the Agent Service"
    )
    
    # Session configuration
    SESSION_TIMEOUT: int = Field(
        default=3600,
        description="Session timeout in seconds (for information only)"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
