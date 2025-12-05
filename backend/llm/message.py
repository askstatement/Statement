from enum import Enum
from typing import Dict, List, Optional

from .utils.json import parse_first_json


class LLMMessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage:
    def __init__(self, role: LLMMessageRole, content: str):
        self.role = role
        self.content = content

    def to_dict(self):
        return {"role": self.role, "content": self.content}


class LLMRequest:
    def __init__(
        self,
        messages: List[LLMMessage],
        model: str = "gpt-5",
        params: Dict = {},
    ):
        # Avoid mutable default args
        self.messages: List[LLMMessage] = messages
        self.model: str = model
        self.params: Dict = params if params else {}

    def to_dict(self):
        return {
            "messages": self.messages,
            "model": self.model,
            "params": self.params,
        }

    def add_message(self, message: LLMMessage):
        self.messages.append(message)

    def add_messages(self, _messages: List[LLMMessage]):
        self.messages.extend(_messages)


class LLMResponse:
    def __init__(
        self,
        text: str,
        reasoning: str = "",
        input_token_count: int = 0,
        output_token_count: int = 0,
        reasoning_token_count: int = 0,
        cached_input_token_count: int = 0,
    ):
        self.text: str = text
        self.reasoning: str = reasoning
        self.input_token_count: int = input_token_count
        self.output_token_count: int = output_token_count
        self.reasoning_token_count: int = reasoning_token_count
        self.cached_input_token_count: int = cached_input_token_count

    def get_token_count_dict(self):
        return {
            "input_token_count": self.input_token_count,
            "output_token_count": self.output_token_count,
            "reasoning_token_count": self.reasoning_token_count,
            "cached_input_token_count": self.cached_input_token_count,
        }

    def to_dict(self):
        return {
            "text": self.text,
            "reasoning": self.reasoning,
            "input_token_count": self.input_token_count,
            "output_token_count": self.output_token_count,
            "reasoning_token_count": self.reasoning_token_count,
            "cached_input_token_count": self.cached_input_token_count,
        }


class JSONLLMResponse(LLMResponse):
    def __init__(
        self,
        text: str,
        reasoning: str = "",
        input_token_count: int = 0,
        output_token_count: int = 0,
        reasoning_token_count: int = 0,
        cached_input_token_count: int = 0,
    ):
        super().__init__(
            text,
            reasoning,
            input_token_count,
            output_token_count,
            reasoning_token_count,
            cached_input_token_count,
        )
        self.json_data: dict = parse_first_json(text)

    def get_token_count_dict(self):
        return {
            "input_token_count": self.input_token_count,
            "output_token_count": self.output_token_count,
            "reasoning_token_count": self.reasoning_token_count,
            "cached_input_token_count": self.cached_input_token_count,
        }

    def to_dict(self):
        return {
            "text": self.text,
            "reasoning": self.reasoning,
            "input_token_count": self.input_token_count,
            "output_token_count": self.output_token_count,
            "reasoning_token_count": self.reasoning_token_count,
            "cached_input_token_count": self.cached_input_token_count,
        }
