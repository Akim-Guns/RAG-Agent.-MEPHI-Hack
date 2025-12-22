import json

from langchain_core.messages import AIMessage
from pydantic import BaseModel

from app.llm.errors import BlackListException, ParserException


class CustomParser:
    def __init__(self, schema: type[BaseModel]):
        self.schema = schema

    @staticmethod
    def parser(message: dict) -> dict:
        ai_message: AIMessage = message["raw"]

        errors = message.get("parsing_errors")
        print(errors)

        text: str = ai_message.content
        finish_reason = ai_message.response_metadata["finish_reason"]

        if finish_reason == "blacklist":
            raise BlackListException(f"Blacklist: {message}")

        try:
            if text.startswith("```json"):
                text = text.strip("```json").strip("```").strip()
            return json.loads(text)
        except json.JSONDecodeError:
            raise ParserException(f"Failed to parse: {message}")

    def validate(self, output: dict) -> BaseModel | dict:
        try:
            return self.schema(**output)
        except Exception as e:
            return output