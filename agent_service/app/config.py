import os

from typing import Optional
from pydantic_settings import BaseSettings

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(".env.agent"))


class Settings(BaseSettings):
    """Настройки приложения через переменные окружения"""

    # FastAPI
    APP_NAME: str = os.getenv("APP_NAME", "Document Agent API")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.0.0")
    DEBUG: bool = os.getenv("DEBUG", False)

    # Redis для кэша состояний
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_DB: int = os.getenv("REDIS_DB", 0)
    SESSION_TTL: int = os.getenv("SESSION_TTL", 600)

    # Qdrant для RAG
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY", None)
    QDRANT_COLLECTION: str = os.getenv("DOCUMENTS", None)

    # LLM (пример для OpenAI)
    GIGACHAT_CREDENTIALS: str = os.getenv("GIGACHAT_CREDENTIALS", None)
    MODEL: str = os.getenv("MODEL", None)
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", None)

    # Агент
    AGENT_MAX_ITERATIONS: int = os.getenv("AGENT_MAX_ITERATIONS", None)
    AGENT_MAX_TOKENS: int = os.getenv("AGENT_MAX_TOKENS", None)


SETTINGS = Settings()


if __name__ == "__main__":
    settings = Settings()
    print(settings)