import asyncio
import datetime
import uuid
from typing import Optional

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_gigachat import GigaChat

from app.graph.enums import StageEnum
from app.graph.nodes import Graph
from app.llm.tools.rag import Doc
from app.models import AgentResponse
from app.states import AgentState

from app.config import SETTINGS

import logging

logging.basicConfig(level=logging.INFO)


class Agent:

    def __init__(
            self,
            message: str,
            state: AgentState | None = None,
            session_id: str | None = None
    ) -> None:
        """Инициализация графа"""
        gigachat = GigaChat(
            credentials=SETTINGS.GIGACHAT_CREDENTIALS,
            model=SETTINGS.MODEL,
            verify_ssl_certs=False
        )
        self.session_id = session_id
        if not self.session_id:
            self.session_id = str(uuid.uuid4())

        self.state: AgentState | None = state
        # Если state не передан, инициаилизируем новый
        if not self.state:
            self.state: AgentState = self.create_initial_state(
                current_phrase=message,
                session_id=self.session_id
            )
        else:
            if self.state["messages"]:
                messages = []
                for message in messages:
                    match message["type"].lower():
                        case "human":
                            processed_message = HumanMessage(**message)
                        case "ai":
                            processed_message = HumanMessage(**message)
                        case "tool":
                            processed_message = ToolMessage(**message)
                        case "system":
                            processed_message = SystemMessage(**message)
                        case _:
                            raise ValueError("Unprocessable message found")
                    messages.append(processed_message)
                self.state["messages"] = messages


            if self.state["documents"]:
                self.state["documents"] = [Doc(**document) for document in self.state["documents"]]

            self.state["task_to_planner"] = message
            self.state["current_phrase"] = message
            self.state["messages"].append(HumanMessage(content=message))

        self.graph = Graph(llm=gigachat)
        # компилируем граф
        self.compiled = self.graph.compile_graph()


    async def invoke(self) -> tuple[AgentResponse, AgentState]:
        """Асинхронный запуск графа"""
        run_config = RunnableConfig(
            run_id=self.session_id,
            recursion_limit=100,
            configurable={
                "thread_id": self.session_id
            }
        )
        state: AgentState =  await self.compiled.ainvoke(
            self.state, run_config
        )

        return self.return_message_and_state_from_state(state)

    @staticmethod
    def return_message_and_state_from_state(state: AgentState) -> tuple[AgentResponse, AgentState]:
        state["next_action"] = None,
        state["iteration"] = 0
        state["current_plan"] = None
        state["current_step"] = None
        if state["error"]:
            return (AgentResponse(
                response="Во время обработки вашего запроса произошли технические неполадки. Пожалуйста, попробуйте перефразировать запрос.",
                sources=state["documents"],
                session_id=state["session_id"],
                is_error=bool(state["error"])
            ), state)
        else:
            return (AgentResponse(
                response=state["final_answer"],
                sources=state["documents"],
                session_id=state["session_id"],
                is_error=False
            ), state)

    @staticmethod
    def create_initial_state(
            current_phrase: str,
            session_id: str,
            messages: Optional[list[BaseMessage]] = None,
            initial_stage: Optional[StageEnum] = None
    ) -> AgentState:
        """
        Создает и возвращает инициализированный экземпляр AgentState

        Args:
            current_phrase: Текущий запрос пользователя
            session_id: Идентификатор сессии
            messages: Существующая история сообщений (опционально)
            initial_stage: Начальная стадия обработки

        Returns:
            AgentState: Инициализированный экземпляр состояния агента
        """
        now = datetime.datetime.now()

        # Если messages не предоставлены, создаем новый список с текущим запросом
        if messages is None:
            messages = [HumanMessage(content=current_phrase)]
        elif not any(isinstance(msg, HumanMessage) for msg in messages):
            # Если есть история, но нет текущего запроса, добавляем его
            messages.append(HumanMessage(content=current_phrase))

        # Создаем экземпляр AgentState с правильным синтаксисом
        agent_state = AgentState(
            # Входные данные
            current_phrase=current_phrase,
            messages=messages,

            # Контекст агента
            session_id=session_id,
            iteration=0,
            current_plan=None,
            current_step=None,
            task_to_planner=current_phrase,  # Начинаем с исходного запроса

            # Мысли и рассуждения
            thoughts=[],
            current_thought="",

            # Инструменты и результаты
            next_action=None,
            documents=[],

            # Финальный результат
            final_answer=None,
            is_finished=False,

            # Метаданные
            error=None,
            start_time=datetime.datetime.strftime(now, format="%Y-%m-%d %H:%M:%S"),
            last_updated=datetime.datetime.strftime(now, format="%Y-%m-%d %H:%M:%S"),

            # Данные графа
            next_stage=initial_stage
        )

        return agent_state

if __name__ == '__main__':
    async def main():
        agent = Agent(
            message="Видел статью про пользу Go для JS разработчика. Расскажи, что там",
            session_id=str(uuid.uuid4()),
        )
        print(await agent.invoke())

    asyncio.run(main())