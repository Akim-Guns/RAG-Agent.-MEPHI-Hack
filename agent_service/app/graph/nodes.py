from typing import Any, Literal, Optional

from gigachat.exceptions import GigaChatException
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_gigachat import GigaChat
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel

from app.graph.config import GraphConfig
from app.graph.descriptions import PLAN_STEPS, COLLECTIONS
from app.graph.enums import NodesEnum, StepStatusEnum, StageEnum, ReactEnum, RagFlowStatusEnum
from app.llm.errors import BlackListException
from app.llm.models import Plan, Step, RagFlow
from app.llm.parser import CustomParser
from app.llm.prompts import PlannerPrompts, RagPrompts, ResponsePrompt
from app.llm.tools.rag import rag_tool
from app.states import AgentState


class Graph:

    def __init__(self, llm: GigaChat) -> None:
        self.llm = llm
        self.config = GraphConfig


    def compile_graph(self) -> CompiledStateGraph:
        graph = StateGraph(AgentState)
        graph.add_node(NodesEnum.ROUTER, self.router_node)
        graph.add_node(NodesEnum.PLANNER, self.planner_node)
        graph.add_node(NodesEnum.RETRIEVER, self.retrieve_node)
        graph.add_node(ReactEnum.THOUGHT, self.reasoning_node)
        graph.add_node(ReactEnum.FINAL, self.final_react_node)
        graph.add_node(NodesEnum.RAG_TOOL, self.rag_tool)
        graph.add_node(NodesEnum.RESPONSE, self.response_node)

        graph.set_entry_point(NodesEnum.ROUTER)

        compiled = graph.compile()

        return compiled

    async def get_chain(
            self,
            data: dict | str,
            prompt: str | None = None,
            tools: Optional[list] = None
    ) -> AIMessage:
        """вызов модели без Structured Output"""
        llm = self.llm
        if prompt:
            prompt_template = PromptTemplate.from_template(prompt)
            if tools:
                llm = llm.bind_functions(tools)
            chain = prompt_template | llm
            future: AIMessage = await chain.ainvoke(data)
            if future.response_metadata.get("finish_reason") == "blacklist":
                raise BlackListException
            return future
        else:
            llm = self.llm
            if tools:
                llm = llm.bind_tools(tools)
            future: AIMessage = await llm.ainvoke(data)
            if future.response_metadata.get("finish_reason") == "blacklist":
                raise BlackListException
            return future

    async def get_chain_with_structured_output(
            self,
            schema: dict[str, Any] | type[BaseModel],
            data: dict[str, Any],
            prompt: ChatPromptTemplate | None = None,
            system_prompt: str | None = None,
            user_prompt: str | None = None,
            use_format_instructions: bool = False,
            parser: Optional[CustomParser] = None
    ) -> BaseModel | dict:
        """Вызов модели с Structured Output"""
        try:
            llm = self.llm
            structured_llm = llm.with_structured_output(
                schema=schema,
                method="function_calling" if not use_format_instructions else "format_instructions",
                include_raw=True
            )

            if not (prompt and isinstance(prompt, ChatPromptTemplate)):
                prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", user_prompt)])

            if parser:
                parser_ = parser.parser
                chain = prompt | structured_llm | parser_
            else:
                raise ValueError("parser must be provided")
            raw = await chain.ainvoke(
                input=data,
                verbose=True
            )
            return parser.validate(raw)

        except GigaChatException as e:
            raise e

    async def router_node(self, state: AgentState) -> Command[
        Literal[
            NodesEnum.ROUTER,
            NodesEnum.PLANNER,
        ]
    ]:
        """Определяет следующий узел на основе текущего состояния"""

        # Если агент отчитался, что закончил действовать, переходим к финальной стадии - формированию ответа
        if state.get("is_finished", False):
            return Command(
                goto=NodesEnum.RESPONSE,
                update={
                    "next_action": NodesEnum.RESPONSE,
                }
            )

        # Если превышен лимит итераций, необходимо сформировать ответ as-is
        if state["iteration"] >= self.config.max_iterations:
            return Command(
                goto=NodesEnum.RESPONSE,
                update={
                    "next_action": "respond",
                    "current_thought": "Достигнут лимит итераций. Нужно дать финальный ответ."
                }
            )

        if state["next_action"] and (state["next_action"] in NodesEnum.__members__.values() or state["next_action"] in ReactEnum.__members__.values()):
            return Command(
                goto=state["next_action"],
            )
        else:
            return Command(
                goto=NodesEnum.PLANNER
            )

    # ________________PLANNER_______________________
    async def planner_node(self, state: AgentState) -> Command[
        Literal[
            NodesEnum.ROUTER,
        ]
    ]:
        """Узел рассуждений и планирования - генерирует план для решения задачи"""
        try:
            task_to_planner = state.get("task_to_planner") if not state.get("task_to_planner") else state["current_phrase"]
            current_plan = Plan(**state["current_plan"]) if state["current_plan"] and isinstance(state["current_plan"], dict) else state["current_plan"]
            system_prompt_template = PlannerPrompts.system_prompt
            model = Plan
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt_template),
                    ("human", "Необходимо составить план к запросу: {input}")
                ]
            ).partial(
                sender="Пользователь",
                available_steps=PLAN_STEPS,
                schema=model.model_json_schema()
            )

            parser = CustomParser(schema=model)

            plan: Plan = await self.get_chain_with_structured_output(
                data={
                    "input": task_to_planner
                },
                prompt=prompt,
                schema=model,
                use_format_instructions=True,
                parser=parser
            )

            state["current_plan"] = plan
            state["task_to_planner"] = None # Задача для планировщика исполнена -> обнуляем
            state["current_step"] = state["current_plan"].plan[0]
            state["next_action"] = state["current_step"].name

            return Command(
                goto=NodesEnum.ROUTER,
                update={**state}
            )

        except Exception as e:
            raise e

    async def reasoning_node(self, state: AgentState) -> Command[
        Literal[
            NodesEnum.ROUTER,
        ]
    ]:
        current_plan = Plan(**state["current_plan"]) if state["current_plan"] and isinstance(state["current_plan"], dict) else state["current_plan"]
        current_step = Step(**state["current_step"]) if state["current_step"] and isinstance(state["current_step"], dict) else state["current_step"]
        task = current_step.task
        current_iteration = state["iteration"]

        prompt = RagPrompts.reasoning_system_prompt

        ai_message = await self.get_chain(
            prompt=prompt,
            data={
                "messages": state["messages"],
                "current_task": task,
                "collections": COLLECTIONS
            }
        )

        current_step.status = StepStatusEnum.PENDING
        state["messages"].append(ai_message)
        state["current_step"] = current_step
        state["next_action"] = NodesEnum.RETRIEVER

        print(ai_message)

        return Command(
            goto=NodesEnum.ROUTER,
            update={**state}
        )


    async def retrieve_node(self, state: AgentState) -> Command[
        Literal[
            NodesEnum.ROUTER,
        ]
    ]:
        """Поиск документов через RAG"""

        # Извлекаем вопросы для поиска
        current_plan = Plan(**state["current_plan"]) if state["current_plan"] and isinstance(state["current_plan"], dict) else state["current_plan"]
        current_step = Step(**state["current_step"]) if state["current_step"] and isinstance(state["current_step"], dict) else state["current_step"]
        task = current_step.task
        if current_step.status != StepStatusEnum.PENDING:
            print("Мысль не найдена. Надо подумать.")
            return Command(
                goto=NodesEnum.ROUTER,
                update={
                    "next_action": ReactEnum.THOUGHT
                }
            )
        current_iteration = state["iteration"]

        prompt = RagPrompts.retrieve_system_prompt

        ai_message = await self.get_chain(
            prompt=prompt,
            data={
                "messages": state["messages"],
                "current_task": task,
                "collections": COLLECTIONS
            },
            tools=[rag_tool]
        )

        current_step.status = StepStatusEnum.PENDING
        state["messages"].append(ai_message)
        state["current_step"] = current_step

        print(ai_message)

        if ai_message.tool_calls:
            return Command(
                goto=NodesEnum.RAG_TOOL,
                update={**state}
            )

        print("not a tool call")

        state["next_action"] = ReactEnum.THOUGHT
        if ai_message.content == "END":
            state["next_action"] = ReactEnum.FINAL
        state["iteration"] += 1

        return Command(
            goto=NodesEnum.ROUTER,
            update={**state}
        )

    async def final_react_node(self, state: AgentState) -> Command[
        Literal[NodesEnum.ROUTER]
    ]:
        try:
            current_plan = Plan(**state["current_plan"]) if state["current_plan"] and isinstance(state["current_plan"], dict) else state["current_plan"]
            current_step = Step(**state["current_step"]) if state["current_step"] and isinstance(state["current_step"], dict) else state["current_step"]
            task = current_step.task
            system_prompt_template = RagPrompts.final_system_prompt
            model = RagFlow
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt_template),
                    ("human", "Дай финальный ответ по задаче, если она выполнена. Текст задачи: {input}")
                ]
            ).partial(
                messages=state["messages"],
                schema=model.model_json_schema()
            )

            parser = CustomParser(schema=model)

            rag_flow: RagFlow = await self.get_chain_with_structured_output(
                data={
                    "input": task
                },
                prompt=prompt,
                schema=model,
                use_format_instructions=True,
                parser=parser
            )

            print(rag_flow)

            if rag_flow.status == RagFlowStatusEnum.SUCCESS:
                current_step.status = StepStatusEnum.SUCCESS
                ai_message = AIMessage(content=rag_flow.answer)
                current_step = current_plan.plan[-1]
                return Command(
                    goto=NodesEnum.ROUTER,
                    update={
                        "messages": state["messages"] + [ai_message],
                        "next_action": current_step.name,
                        "current_step": current_step,
                        "final_answer": ai_message.content
                    }
                )
            else:
                ai_message = AIMessage(content=rag_flow.corrections)
                return Command(
                    goto=NodesEnum.ROUTER,
                    update={
                        "messages": state["messages"] + [ai_message],
                        "next_action": ReactEnum.THOUGHT,
                    }
                )
        except Exception as e:
            raise e

    async def rag_tool(self, state: AgentState) -> Command[
        Literal[NodesEnum.RETRIEVER],
    ]:
        tools_by_name = {tool.name: tool for tool in [rag_tool]}
        result = []
        observation = []
        for tool_call in state["messages"][-1].tool_calls:
            tool = tools_by_name[tool_call["name"]]
            observation = await tool.ainvoke(tool_call["args"])
            result.append(ToolMessage(contnet=observation, tool_call_id=tool_call["id"]))
        return Command(
            goto=NodesEnum.RETRIEVER,
            update={
                "messages": state["messages"] + result,
                "sources": observation.documents
            }
        )

    async def response_node(self, state: AgentState) -> Command[
        Literal[StageEnum.END]
    ]:
        print(state["messages"][-1].content)
        ai_message = await self.get_chain(
            prompt=ResponsePrompt.system_prompt,
            data={
                "question": state["current_phrase"],
                "answer": state["final_answer"]
            }
        )

        final_answer = state["final_answer"] + "\n\n" + ai_message.content if state["final_answer"] else ai_message.content

        state["final_answer"] = final_answer
        state["messages"].append(ai_message)
        state["is_finished"] = True

        return Command(
            goto=NodesEnum.END,
            update={**state}
        )



