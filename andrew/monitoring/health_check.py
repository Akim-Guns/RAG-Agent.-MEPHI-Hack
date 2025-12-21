from fastapi import APIRouter, HTTPException
from prometheus_client import generate_latest
import httpx
from core.logging_config import logger
from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timezone
from monitoring.metrics import QDRAIN_STATUS, LLM_STATUS, REGISTRY

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

class HealthStatus(BaseModel):
    status: str
    components: Dict[str, str]
    timestamp: str
    version: str

async def check_qdrant() -> bool:
    """Проверка соединения с Qdrant"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://qdrant:6333")
            return response.status_code == 200
    except Exception as e:
        logger.warning("qdrant_health_check_failed", error=str(e))
        return False

async def check_llm() -> bool:
    """Проверка доступности LLM провайдера"""
    try:
        # Проверка для разных провайдеров
        if self.llm_type == "gemini":
            # Простой тестовый запрос
            test_prompt = "Hello"
            await self.llm.agenerate([test_prompt])
            return True
        else:  # Ollama/LMStudio
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://ollama:11434/api/tags")
                return response.status_code == 200
    except Exception as e:
        logger.warning("llm_health_check_failed", error=str(e))
        return False

@router.get("/health")
async def health_check() -> HealthStatus:
    """Полная проверка здоровья системы"""
    components = {}
    
    # Проверяем все компоненты
    qdrant_ok = await check_qdrant()
    llm_ok = await check_llm()
    
    # Обновляем метрики статуса
    QDRAIN_STATUS.set(1 if qdrant_ok else 0)
    LLM_STATUS.set(1 if llm_ok else 0)
    
    components["qdrant"] = "healthy" if qdrant_ok else "unhealthy"
    components["llm"] = "healthy" if llm_ok else "unhealthy"
    components["api"] = "healthy"
    
    # Определяем общий статус
    overall_status = "healthy" if all([qdrant_ok, llm_ok]) else "degraded"
    
    return HealthStatus(
        status=overall_status,
        components=components,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0"
    )

@router.get("/metrics")
async def metrics():
    """Эндпоинт для Prometheus"""
    return generate_latest(REGISTRY)