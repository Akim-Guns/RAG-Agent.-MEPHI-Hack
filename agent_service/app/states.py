from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.models import Document


class AgentState(TypedDict):
    """Состояние агента LangGraph"""
    # Входные данные
    input: str  # Текущий запрос пользователя
    messages: List[BaseMessage]  # История диалога (LangChain сообщения)

    # Контекст агента
    session_id: str  # ID сессии
    iteration: int  # Счетчик итераций

    # Мысли и рассуждения
    thoughts: List[str]  # Цепочка мыслей (Reasoning)
    current_thought: str  # Текущая мысль

    # Инструменты и результаты
    next_action: Optional[str]  # Следующее действие
    action_input: Optional[Dict[str, Any]]  # Входные данные для действия
    tool_results: List[Dict[str, Any]]  # Результаты выполнения инструментов
    documents: List[Document]  # Найденные документы

    # Финальный результат
    final_answer: Optional[str]
    sources: List[str]  # Источники для цитирования
    is_finished: bool  # Флаг завершения

    # Метаданные
    error: Optional[str]
    start_time: datetime
    last_updated: datetime