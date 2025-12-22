from enum import StrEnum


class ReactStep(StrEnum):
    THOUGHT = "thought"
    ACTION = "action"
    ANSWER = "answer"
    ERROR = "error"
