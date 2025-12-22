import json
from typing import Optional
from redis.asyncio import Redis
from datetime import datetime

from app.states import AgentState
from app.config import SETTINGS


class StateManager:
    """Управление состояниями агента в Redis"""

    def __init__(self):
        self.redis_client = None

    async def connect(self):
        try:
            self.redis_client = Redis.from_url(
                SETTINGS.REDIS_URL,  # Используем URL из конфига
                db=SETTINGS.REDIS_DB,
                decode_responses=True,
                health_check_interval=30  # Автоматическая проверка соединения
            )
            await self.redis_client.ping()  # Асинхронная проверка
            print("✓ Connected to Redis")
        except Exception as e:
            print(f"✗ Redis connection error: {e}")
            raise

    async def disconnect(self):
        """Отключиться от Redis"""
        if self.redis_client:
            await self.redis_client.close()

    def _generate_session_id(self, user_id: Optional[str] = None) -> str:
        """Сгенерировать ID сессии"""
        import uuid
        if user_id:
            return f"session_{user_id}_{uuid.uuid4().hex[:8]}"
        return f"session_{uuid.uuid4().hex}"

    async def get_state(self, session_id: str) -> Optional[AgentState]:
        """Получить состояние агента по ID сессии"""
        try:
            data = await self.redis_client.get(f"agent_state:{session_id}")
            if data:
                state_dict = json.loads(data)
                return AgentState(**state_dict)
        except Exception as e:
            print(f"Error getting state: {e}")
        return None

    async def save_state(self, session_id: str, state: AgentState) -> bool:
        """Сохранить состояние агента"""
        try:
            # Приводим модели данных к словарям
            messages = [json.loads(message.model_dump_json()) for message in state["messages"]]
            state["messages"] = messages

            documents = [json.loads(document.model_dump_json()) for document in state["documents"]]
            state["documents"] = documents

            data = json.dumps(state)

            # Сохраняем с TTL
            await self.redis_client.setex(
                f"agent_state:{session_id}",
                SETTINGS.SESSION_TTL,
                data
            )
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False

    async def create_state(self, session_id: Optional[str] = None) -> tuple[str, AgentState]:
        """Создать новое состояние"""
        if not session_id:
            session_id = self._generate_session_id()

        state = AgentState()
        await self.save_state(session_id, state)
        return session_id, state

    async def reset_state(self, session_id: str) -> bool:
        """Сбросить состояние сессии"""
        try:
            await self.redis_client.delete(f"agent_state:{session_id}")
            return True
        except Exception as e:
            print(f"Error resetting state: {e}")
            return False

    async def cleanup_expired_sessions(self):
        """Очистить просроченные сессии (Redis делает это автоматически через TTL)"""
        pass


# Глобальный экземпляр менеджера состояний
state_manager = StateManager()