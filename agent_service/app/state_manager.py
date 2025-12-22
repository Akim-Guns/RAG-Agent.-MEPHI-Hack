import json
from typing import Optional
import redis.asyncio as redis
from datetime import datetime

from app.models import AgentState
from app.config import SETTINGS


class StateManager:
    """Управление состояниями агента в Redis"""

    def __init__(self):
        self.redis_client = None

    async def connect(self):
        """Подключиться к Redis"""
        try:
            self.redis_client = redis.from_url(
                SETTINGS.REDIS_URL,
                password=SETTINGS.REDIS_PASSWORD,
                db=SETTINGS.REDIS_DB,
                decode_responses=True
            )
            await self.redis_client.ping()
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
                # Конвертируем строки времени обратно в datetime
                state_dict["created_at"] = datetime.fromisoformat(state_dict["created_at"])
                state_dict["updated_at"] = datetime.fromisoformat(state_dict["updated_at"])
                return AgentState(**state_dict)
        except Exception as e:
            print(f"Error getting state: {e}")
        return None

    async def save_state(self, session_id: str, state: AgentState) -> bool:
        """Сохранить состояние агента"""
        try:
            # Обновляем время изменения
            state.updated_at = datetime.now()

            # Конвертируем в словарь и сериализуем
            state_dict = state.dict()
            state_dict["created_at"] = state_dict["created_at"].isoformat()
            state_dict["updated_at"] = state_dict["updated_at"].isoformat()

            data = json.dumps(state_dict)

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