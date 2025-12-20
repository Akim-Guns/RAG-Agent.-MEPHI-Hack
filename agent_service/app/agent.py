# Здесь будет реакт агент на lang graph
import os
import uuid

from langchain_gigachat import GigaChat

from app.graph.nodes import Graph
from app.states import AgentState
from app.utils import init_new_state


class Agent:

    def __init__(self, state: AgentState | None = None, session_id: str | None = None) -> None:
        """Инициализация графа"""
        gigachat = GigaChat(
            credentials=os.environ.get("GIGACHAT_CREDENTIALS"),
            model=os.environ.get("MODEL"),
        )
        self.state = state
        if not self.state:
            self. state: AgentState = init_new_state()
        self.session_id = session_id
        if not self.session_id:
            self.session_id = uuid.uuid4()
        self.graph = Graph(llm=gigachat, state=state)
        self.compiled = self.graph.compile_graph()


    async def invoke(self) -> AgentState:
        """Асинхронный запуск графа"""
        run_config = {
            "configurable": {
                "thread_id": self.session_id
            }
        }
        return await self.compiled.ainvoke(
            self.state, run_config
        )