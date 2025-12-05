from typing_extensions import Dict

from llm.message import JSONLLMResponse, LLMResponse
from llm.provider import BaseLLMProvider
from llm.tool import Tool, ToolSet


class Agent:
    def __init__(self, name, provider: BaseLLMProvider):
        self.name = name
        self.provider = provider
        self.total_token_usage = {
            "input_token_count": 0,
            "output_token_count": 0,
            "reasoning_token_count": 0,
            "cached_input_token_count": 0,
        }

    def add_token_usage(self, token_usage_dict: Dict):
        self.total_token_usage["input_token_count"] += token_usage_dict.get(
            "input_token_count", 0
        )
        self.total_token_usage["output_token_count"] += token_usage_dict.get(
            "output_token_count", 0
        )
        self.total_token_usage["reasoning_token_count"] += token_usage_dict.get(
            "reasoning_token_count", 0
        )
        self.total_token_usage["cached_input_token_count"] += token_usage_dict.get(
            "cached_input_token_count", 0
        )

    def reset_token_usage(self):
        self.token_usage_dict = {
            "input_token_count": 0,
            "output_token_count": 0,
            "reasoning_token_count": 0,
            "cached_input_token_count": 0,
        }

    def generate_response(self, request) -> LLMResponse:
        response = self.provider.generate_response(request)
        self.add_token_usage(response.get_token_count_dict())
        return response

    def generate_structured_response(self, request) -> JSONLLMResponse:
        response = self.provider.generate_structured_response(request)
        self.add_token_usage(response.get_token_count_dict())
        return response

    def generate_response_using_schema(
        self, request, response_schema: Dict
    ) -> JSONLLMResponse:
        response = self.provider.generate_response_using_schema(
            request, response_schema
        )
        self.add_token_usage(response.get_token_count_dict())
        return response

    def handle_request(self, *args, **kwargs):
        pass
