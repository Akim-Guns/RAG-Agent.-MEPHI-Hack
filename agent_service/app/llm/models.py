from pydantic import BaseModel, Field

from app.graph.enums import NodesEnum, StepStatusEnum, RagFlowStatusEnum


class Step(BaseModel):
    """Шаг плана, который будет выполнять агент"""
    name: NodesEnum = Field(description="Наименование агента")
    task: str = Field(default="Не удалось описать задачу", description="Задача для данного агента")
    comment: str = Field(default="", description="Комментарий от агента после выполнения им задачи")
    status: StepStatusEnum = Field(default=StepStatusEnum.NOT_STARTED, description="Статус выполнения шага")

class Plan(BaseModel):
    """План, который будет выполнять агент. Состоит из шагов."""
    global_task: str = Field(description="Описание глобальной задачи, которую необходимо выполнить")
    require_documents: bool = Field(description="Необходимо ли осуществлять поиск в базе знаний для ответа на запрос")
    plan: list[Step] = Field(default=[], description="Последовательность агентов для решения изначальной задачи")
    reasoning: str = Field(default="Не удалось построить цепочку размышлений", description="Цепочка размышлений, которая описывает, почему был составлен именно такой план")


class RagFlow(BaseModel):
    """Пайплайн раг"""
    status: RagFlowStatusEnum = Field(default=RagFlowStatusEnum.PENDING, description="Статус выполнения задачи, поставленной для RAG агента")
    corrections: str = Field(default="", description="Корректировки, которые необходимо сделать, чтобы задача была выполнена.")
    answer: str = Field(default="", description="Финальный ответ на основе релевантных источников.")
