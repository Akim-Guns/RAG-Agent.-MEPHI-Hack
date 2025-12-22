from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.llm.tools.rag import Doc


# Запросы
class AgentRequest(BaseModel):
    """Запрос к агенту"""
    query: str = Field(..., description="Запрос пользователя")
    session_id: Optional[str] = Field(None, description="ID сессии (опционально, если передается в заголовке)")


class RAGRequest(BaseModel):
    """Запрос к RAG"""
    query: str = Field(..., description="Поисковый запрос")
    index: str = Field("documents", description="Название коллекции/индекса")
    limit: int = Field(5, description="Количество результатов", ge=1, le=20)


# Ответы
class Document(BaseModel):
    """Документ из векторной БД"""
    id: str
    text: str
    metadata: Dict[str, Any]
    score: float


class RAGResponse(BaseModel):
    """Ответ от RAG"""
    results: List[Document]
    query: str
    total: int


class AgentResponse(BaseModel):
    """Ответ от агента"""
    response: str = Field(..., description="Текст ответа")
    sources: list[Doc] = Field(default_factory=list, description="Источники информации")
    session_id: str = Field(..., description="ID сессии")
    is_error: bool = Field(description="Случилась ли ошибка")


# Состояние агента
class AgentState(BaseModel):
    """Состояние агента для сессии"""
    history: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_message(self, role: str, content: str, **kwargs):
        """Добавить сообщение в историю"""
        message = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        message.update(kwargs)
        self.history.append(message)
        self.updated_at = datetime.now()

    def get_conversation_context(self, max_messages: int = 10) -> str:
        """Получить контекст диалога для промпта"""
        recent_history = self.history[-max_messages:]
        context = []
        for msg in recent_history:
            role = "Пользователь" if msg["role"] == "user" else "Ассистент"
            context.append(f"{role}: {msg['content']}")
        return "\n".join(context)