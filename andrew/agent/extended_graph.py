from agent.instrumented_agent import InstrumentedArticleSearchAgent
from agent.graph import AgentState
from core.logging_config import logger
from typing import List, Dict
from langgraph.graph import StateGraph, END

class ExtendedArticleSearchAgent(InstrumentedArticleSearchAgent):
    """Расширенный агент с дополнительными функциями из ТЗ"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = self._build_extended_graph()
    
    def generate_recommendations(self, state: AgentState) -> AgentState:
        """Генерация рекомендаций похожих статей"""
        if not state.get("context"):
            return {**state, "recommendations": []}
        
        logger.info("generating_recommendations", query=state["query"])
        
        try:
            # Берем первую (самую релевантную) статью из контекста
            main_article = state["context"][0]
            
            # Ищем статьи, похожие на основную
            similar_articles = self.rag.search_with_filters(
                query=main_article["title"],
                top_k=3,
                source=main_article.get("source")
            )
            
            # Фильтруем, чтобы не повторять уже найденные статьи
            current_urls = {art.get("url") for art in state["context"]}
            recommendations = [
                art for art in similar_articles 
                if art.get("url") not in current_urls
            ][:2]  # Берем до 2 рекомендаций
            
            return {**state, "recommendations": recommendations}
            
        except Exception as e:
            logger.error("recommendations_generation_failed", error=str(e))
            return {**state, "recommendations": []}
    
    def generate_quiz(self, state: AgentState) -> AgentState:
        """Генерация тестовых вопросов по найденным статьям"""
        if not state.get("context"):
            return {**state, "quiz": []}
        
        logger.info("generating_quiz", articles_count=len(state["context"]))
        
        try:
            # Берем основную статью для генерации вопросов
            main_article = state["context"][0]
            content_preview = main_article.get("combined_content", "")[:2000]
            
            # Промпт для генерации вопросов
            quiz_prompt = f"""
            На основе следующего текста статьи сгенерируй 3 тестовых вопроса с вариантами ответов:
            
            Текст: {content_preview}
            
            Формат:
            1. Вопрос 1
            A) Вариант 1
            B) Вариант 2
            C) Вариант 3
            D) Вариант 4
            Правильный ответ: A
            
            Сгенерируй вопросы разного типа: фактологические, аналитические, на понимание.
            """
            
            # Вызываем LLM
            response = self.llm.invoke(quiz_prompt)
            
            # Парсим ответ
            questions = self._parse_quiz_response(response.content)
            
            return {**state, "quiz": questions}
            
        except Exception as e:
            logger.error("quiz_generation_failed", error=str(e))
            return {**state, "quiz": []}
    
    def _parse_quiz_response(self, text: str) -> List[Dict]:
        """Парсинг сгенерированных вопросов из текста LLM"""
        # Упрощенный парсер - в реальности нужна более сложная логика
        questions = []
        lines = text.strip().split('\n')
        
        current_question = None
        for line in lines:
            if line.startswith(('1.', '2.', '3.', 'Q1:', 'Q2:', 'Q3:')):
                if current_question:
                    questions.append(current_question)
                current_question = {
                    'question': line[3:].strip(),
                    'options': [],
                    'correct_answer': ''
                }
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                if current_question:
                    current_question['options'].append(line.strip())
            elif 'Правильный ответ:' in line or 'Correct answer:' in line:
                if current_question:
                    current_question['correct_answer'] = line.split(':')[-1].strip()
        
        if current_question:
            questions.append(current_question)
        
        return questions
    
    def _build_extended_graph(self):
        """Создание расширенного графа с новыми узлами"""
        workflow = StateGraph(AgentState)
        
        # Добавляем все узлы
        workflow.add_node("route", self._route_query)
        workflow.add_node("direct_response", self.direct_response)
        workflow.add_node("search_articles", self.search_articles)
        workflow.add_node("generate_recommendations", self.generate_recommendations)
        workflow.add_node("generate_quiz", self.generate_quiz)
        
        # Определяем начальную точку
        workflow.set_entry_point("route")
        
        # Условные переходы
        workflow.add_conditional_edges(
            "route",
            lambda state: "direct_response" if state["query"].lower() in ["привет", "помощь", "start", "help"] else "search_articles",
            {
                "direct_response": "direct_response",
                "search_articles": "search_articles"
            }
        )
        
        # Последовательность после поиска
        workflow.add_edge("direct_response", END)
        workflow.add_edge("search_articles", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "generate_quiz")
        workflow.add_edge("generate_quiz", END)
        
        return workflow.compile()