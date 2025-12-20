from typing import List, Optional
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct, Distance, VectorParams
import numpy as np

from app.models import Document, RAGRequest, RAGResponse
from app.config import settings


class RAGClient:
    """Клиент для работы с векторной БД Qdrant"""

    def __init__(self):
        self.client = None
        self.embedding_model = None

    async def connect(self):
        """Подключиться к Qdrant"""
        try:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=30
            )

            # Проверяем соединение
            collections = self.client.get_collections()
            print(f"✓ Connected to Qdrant. Collections: {[c.name for c in collections.collections]}")

            # Инициализируем модель эмбеддингов (для MVP используем локальную)
            self._init_embedding_model()

        except Exception as e:
            print(f"✗ Qdrant connection error: {e}")
            raise

    def _init_embedding_model(self):
        """Инициализировать модель эмбеддингов"""
        try:
            from sentence_transformers import SentenceTransformer
            # Используем легкую модель для MVP
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✓ Embedding model loaded")
        except ImportError:
            print("⚠ SentenceTransformer not installed. Using mock embeddings.")
            self.embedding_model = None

    def _get_embedding(self, text: str) -> List[float]:
        """Получить эмбеддинг для текста"""
        if self.embedding_model:
            return self.embedding_model.encode(text).tolist()
        else:
            # Заглушка для тестирования
            return [0.1] * 384  # Размерность all-MiniLM-L6-v2

    async def search(self, request: RAGRequest) -> RAGResponse:
        """Поиск по векторной БД"""
        try:
            # Получаем эмбеддинг запроса
            query_embedding = self._get_embedding(request.query)

            # Выполняем поиск
            search_result = self.client.search(
                collection_name=request.index or settings.QDRANT_COLLECTION,
                query_vector=query_embedding,
                limit=request.limit,
                with_payload=True,
                with_vectors=False
            )

            # Конвертируем результат в наши модели
            documents = []
            for hit in search_result:
                doc = Document(
                    id=str(hit.id),
                    text=hit.payload.get("text", ""),
                    metadata=hit.payload.get("metadata", {}),
                    score=hit.score
                )
                documents.append(doc)

            return RAGResponse(
                results=documents,
                query=request.query,
                total=len(documents)
            )

        except Exception as e:
            print(f"RAG search error: {e}")
            # Возвращаем пустой результат при ошибке
            return RAGResponse(results=[], query=request.query, total=0)

    async def health_check(self) -> bool:
        """Проверка здоровья сервиса"""
        try:
            self.client.get_collections()
            return True
        except:
            return False


# Глобальный экземпляр клиента RAG
rag_client = RAGClient()