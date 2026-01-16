import json
import os
from typing import Any, Dict, List, Optional

import openai
from openai import OpenAI

from core.logger import Logger
from llm.message import (
    JSONLLMResponse,
    LLMMessage,
    LLMRequest,
    LLMResponse,
)
from llm.provider import BaseLLMProvider
from llm.utils.backoff import retry_with_exponential_backoff

logger = Logger(__name__)

MAX_RETRIES_INVALID_JSON = 3


def _get_nested(obj, *path, default=None):
    cur = obj
    for key in path:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(key, None)
        else:
            cur = getattr(cur, key, None)
    return default if cur is None else cur


class OpenAIProvider(BaseLLMProvider):
    """
    Thin wrapper over OpenAI's Chat Completions API.
    Falls back to a graceful error if the openai client isn't available.
    """

    def __init__(self):
        try:
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
            self.client = OpenAI(api_key=OPENAI_API_KEY)
        except Exception:
            print("OpenAI client not available; OpenAIProvider will not function.")
            self.client = None

    def _to_openai_messages(self, messages: List[LLMMessage]) -> List[Dict]:
        openai_messages = []

        for m in messages:
            openai_messages.append({"role": m.role.value, "content": m.content})

        return openai_messages

    @retry_with_exponential_backoff(errors=(openai.RateLimitError,))
    def generate_response(self, request: LLMRequest) -> LLMResponse:
        try:
            messages = self._to_openai_messages(request.messages)

            # Responses API is where reasoning + usage live
            resp = self.client.responses.create(
                model=request.model or "gpt-5",
                input=messages,
                **(request.params or {}),
            )

            # Primary text
            text = getattr(resp, "output_text", "") or ""

            # Reasoning summary (if present)
            reasoning = ""
            output_items = getattr(resp, "output", []) or []
            for item in output_items:
                if getattr(item, "type", "") == "reasoning":
                    summary = getattr(item, "summary", []) or []
                    reasoning = "".join(getattr(ch, "text", str(ch)) for ch in summary)
                    break

            # Token counts
            usage = getattr(resp, "usage", None)
            input_tokens = int(_get_nested(usage, "input_tokens", default=0) or 0)
            output_tokens = int(_get_nested(usage, "output_tokens", default=0) or 0)
            reasoning_tokens = int(
                _get_nested(
                    usage, "output_tokens_details", "reasoning_tokens", default=0
                )
                or 0
            )
            cached_input_tokens = int(
                _get_nested(usage, "input_tokens_details", "cached_tokens", default=0)
                or 0
            )

            return LLMResponse(
                text=text,
                reasoning=reasoning,
                input_token_count=input_tokens,
                output_token_count=output_tokens,
                reasoning_token_count=reasoning_tokens,
                cached_input_token_count=cached_input_tokens,
            )
        except Exception as e:
            logger.error(f"Error performing OpenAI request: {e}")
            return LLMResponse(f"Error performing OpenAI request: {e}")

    @retry_with_exponential_backoff(errors=(openai.RateLimitError,))
    def generate_structured_response(self, request: LLMRequest) -> JSONLLMResponse:
        count = 0
        messages = self._to_openai_messages(request.messages)
        total_input_tokens = 0
        total_output_tokens = 0
        total_reasoning_tokens = 0
        total_cached_input_tokens = 0

        while True:
            resp = self.client.responses.create(
                model=request.model or "gpt-5",
                input=messages,
                **(request.params or {}),
            )

            # Text to parse as JSON
            text = getattr(resp, "output_text", "") or "{}"

            # Optional reasoning and counts (attached to the JSON response object)
            usage = getattr(resp, "usage", None)
            input_tokens = int(_get_nested(usage, "input_tokens", default=0) or 0)
            output_tokens = int(_get_nested(usage, "output_tokens", default=0) or 0)
            reasoning_tokens = int(
                _get_nested(
                    usage, "output_tokens_details", "reasoning_tokens", default=0
                )
                or 0
            )
            cached_input_tokens = int(
                _get_nested(usage, "input_tokens_details", "cached_tokens", default=0)
                or 0
            )

            reasoning = ""
            output_items = getattr(resp, "output", []) or []
            for item in output_items:
                if getattr(item, "type", "") == "reasoning":
                    summary = getattr(item, "summary", []) or []
                    reasoning = "".join(getattr(ch, "text", str(ch)) for ch in summary)
                    break

            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            total_reasoning_tokens += reasoning_tokens
            total_cached_input_tokens += cached_input_tokens

            try:
                return JSONLLMResponse(
                    text=text,
                    reasoning=reasoning,
                    input_token_count=total_input_tokens,
                    output_token_count=total_output_tokens,
                    reasoning_token_count=total_reasoning_tokens,
                    cached_input_token_count=total_cached_input_tokens,
                )
            except Exception as e:
                count += 1
                print(
                    f"Failed to parse JSON response from OpenAI (attempt {count}): {e}"
                )
                if count >= MAX_RETRIES_INVALID_JSON:
                    logger.error(f"Max retries reached for JSON parsing: {e}")
                    err = JSONLLMResponse(f'{{"error":"{str(e)}"}}')
                    return err
                logger.error(
                    f"Failed to parse JSON response from OpenAI (attempt {count}): {e}"
                )

    @retry_with_exponential_backoff(errors=(openai.RateLimitError,))
    def generate_response_using_schema(
        self, request: LLMRequest, schema: Dict[str, Any]
    ) -> JSONLLMResponse:
        count = 0
        llm_messages = request.messages

        llm_messages.append(
            LLMMessage(
                role="system",
                content="Return the requested information following the provided JSON schema.",
            )
        )

        messages = self._to_openai_messages(llm_messages)

        total_input_tokens = 0
        total_output_tokens = 0
        total_reasoning_tokens = 0
        total_cached_input_tokens = 0

        while True:
            resp = self.client.responses.create(
                model=request.model or "gpt-5.1",
                input=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_response",
                        "schema": schema,
                        "strict": True,
                    },
                },
                **(request.params or {}),
            )

            usage = getattr(resp, "usage", None)
            input_tokens = int(_get_nested(usage, "input_tokens", default=0) or 0)
            output_tokens = int(_get_nested(usage, "output_tokens", default=0) or 0)
            reasoning_tokens = int(
                _get_nested(
                    usage, "output_tokens_details", "reasoning_tokens", default=0
                )
                or 0
            )
            cached_input_tokens = int(
                _get_nested(usage, "input_tokens_details", "cached_tokens", default=0)
                or 0
            )

            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            total_reasoning_tokens += reasoning_tokens
            total_cached_input_tokens += cached_input_tokens

            # Extract optional reasoning text (if present in output)
            reasoning = ""
            output_items = getattr(resp, "output", []) or []
            for item in output_items:
                if getattr(item, "type", "") == "reasoning":
                    summary = getattr(item, "summary", []) or []
                    reasoning = "".join(getattr(ch, "text", str(ch)) for ch in summary)
                    break

            # Extract the **structured JSON** from the output
            try:
                # This part depends on SDK shape; for the Responses API the first
                # text/json output is usually something like:
                # resp.output[0].content[0].json
                if not output_items:
                    raise RuntimeError("No output items in response")

                first_item = output_items[0]
                contents = getattr(first_item, "content", []) or []
                if not contents:
                    raise RuntimeError("No content in first output item")

                json_obj = getattr(contents[0], "json", None)
                if json_obj is None:
                    raise RuntimeError("Expected JSON structured output, found none")

                # At this point json_obj is already a Python dict matching your schema
                text = json.dumps(json_obj)

                return JSONLLMResponse(
                    text=text,
                    reasoning=reasoning,
                    input_token_count=total_input_tokens,
                    output_token_count=total_output_tokens,
                    reasoning_token_count=total_reasoning_tokens,
                    cached_input_token_count=total_cached_input_tokens,
                )

            except Exception as e:
                count += 1
                print(
                    f"Failed to parse JSON response from OpenAI (attempt {count}): {e}"
                )
                if count >= MAX_RETRIES_INVALID_JSON:
                    logger.error(f"Max retries reached for JSON parsing: {e}")
                    err = JSONLLMResponse(f'{{"error":"{str(e)}"}}')
                    return err
                logger.error(
                    f"Failed to parse JSON response from OpenAI (attempt {count}): {e}"
                )
