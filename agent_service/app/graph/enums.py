from enum import StrEnum


class NodesEnum(StrEnum):
    RAG_TOOL = "rag_tool"
    ROUTER = "router"
    PLANNER = "planner"
    RETRIEVER = "retriever"
    RESPONSE = "response"
    ERROR = "error"

class ReactEnum(StrEnum):
    THOUGHT = "though"
    EXECUTOR = "executor"
    FINAL = "final"

class StageEnum(StrEnum):
    HUMAN_ANSWER = "human_answer"
    FAILURE = "failure"
    END = "__end__"

class StepStatusEnum(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    NOT_STARTED = "not_started"

class RagFlowStatusEnum(StrEnum):
    SUCCESS = "success"
    PENDING = "pending"

class CollectionsEnum(StrEnum):
    PYTHON = "python"
    AI = "ai"
    LLM = "llm"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    HABR_ARTICLES = "habr_articles"


