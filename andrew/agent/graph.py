from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

class AgentState(TypedDict):
    query: str
    context: List[Dict]
    response: str
    search_needed: bool

class ArticleSearchAgent:
    def __init__(self, llm_type="gemini", rag_system=None):
        if llm_type == "gemini":
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                temperature=0.3
            )
        else:  # ollama/lmstudio
            self.llm = ChatOllama(
                model="llama2",
                base_url="http://localhost:11434"
            )
        
        self.rag = rag_system
        self.graph = self._build_graph()
    
    def _route_query(self, state: AgentState) -> str:
        """Определяет, нужен ли поиск или можно ответить напрямую"""
        direct_questions = ["привет", "помощь", "start", "help"]
        
        if state["query"].lower() in direct_questions:
            return "direct_response"
        return "search_articles"
    
    def direct_response(self, state: AgentState) -> AgentState:
        """Ответ на общие вопросы"""
        prompt = ChatPromptTemplate.from_template("""
        Ты ассистент для поиска статей. Пользователь спрашивает: {query}
        
        Ответь кратко и полезно. Если это приветствие - представься.
        """)
        
        chain = prompt | self.llm
        response = chain.invoke({"query": state["query"]})
        
        return {**state, "response": response.content}
    
    def search_articles(self, state: AgentState) -> AgentState:
        """Поиск статей через RAG"""
        # 1. Получаем релевантные статьи
        articles = self.rag.search(state["query"])
        
        # 2. Формируем контекст
        context = "\n\n".join([
            f"Статья {i+1}: {art['title']}\n{art['content']}"
            for i, art in enumerate(articles)
        ])
        
        # 3. Генерируем ответ с использованием контекста
        prompt = ChatPromptTemplate.from_template("""
        Ты помощник для поиска статей. На основе контекста ответь на вопрос.
        
        Контекст (релевантные статьи):
        {context}
        
        Вопрос пользователя: {query}
        
        Ответ должен содержать:
        1. Краткий ответ на вопрос
        2. Ссылки на найденные статьи (если есть)
        3. Если статьи не релевантны - сообщи об этом
        
        Ответ:
        """)
        
        chain = prompt | self.llm
        response = chain.invoke({
            "query": state["query"],
            "context": context
        })
        
        return {
            **state,
            "context": articles,
            "response": response.content
        }
    
    def _build_graph(self):
        """Создаем граф агента"""
        workflow = StateGraph(AgentState)
        
        # Добавляем узлы
        workflow.add_node("direct_response", self.direct_response)
        workflow.add_node("search_articles", self.search_articles)
        
        # Определяем начальную точку
        workflow.set_entry_point("route")
        
        # Добавляем условное ветвление
        workflow.add_conditional_edges(
            "route",
            self._route_query,
            {
                "direct_response": "direct_response",
                "search_articles": "search_articles"
            }
        )
        
        # Завершающие узлы
        workflow.add_edge("direct_response", END)
        workflow.add_edge("search_articles", END)
        
        return workflow.compile()
    
    def query(self, user_query: str):
        """Основной метод для запросов"""
        return self.graph.invoke({
            "query": user_query,
            "context": [],
            "response": "",
            "search_needed": True
        })