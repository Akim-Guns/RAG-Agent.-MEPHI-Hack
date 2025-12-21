from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict

class RAGSystem:
    def __init__(self, model_name="ai-community/GigaChat-Embeddings"):
        self.model = SentenceTransformer(model_name)
        self.client = QdrantClient("localhost", port=6333)
        self.collection_name = "articles"
        
    def init_collection(self):
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.model.get_sentence_embedding_dimension(),
                distance=Distance.COSINE
            )
        )
    
    def add_articles(self, articles: List[Dict]):
        """Добавление статей в векторную БД"""
        points = []
        for i, article in enumerate(articles):
            # Эмбеддинг заголовка + контента
            text = f"{article['title']} {article['content'][:1000]}"
            embedding = self.model.encode(text).tolist()
            
            points.append(PointStruct(
                id=i,
                vector=embedding,
                payload={
                    "title": article["title"],
                    "content": article["content"],
                    "url": article.get("url", ""),
                    "date": article.get("date", "")
                }
            ))
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def search(self, query: str, top_k: int = 5):
        """Поиск релевантных статей"""
        query_embedding = self.model.encode(query).tolist()
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        
        return [
            {
                "score": hit.score,
                "title": hit.payload["title"],
                "content": hit.payload["content"][:500],  # Обрезаем для контекста
                "url": hit.payload["url"]
            }
            for hit in results
        ]