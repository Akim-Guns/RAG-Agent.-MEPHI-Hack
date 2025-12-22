import time
import uuid
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class UserSession:
    """Структура для хранения сессии пользователя"""
    user_id: int
    session_id: str
    created_at: float
    last_activity: float


class SessionManager:
    """Менеджер сессий для Telegram бота"""
    
    def __init__(self):
        self.sessions: Dict[int, UserSession] = {}
    
    def generate_session_id(self, user_id: int) -> str:
        """Генерация Session ID в формате tg_{user_id}_{timestamp}"""
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]  # Добавляем уникальность
        return f"tg_{user_id}_{timestamp}_{unique_id}"
    
    def get_or_create_session(self, user_id: int) -> UserSession:
        """Получение или создание сессии для пользователя"""
        if user_id not in self.sessions:
            session_id = self.generate_session_id(user_id)
            current_time = time.time()
            self.sessions[user_id] = UserSession(
                user_id=user_id,
                session_id=session_id,
                created_at=current_time,
                last_activity=current_time
            )
        else:
            # Обновляем время последней активности
            self.sessions[user_id].last_activity = time.time()
        
        return self.sessions[user_id]
    
    def create_new_session(self, user_id: int) -> UserSession:
        """Создание новой сессии для пользователя (явный сброс)"""
        session_id = self.generate_session_id(user_id)
        current_time = time.time()
        
        self.sessions[user_id] = UserSession(
            user_id=user_id,
            session_id=session_id,
            created_at=current_time,
            last_activity=current_time
        )
        
        return self.sessions[user_id]
    
    def get_session(self, user_id: int) -> Optional[UserSession]:
        """Получение сессии пользователя"""
        return self.sessions.get(user_id)
    
    def cleanup_inactive_sessions(self, timeout_seconds: int = 3600):
        """Очистка неактивных сессий (опционально)"""
        current_time = time.time()
        inactive_users = [
            user_id for user_id, session in self.sessions.items()
            if current_time - session.last_activity > timeout_seconds
        ]
        
        for user_id in inactive_users:
            del self.sessions[user_id]


# Глобальный экземпляр менеджера сессий
session_manager = SessionManager()