from abc import ABC, abstractmethod

from .message import JSONLLMResponse, LLMRequest, LLMResponse


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_response(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    def generate_structured_response(self, request: LLMRequest) -> JSONLLMResponse: ...

    @abstractmethod
    def generate_response_using_schema(
        self, request: LLMRequest, schema: dict
    ) -> JSONLLMResponse: ...
