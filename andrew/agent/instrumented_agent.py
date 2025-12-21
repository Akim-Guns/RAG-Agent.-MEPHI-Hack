# agent/instrumented_agent.py
from core.logging_config import logger
import time
from typing import Dict, Any
from langgraph.graph import StateGraph
from pydantic import BaseModel
from agent.graph import ArticleSearchAgent, AgentState

class InstrumentedArticleSearchAgent(ArticleSearchAgent):
    """Агент с интегрированным логированием и метриками"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = {
            'total_queries': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'avg_response_time': 0
        }
    
    def search_articles(self, state: AgentState) -> AgentState:
        """Переопределённый метод поиска с логированием"""
        start_time = time.time()
        
        # Логируем начало операции
        logger.info(
            "rag_search_started",
            query=state["query"],
            user_id=state.get("user_id"),
            search_needed=state.get("search_needed", True)
        )
        
        try:
            # Выполняем поиск
            result = super().search_articles(state)
            
            # Логируем успех
            search_time = time.time() - start_time
            logger.info(
                "rag_search_completed",
                query=state["query"],
                found_articles=len(result.get("context", [])),
                search_time_seconds=search_time,
                llm_model=self.llm.model_name if hasattr(self.llm, 'model_name') else 'unknown'
            )
            
            # Обновляем метрики
            self.metrics['successful_searches'] += 1
            self.metrics['total_queries'] += 1
            
            return result
            
        except Exception as e:
            # Логируем ошибку
            logger.error(
                "rag_search_failed",
                query=state["query"],
                error=str(e),
                error_type=type(e).__name__,
                search_time_seconds=time.time() - start_time
            )
            
            self.metrics['failed_searches'] += 1
            self.metrics['total_queries'] += 1
            
            # Возвращаем fallback-ответ
            return {
                **state,
                "response": "Извините, произошла ошибка при поиске статей.",
                "context": [],
                "error": str(e)
            }