#!/usr/bin/env python3
"""
Скрипт для инициализации коллекции в Qdrant
"""
import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

# Настройки из переменных окружения
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "documents")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))


def main():
    print(f"🚀 Инициализация Qdrant коллекции '{QDRANT_COLLECTION}'...")

    try:
        # Подключаемся к Qdrant
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY if QDRANT_API_KEY else None,
            timeout=30
        )

        # Проверяем соединение
        collections = client.get_collections()
        print(f"✅ Подключено к Qdrant. Доступные коллекции: {[c.name for c in collections.collections]}")

        # Создаем коллекцию если не существует
        existing_collections = [c.name for c in collections.collections]

        if QDRANT_COLLECTION in existing_collections:
            print(f"ℹ️ Коллекция '{QDRANT_COLLECTION}' уже существует")

            # Проверяем параметры коллекции
            collection_info = client.get_collection(QDRANT_COLLECTION)
            print(f"   Параметры: размерность={collection_info.config.params.vectors.size}, "
                  f"расстояние={collection_info.config.params.vectors.distance}")
        else:
            print(f"📁 Создаем коллекцию '{QDRANT_COLLECTION}'...")

            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE
                )
            )
            print(f"✅ Коллекция '{QDRANT_COLLECTION}' успешно создана")

        # Выводим информацию о коллекции
        collection_info = client.get_collection(QDRANT_COLLECTION)
        print(f"\n📊 Информация о коллекции:")
        print(f"   Имя: {QDRANT_COLLECTION}")
        print(f"   Количество точек: {collection_info.points_count}")
        print(f"   Размерность векторов: {collection_info.config.params.vectors.size}")
        print(f"   Метрика расстояния: {collection_info.config.params.vectors.distance}")

        return 0

    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())