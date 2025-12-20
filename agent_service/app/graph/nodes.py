from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage
from langchain_gigachat import GigaChat
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.states import AgentState


class Graph:

    def __init__(self, llm: GigaChat, state: AgentState) -> None:
        self.llm = llm
        self.graph = StateGraph(state)


    def compile_graph(self) -> CompiledStateGraph:
        self.graph.add_node("agent", self.agent_node)
        self.graph.add_node("retrieve", self.retrieve_node)
        self.graph.add_node("final", self.final_node)
        self.graph.add_node("error", self.error_node)

        self.graph.set_entry_point("agent")

        compiled = self.graph.compile()

        return compiled

    # def think_node(self, state: AgentState) -> dict[str, Any]:
    #     """Узел рассуждений - генерирует мысли о том, как решить задачу"""
    #
    #     system_prompt = """Ты - помощник, который думает вслух. Твоя задача:
    #     1. Проанализируй запрос пользователя
    #     2. Подумай, какая информация нужна для ответа
    #     3. Определи, нужно ли искать документы
    #     4. Сформулируй план действий
    #
    #     Формат вывода:
    #     Мысль: [Твоя мысль]
    #     План: [План действий]
    #     Вопросы: [Вопросы для поиска]"""
    #
    #     # Формируем промпт с историей
    #     history = "\n".join([f"{msg.type}: {msg.content}"
    #                          for msg in state["messages"][-5:]])
    #
    #     prompt = f"""
    #     История:
    #     {history}
    #
    #     Запрос: {state['input']}
    #
    #     Найденные документы: {len(state.get('documents', []))}
    #
    #     Подумай и составь план:"""
    #
    #     # Вызываем LLM для генерации мысли
    #     response = self.llm.invoke([
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": prompt}
    #     ])
    #
    #     # Парсим ответ
    #     thought = self._parse_thought(response.content)
    #
    #     return {
    #         "current_thought": thought["thought"],
    #         "thoughts": state.get("thoughts", []) + [thought["thought"]],
    #         "action_input": {"plan": thought["plan"], "questions": thought["questions"]}
    #     }
    #
    # def retrieve_node(self, state: AgentState) -> dict[str, Any]:
    #     """Поиск документов через RAG"""
    #
    #     # Извлекаем вопросы для поиска
    #     questions = state.get("action_input", {}).get("questions", [])
    #     if not questions:
    #         # Если вопросов нет, используем запрос пользователя
    #         questions = [state["input"]]
    #
    #     # Ищем документы для каждого вопроса
    #     all_documents = []
    #     for question in questions:
    #         documents = self.rag_client.search(
    #             query=question,
    #             limit=self.config.retrieval_limit
    #         )
    #         all_documents.extend(documents)
    #
    #     # Дедюплицируем документы
    #     unique_docs = self._deduplicate_documents(all_documents)
    #
    #     return {
    #         "documents": unique_docs,
    #         "tool_results": [{
    #             "tool": "retrieve",
    #             "input": questions,
    #             "output": f"Найдено {len(unique_docs)} документов",
    #             "timestamp": datetime.now()
    #         }]
    #     }
    #
    # def analyze_node(self, state: AgentState) -> dict[str, Any]:
    #     """Анализ найденных документов"""
    #
    #     if not state.get("documents"):
    #         return {"error": "Нет документов для анализа"}
    #
    #     # Формируем контекст для анализа
    #     documents_text = "\n\n".join([
    #         f"Документ {i + 1} (релевантность: {doc.score:.2f}):\n{doc.text[:500]}..."
    #         for i, doc in enumerate(state["documents"][:5])
    #     ])
    #
    #     analysis_prompt = f"""
    #     Проанализируй найденные документы и ответь на вопросы:
    #
    #     Документы:
    #     {documents_text}
    #
    #     Вопрос пользователя: {state['input']}
    #
    #     Ответь:
    #     1. Какие документы наиболее релевантны?
    #     2. Что в них сказано по теме вопроса?
    #     3. Есть ли противоречия между документами?
    #     4. Какую информацию можно использовать для ответа?
    #     """
    #
    #     # Анализируем документы
    #     analysis = self.llm.invoke([
    #         {"role": "system", "content": "Ты - аналитик документов"},
    #         {"role": "user", "content": analysis_prompt}
    #     ])
    #
    #     return {
    #         "tool_results": state.get("tool_results", []) + [{
    #             "tool": "analyze",
    #             "input": f"{len(state['documents'])} документов",
    #             "output": analysis.content,
    #             "timestamp": datetime.now()
    #         }],
    #         "current_thought": analysis.content[:500] + "..."
    #     }
    #
    # def synthesize_node(self, state: AgentState) -> dict[str, Any]:
    #     """Синтез информации в единый ответ"""
    #
    #     # Собираем всю информацию
    #     thoughts = "\n".join(state.get("thoughts", []))
    #     tool_results = "\n".join([
    #         f"{res['tool']}: {res['output']}"
    #         for res in state.get("tool_results", [])
    #     ])
    #
    #     synthesis_prompt = f"""
    #     На основе всей информации сформулируй полный ответ:
    #
    #     Мысли агента:
    #     {thoughts}
    #
    #     Результаты работы:
    #     {tool_results}
    #
    #     Запрос пользователя: {state['input']}
    #
    #     Требования к ответу:
    #     1. Будь точным и информативным
    #     2. Используй информацию из документов
    #     3. Цитируй источники [1], [2], ...
    #     4. Если информации недостаточно, честно скажи об этом
    #     5. Будь вежливым и полезным
    #
    #     Ответ:"""
    #
    #     response = self.llm.invoke([
    #         {"role": "system", "content": "Ты - помощник, синтезирующий информацию"},
    #         {"role": "user", "content": synthesis_prompt}
    #     ])
    #
    #     # Извлекаем цитаты
    #     sources = self._extract_sources(response.content)
    #
    #     return {
    #         "final_answer": response.content,
    #         "sources": sources,
    #         "is_finished": True
    #     }



