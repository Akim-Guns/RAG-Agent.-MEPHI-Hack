import getpass
import os
import glob
from pathlib import Path
from dotenv import find_dotenv, load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.documents import Document
from langchain_gigachat import GigaChatEmbeddings
from langchain_gigachat.chat_models import GigaChat
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

load_dotenv(find_dotenv(".env.agent"))

# Правильная настройка GigaChat credentials
if "GIGACHAT_CREDENTIALS" not in os.environ:
    # Если credentials не установлены, запрашиваем у пользователя
    print("Введите GigaChat credentials (client_id:client_secret в base64):")
    credentials = getpass.getpass("GigaChat Credentials: ")
    os.environ["GIGACHAT_CREDENTIALS"] = credentials
elif not os.environ.get("GIGACHAT_CREDENTIALS"):
    # Если переменная пустая, тоже запрашиваем
    print("GIGACHAT_CREDENTIALS не установлена. Введите credentials:")
    credentials = getpass.getpass("GigaChat Credentials: ")
    os.environ["GIGACHAT_CREDENTIALS"] = credentials

# Настройки
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "qdrant")
QDRANT_URL = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "habr_articles"


def load_text_file(file_path):
    """Загрузить текстовый файл"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def chunk_text(text, chunk_size=990, overlap=150):
    """Разбить текст на перекрывающиеся чанки"""
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
        if i + chunk_size >= len(words):
            break

    return chunks


def process_documents():
    """Обработать все .txt файлы в папке"""
    print(f"📂 Загрузка документов из: {DATA_PATH}")

    if not os.path.exists(DATA_PATH):
        print(f"❌ Папка {DATA_PATH} не существует")
        return []

    langchain_documents = []

    # Ищем все .txt файлы
    pattern = os.path.join(DATA_PATH, "**/*.txt")
    for file_path in glob.glob(pattern, recursive=True):
        try:
            text = load_text_file(file_path)
            chunks = chunk_text(text)

            for i, chunk in enumerate(chunks):
                # Создаем объект Document для LangChain
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "source": os.path.basename(file_path),
                        "file_path": file_path,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                )
                langchain_documents.append(doc)

            print(f"  ✅ Загружен: {file_path} ({len(chunks)} чанков)")

        except Exception as e:
            print(f"  ❌ Ошибка обработки {file_path}: {e}")

    return langchain_documents

def collection_exists(client, collection_name):
    """Проверить, существует ли коллекция"""
    try:
        collections = client.get_collections()
        return collection_name in [col.name for col in collections.collections]
    except Exception:
        return False


def test_search(qdrant_store, query, top_k=4):
    """Выполнить тестовый поиск"""
    print(f"\n🔍 Поиск по запросу: '{query}'")
    try:
        results = qdrant_store.similarity_search(query, k=top_k)

        print(f"📊 Найдено {len(results)} результатов:")
        for i, doc in enumerate(results, 1):
            print(f"\n{i}. 📄 {doc.metadata.get('source', 'Unknown')}")
            print(f"   📍 Чанк {doc.metadata.get('chunk_index', 0) + 1}/{doc.metadata.get('total_chunks', 1)}")
            print(f"   📝 {doc.page_content[:200]}...")

    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")


def main():
    """Основная функция загрузки"""
    print("🚀 Начало работы с RAG системой")

    try:
        # Подключаемся к Qdrant для проверки коллекции
        client = QdrantClient(host=QDRANT_URL, port=QDRANT_PORT)

        # Проверяем, существует ли коллекция
        if collection_exists(client, COLLECTION_NAME):
            print(f"✅ Коллекция '{COLLECTION_NAME}' уже существует")

            # Подключаемся к существующей коллекции
            embeddings_model = GigaChatEmbeddings(
                verify_ssl_certs=False,
                model='EmbeddingsGigaR'
            )

            try:
                qdrant = QdrantVectorStore.from_existing_collection(
                    embedding=embeddings_model,
                    collection_name=COLLECTION_NAME,
                    url=f"http://{QDRANT_URL}:{QDRANT_PORT}"
                )

                # Получаем информацию о коллекции
                collection_info = client.get_collection(COLLECTION_NAME)
                print(f"📊 Коллекция содержит {collection_info.points_count} документов")

            except Exception as e:
                if "dimensions" in str(e).lower() and ("2560" in str(e) or "384" in str(e)):
                    print(f"⚠️  Несовпадение размерностей эмбеддингов: {e}")
                    print("🔄 Пересоздаю коллекцию с новыми эмбеддингами...")
                    
                    # Удаляем старую коллекцию
                    client.delete_collection(COLLECTION_NAME)
                    print(f"🗑️  Удалена старая коллекция '{COLLECTION_NAME}'")
                    
                    # Создаем новую коллекцию
                    documents = process_documents()
                    if not documents:
                        print("⚠️ Не найдено документов для обработки")
                        return

                    print(f"📊 Найдено {len(documents)} чанков для загрузки")
                    print("🧠 Инициализация GigaChat Embeddings")
                    
                    qdrant = QdrantVectorStore.from_documents(
                        documents=documents,
                        embedding=embeddings_model,
                        url=f"http://localhost:6333",
                        collection_name=COLLECTION_NAME,
                        force_recreate=True
                    )
                    
                    print(f"✅ Успешно пересоздана коллекция '{COLLECTION_NAME}' с {len(documents)} чанками")
                else:
                    raise e

        else:
            print(f"📝 Коллекция '{COLLECTION_NAME}' не найдена, создаем новую...")

            # 1. Загружаем документы
            documents = process_documents()

            if not documents:
                print("⚠️ Не найдено документов для обработки")
                return

            print(f"📊 Найдено {len(documents)} чанков для загрузки")

            # 2. Инициализируем модель эмбеддингов
            print("🧠 Инициализация GigaChat Embeddings")
            embeddings_model = GigaChatEmbeddings(
                verify_ssl_certs=False,
                model='EmbeddingsGigaR'
            )

            # 3. Создаем коллекцию и загружаем документы
            print(f"🔗 Создаем QdrantVectorStore и загружаем документы")

            qdrant = QdrantVectorStore.from_documents(
                documents=documents,
                embedding=embeddings_model,
                url=f"http://localhost:6333",
                collection_name=COLLECTION_NAME,
                force_recreate=False
            )

            print(f"✅ Успешно загружено {len(documents)} чанков в коллекцию '{COLLECTION_NAME}'")

        # 4. Выполняем тестовые запросы
        print("\n🧪 Выполняем тестовые запросы...")

        test_queries = [
            "Расскажи про LLM",
            "Что такое JavaScript?",
            "Как работает Python?",
            "Расскажи про машинное обучение",
            "Что такое нейросети?"
        ]

        for query in test_queries:
            test_search(qdrant, query)

        print(f"\n✅ Все тестовые запросы выполнены!")
        print(f"💡 Коллекция '{COLLECTION_NAME}' готова к использованию")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    main()