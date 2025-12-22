from typing import TypedDict, Optional, Any, Annotated
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.graph.enums import StageEnum
from app.llm.models import Plan, Step
from app.llm.tools.rag import Doc
from app.models import Document


class AgentState(TypedDict):
    """Состояние агента LangGraph для обработки пользовательских запросов"""

    # === Входные данные ===
    current_phrase: Annotated[str, "Текущий запрос пользователя для обработки"]
    messages: Annotated[list[BaseMessage | AIMessage | HumanMessage], "История диалога в формате LangChain сообщений"]

    # === Контекст агента ===
    session_id: Annotated[str, "Уникальный идентификатор сессии диалога"]
    iteration: Annotated[int, "Счетчик итераций обработки текущего запроса"]
    current_plan: Annotated[Optional[Plan | dict], "Текущий план выполнения задачи"]
    current_step: Annotated[Optional[Step | dict], "Текущий выполняемый шаг плана"]
    task_to_planner: Annotated[str, "Сформулированная задача для планировщика"]

    # === Мысли и рассуждения ===
    thoughts: Annotated[list[str], "Цепочка рассуждений агента (Reasoning Chain)"]
    current_thought: Annotated[str, "Текущая мысль/рассуждение агента"]

    # === Инструменты и результаты ===
    next_action: Annotated[Optional[str], "Следующее действие для выполнения"]
    documents: Annotated[list[Doc], "Найденные документы и материалы"]

    # === Финальный результат ===
    final_answer: Annotated[Optional[str], "Финальный ответ пользователю"]
    is_finished: Annotated[bool, "Флаг завершения обработки запроса"]

    # === Метаданные ===
    error: Annotated[Optional[str], "Сообщение об ошибке, если возникла"]
    start_time: Annotated[str, "Время начала обработки запроса"]
    last_updated: Annotated[str, "Время последнего обновления состояния"]

    # === Данные графа ===
    next_stage: Annotated[StageEnum, "Текущая стадия обработки запроса"]
