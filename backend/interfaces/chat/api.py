from uuid import uuid4
from fastapi import Request, HTTPException, status
from pydantic import ValidationError
from core.registry import ServiceRegistry
from core.base_interface import BaseInterface
from core.base_api import post
from core.decorators import api_key_required, rate_limit, token_limit
from .models import ChatCompletionRequest, ChatCompletionResponse, PromptData
from .utils import ChatUtils
from agents.agent_router import AgentRouter
from llm.providers.openai.openai_provider import OpenAIProvider
from core.logger import Logger

logger = Logger(__name__)

class ChatInterface(BaseInterface):
    utils: ChatUtils

    @post("/completions")
    @api_key_required
    @rate_limit("5/m")
    @token_limit("1000/tpm") # limit token and measure credit usage
    async def create_chat_completion(self, request: Request, data: ChatCompletionRequest):
        """
        Public API for generating chat completions.
        Mirrors OpenAI's /v1/chat/completions structure.

        Request body:
        {
            "model": "",
            "messages": [{"role": "user", "content": "What is my MRR?"}],
            "response_schema": {...}  # optional JSON schema
        }
        """
        logger.info(f"Received chat completion request for model {data.model}")

        # Validate message format
        try:
            if not data.messages or not isinstance(data.messages, list):
                raise ValueError("messages must be a non-empty list of {role, content} objects")

            for msg in data.messages:
                if msg.role not in ["user", "assistant"]:
                    raise ValueError(f"Invalid message role '{msg.role}'")
                if not msg.content or not isinstance(msg.content, str):
                    raise ValueError("Each message must have non-empty string 'content'")
        except (ValueError, ValidationError) as e:
            logger.error(f"Message validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid messages: {e}"
            )

        # Validate optional JSON schema (if provided)
        if data.response_schema:
            try:
                schema_dict = data.response_schema.dict(exclude_none=True)
                if "type" not in schema_dict:
                    raise ValueError("response_schema must contain a 'type' field")
                # Optional: validate that `properties` matches its type
                if schema_dict["type"] == "object" and not schema_dict.get("properties"):
                    raise ValueError("Object schema must define 'properties'")
                self.utils.validate_response_schema(data.response_schema)
            except Exception as e:
                logger.error(f"Schema validation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid response_schema: {str(e)}"
                )

        try:
            # Find user
            user = request.state.user
            project_id = await self.utils.get_last_project_for_user(user_id=user.get("_id"))
            if request.state.project:
                project_id = str(request.state.project.get("_id"))
                 
            # get user message from messages
            last_user_message = data.messages[-1] or {}
            last_user_message = last_user_message.dict() if hasattr(last_user_message, "dict") else last_user_message
            user_query = last_user_message.get("content", "")
            message_history = data.messages[:-1] if len(data.messages) > 1 else []
                
            # new agent router with provider
            agent_router = AgentRouter(provider=OpenAIProvider)
            router_response = await agent_router.handle_request(
                query=user_query,
                project_id=project_id,
                agent_scope=[],
                messages=message_history, 
                conversation_id=None
            )
            token_usage = router_response.get("token_usage", {})
            response = router_response.get("response_text", "")
            agent_responses = router_response.get("agent_responses", {})
                
            # Save response
            response_data = PromptData(
                user_id=str(user.get("_id")),
                conversation_id="",
                model="",
                session_id="",
                project_id=project_id,
                type='response',
                content=response,
                agent_responses=agent_responses,
                followup="",
                steps=[],
                messages=[],
                token_usage=token_usage,
                graph_data={}
            )
            await self.utils.save_prompt(response_data)

            return ChatCompletionResponse(
                id=str(uuid4()),
                object="chat.completion",
                model=data.model or "default",
                created=int(request.scope.get("time", 0)) or 0,
                choices=[
                    {"message": {"role": "assistant", "content": response}}
                ]
            ).dict()

        except Exception as e:
            logger.error(f"Chat completion failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal chat engine error")

# Register globally
ServiceRegistry.register_api("chat", ChatInterface("/chat", "v1").router)