from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent.graph import ArticleSearchAgent
from rag.core import RAGSystem
import uvicorn
from typing import List, Dict
from contextlib import asynccontextmanager
from rag.rag import AdvancedRAGSystem
from agent.extended_graph import ExtendedArticleSearchAgent
from core.logging_config import logger
from monitoring.health_check import router as health_router
from monitoring.metrics import router as metrics_router

app = FastAPI(title="Article Search Agent API")

# Инициализация систем
rag = RAGSystem()
agent = ArticleSearchAgent(llm_type="gemini", rag_system=rag)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Запуск
    logger.info("application_startup", version="1.0.0")
    
    # Инициализация компонентов
    app.state.rag = AdvancedRAGSystem()
    app.state.rag.init_collection()
    
    app.state.agent = ExtendedArticleSearchAgent(
        llm_type="gemini",
        rag_system=app.state.rag
    )
    
    yield
    
    # Завершение
    logger.info("application_shutdown")
    # Здесь можно добавить cleanup

app = FastAPI(
    title="Article Search Agent API - Production",
    version="1.0.0",
    lifespan=lifespan
)

# Подключаем роутеры мониторинга
app.include_router(health_router)
app.include_router(metrics_router)

# Зависимость для получения агента
def get_agent():
    return app.state.agent

def get_rag():
    return app.state.rag

class QueryRequest(BaseModel):
    query: str
    user_id: str = None

class ArticleAddRequest(BaseModel):
    articles: List[Dict]

@app.post("/query")
async def process_query(request: QueryRequest):
    """Основной endpoint для запросов"""
    try:
        result = agent.query(request.query)
        return {
            "response": result["response"],
            "articles": result.get("context", []),
            "user_id": request.user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add_articles")
async def add_articles(request: ArticleAddRequest):
    """Добавление новых статей"""
    rag.add_articles(request.articles)
    return {"status": "success", "added": len(request.articles)}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)