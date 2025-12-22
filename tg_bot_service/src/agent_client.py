import httpx
import asyncio
from typing import Dict, Any, Optional
from loguru import logger

from src.config import settings


class AgentClient:
    """Клиент для взаимодействия с Agent Service"""
    
    def __init__(self):
        self.base_url = settings.AGENT_SERVICE_URL
        self.timeout = httpx.Timeout(30.0)
        
    async def invoke(self, query: str, session_id: str) -> Dict[str, Any]:
        """
        Отправка запроса к Agent Service
        
        Args:
            query: Текст запроса пользователя
            session_id: ID сессии в формате tg_{user_id}_{timestamp}
            
        Returns:
            Dict с ответом или информацией об ошибке
        """
        url = f"{self.base_url}/invoke"
        
        headers = {
            "X-Session-Id": session_id,
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "response": response.json().get("response", ""),
                        "status_code": response.status_code
                    }
                elif 400 <= response.status_code < 500:
                    # Клиентская ошибка
                    logger.warning(f"Client error from agent: {response.status_code}")
                    return {
                        "success": False,
                        "error": "Некорректный запрос. Пожалуйста, проверьте введенные данные.",
                        "status_code": response.status_code
                    }
                elif 500 <= response.status_code < 600:
                    # Серверная ошибка
                    logger.error(f"Server error from agent: {response.status_code}")
                    return {
                        "success": False,
                        "error": "Сервис временно недоступен, попробуйте позже.",
                        "status_code": response.status_code
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Неожиданный статус ответа: {response.status_code}",
                        "status_code": response.status_code
                    }
                    
        except httpx.ConnectError:
            logger.error(f"Cannot connect to agent service at {self.base_url}")
            return {
                "success": False,
                "error": "Сервис временно недоступен, попробуйте позже.",
                "status_code": 503
            }
        except httpx.TimeoutException:
            logger.error("Request to agent service timed out")
            return {
                "success": False,
                "error": "Превышено время ожидания ответа от сервиса.",
                "status_code": 504
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "success": False,
                "error": "Произошла непредвиденная ошибка.",
                "status_code": 500
            }


# Глобальный экземпляр клиента
agent_client = AgentClient()