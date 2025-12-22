from typing import Optional
from app.config import SETTINGS

from qdrant_client import QdrantClient


class RAGClient:
    """Клиент для работы с векторной БД Qdrant"""

    def __init__(self, qdrant_client: Optional[QdrantClient] = None):
        self.client = qdrant_client
        if not self.client:
            self.client = QdrantClient(
                url=SETTINGS.QDRANT_URL,
            )
        self.embedding_model = None

    async def health_check(self) -> bool:
        """Проверка здоровья сервиса"""
        try:
            self.client.get_collections()
            return True
        except:
            return False


# Глобальный экземпляр клиента RAG
rag_client = RAGClient()