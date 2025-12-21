# rag/advanced_rag.py
from qdrant_client.http import models
from typing import Optional, List, Dict
from datetime import datetime
from rag.core import RAGSystem

class AdvancedRAGSystem(RAGSystem):
    """Расширенная RAG система с поддержкой фильтров и чанкированием"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunk_size = 1000
        self.chunk_overlap = 200
    
    def chunk_text(self, text: str) -> List[str]:
        """Разбивает текст на перекрывающиеся чанки"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            chunks.append(chunk)
            if i + self.chunk_size >= len(words):
                break
                
        return chunks
    
    def add_article_with_metadata(self, article: Dict) -> List[str]:
        """Добавление статьи с полной метаинформацией и чанкированием"""
        chunks = self.chunk_text(article['content'])
        points = []
        
        for i, chunk in enumerate(chunks):
            # Эмбеддинг для каждого чанка
            embedding = self.model.encode(f"{article['title']} {chunk}").tolist()
            
            # Полные метаданные для фильтрации
            points.append(models.PointStruct(
                id=f"{article.get('id', '')}_{i}",
                vector=embedding,
                payload={
                    "title": article["title"],
                    "content_chunk": chunk,
                    "full_content": article["content"],
                    "url": article.get("url", ""),
                    "date": article.get("date", ""),
                    "author": article.get("author", ""),
                    "source": article.get("source", ""),
                    "thematic": article.get("thematic", ""),
                    "tags": article.get("tags", []),
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            ))
        
        # Пакетная загрузка в Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        return [p.id for p in points]
    
    def search_with_filters(
        self,
        query: str,
        top_k: int = 5,
        author: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        thematic: Optional[str] = None,
        source: Optional[str] = None
    ) -> List[Dict]:
        """Поиск с применением фильтров"""
        query_embedding = self.model.encode(query).tolist()
        
        # Построение фильтра
        filter_conditions = []
        
        if author:
            filter_conditions.append(
                models.FieldCondition(
                    key="author",
                    match=models.MatchValue(value=author)
                )
            )
        
        if thematic:
            filter_conditions.append(
                models.FieldCondition(
                    key="thematic",
                    match=models.MatchValue(value=thematic)
                )
            )
        
        if source:
            filter_conditions.append(
                models.FieldCondition(
                    key="source",
                    match=models.MatchValue(value=source)
                )
            )
        
        if start_date or end_date:
            range_filter = models.Range()
            if start_date:
                range_filter.gte = start_date
            if end_date:
                range_filter.lte = end_date
            
            filter_conditions.append(
                models.FieldCondition(
                    key="date",
                    range=range_filter
                )
            )
        
        # Если есть фильтры, применяем их
        search_filter = None
        if filter_conditions:
            search_filter = models.Filter(
                must=filter_conditions
            )
        
        # Выполняем поиск
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=top_k,
            with_payload=True
        )
        
        # Группируем чанки по статьям
        articles_map = {}
        for hit in results:
            article_id = hit.id.rsplit('_', 1)[0]  # Получаем ID статьи без номера чанка
            
            if article_id not in articles_map:
                articles_map[article_id] = {
                    "score": hit.score,
                    "title": hit.payload["title"],
                    "url": hit.payload["url"],
                    "author": hit.payload.get("author", ""),
                    "source": hit.payload.get("source", ""),
                    "thematic": hit.payload.get("thematic", ""),
                    "content_chunks": [],
                    "full_content": hit.payload.get("full_content", "")
                }
            
            articles_map[article_id]["content_chunks"].append(
                hit.payload["content_chunk"]
            )
        
        # Формируем финальный результат
        final_results = []
        for article in articles_map.values():
            # Объединяем чанки для контекста
            article["combined_content"] = " ".join(article["content_chunks"][:3])  # Берем первые 3 чанка
            del article["content_chunks"]
            final_results.append(article)
        
        return final_results[:top_k]  # Возвращаем топ-N статей