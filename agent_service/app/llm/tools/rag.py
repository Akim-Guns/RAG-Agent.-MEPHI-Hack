import logging
import traceback

from langchain_core.documents import Document
from langchain_gigachat import GigaChatEmbeddings
from langchain_gigachat.tools.giga_tool import giga_tool
from pydantic import BaseModel, Field

from langchain_qdrant import QdrantVectorStore

from app.config import SETTINGS


class Doc(BaseModel):
    page_content: str
    source: str
    collection_name: str


class RagResult(BaseModel):
    """Описание ответа от RAG"""
    documents: list[Doc] = Field(description="Найденные документы")
    status: bool = Field(description="True, если операция выполнена успешно, False, если операция провалилась")

few_shot_examples = [
    {
        "request": """Найти в коллекции данных Python информацию по запросу "Что такое LLM?".""",
        "params": {"collection_name": "Python", "rag_request": "Что такое LLM?"}
    },
    {
        "request": """Найти в коллекции данных Java информацию по запросу "Актуальные новости Spring".""",
        "params": {"collection_name": "Java", "rag_request": "Актуальные новости Spring"}
    },
]


@giga_tool(few_shot_examples=few_shot_examples)
async def rag_call(
        collection_name: str = Field(description="Название коллекции данных, в которой будет производиться поиск"),
        rag_request: str = Field(description="Текст запроса для RAG")
    ) -> RagResult:
    """Вызов RAG для поиска релевантной информации"""
    try:
        logging.info(
            msg={"event": "Вызов RAG", "collection_name": collection_name, "rag_request": rag_request}
        )
        embeddings = GigaChatEmbeddings(
            credentials=SETTINGS.GIGACHAT_CREDENTIALS,
            verify_ssl_certs=False,
            model=SETTINGS.EMBEDDING_MODEL
        )

        qdrant = QdrantVectorStore.from_existing_collection(
            embedding=embeddings,
            collection_name=collection_name,
            url=SETTINGS.QDRANT_URL,
        )

        logging.info(
            msg={"event": "Вызов RAG", "collection_name": collection_name, "rag_request": rag_request}
        )

        docs: list[Document] = await qdrant.asimilarity_search(
            query=rag_request,
            k=6,
            timeout=15
        )
        result_docs = [
            Doc(
                page_content=it.page_content,
                source=it.metadata.get("source"),
                collection_name=it.metadata.get("_collection_name"),
            ) for it in docs
        ]

        return RagResult(documents=result_docs, status=True)
    except Exception as e:
        print("ПРОИЗОШЛА ОШИБКА ПОИСКА", e)
        return RagResult(documents=[], status=False)


rag_tool = rag_call

if __name__ == "__main__":
    import asyncio

    async def rag_call_test(
            collection_name: str = Field(description="Название коллекции данных, в которой будет производиться поиск"),
            rag_request: str = Field(description="Текст запроса для RAG")
    ) -> RagResult:
        """Вызов RAG для поиска релевантной информации"""
        try:
            embeddings = GigaChatEmbeddings(
                credentials=SETTINGS.GIGACHAT_CREDENTIALS,
                verify_ssl_certs=False,
                model=SETTINGS.EMBEDDING_MODEL
            )
            print(SETTINGS.QDRANT_URL)

            qdrant = QdrantVectorStore.from_existing_collection(
                embedding=embeddings,
                collection_name=collection_name,
                url=SETTINGS.QDRANT_URL,
            )

            docs: list[Document] = await qdrant.asimilarity_search(
                query=rag_request,
                k=6,
                timeout=15
            )
            result_docs = [
                Doc(
                    page_content=it.page_content,
                    source=it.metadata.get("source"),
                    collection_name=it.metadata.get("_collection_name"),
                ) for it in docs
            ]

            return RagResult(documents=result_docs, status=True)
        except Exception as e:
            print("ПРОИЗОШЛА ОШИБКА ПОИСКА", e, str(traceback.format_exc()))
            return RagResult(documents=[], status=False)

    async def main():
        print(await rag_call_test(
            collection_name="habr_articles",
            rag_request="Python"
        ))

    asyncio.run(main())
