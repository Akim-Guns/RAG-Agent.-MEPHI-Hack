#!/usr/bin/env python3
"""
Скрипт для загрузки документов в Qdrant
"""
import os
import sys
import glob
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer
import hashlib

# Настройки
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "documents")
DATA_PATH = os.getenv("DATA_PATH", "./data/documents")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Поддерживаемые форматы
SUPPORTED_EXTENSIONS = ['.txt', '.pdf', '.md', '.docx', '.pptx']


def load_text_file(file_path):
    """Загрузить текстовый файл"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def chunk_text(text, chunk_size=500, overlap=50):
    """Разбить текст на чанки"""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def process_documents():
    """Обработать все документы в папке"""
    print(f"📂 Загрузка документов из: {DATA_PATH}")

    # Проверяем существование папки
    if not os.path.exists(DATA_PATH):
        print(f"❌ Папка {DATA_PATH} не существует")
        return []

    documents = []

    # Ищем все файлы
    for ext in SUPPORTED_EXTENSIONS:
        pattern = os.path.join(DATA_PATH, f"**/*{ext}")
        for file_path in glob.glob(pattern, recursive=True):
            try:
                if ext == '.txt':
                    text = load_text_file(file_path)
                    chunks = chunk_text(text)

                    for i, chunk in enumerate(chunks):
                        doc_id = hashlib.md5(f"{file_path}_{i}".encode()).hexdigest()

                        documents.append({
                            "id": doc_id,
                            "text": chunk,
                            "metadata": {
                                "source": os.path.basename(file_path),
                                "file_path": file_path,
                                "chunk_index": i,
                                "total_chunks": len(chunks)
                            }
                        })

                    print(f"  ✅ Загружен: {file_path} ({len(chunks)} чанков)")

            except Exception as e:
                print(f"  ❌ Ошибка обработки {file_path}: {e}")

    return documents


def main():
    """Основная функция"""
    print("🚀 Начало загрузки документов в Qdrant")

    try:
        # 1. Загружаем документы
        documents = process_documents()

        if not documents:
            print("⚠️ Не найдено документов для обработки")
            return 0

        print(f"📊 Найдено {len(documents)} чанков для загрузки")

        # 2. Инициализируем модель эмбеддингов
        print(f"🧠 Загружаем модель эмбеддингов: {EMBEDDING_MODEL}")
        model = SentenceTransformer(EMBEDDING_MODEL)

        # 3. Подключаемся к Qdrant
        print(f"🔗 Подключаемся к Qdrant: {QDRANT_URL}")
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY if QDRANT_API_KEY else None
        )

        # 4. Генерируем эмбеддинги и загружаем
        print("⚡ Генерируем эмбеддинги и загружаем...")

        points = []
        for i, doc in enumerate(documents):
            # Генерируем эмбеддинг
            embedding = model.encode(doc["text"]).tolist()

            # Создаем точку
            point = PointStruct(
                id=i,
                vector=embedding,
                payload={
                    "text": doc["text"],
                    "metadata": doc["metadata"]
                }
            )
            points.append(point)

            if (i + 1) % 100 == 0:
                print(f"  Обработано {i + 1}/{len(documents)} чанков")

        # Загружаем в Qdrant
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=points
        )

        print(f"✅ Успешно загружено {len(documents)} чанков в коллекцию '{QDRANT_COLLECTION}'")

        # 5. Проверяем результат
        collection_info = client.get_collection(QDRANT_COLLECTION)
        print(f"📊 Итог: {collection_info.points_count} точек в коллекции")

        return 0

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())