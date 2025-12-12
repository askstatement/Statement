from uuid import uuid4
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from core.decorators import ws_auth_required, AuthMode
from core.base_websocket import BaseWebSocketHandler, register_route
from core.registry import ServiceRegistry
from agents.agent_router import AgentRouter
from llm.providers.openai.openai_provider import OpenAIProvider
from .utils import ChatUtils
from .models import PromptData
from core.logger import Logger

logger = Logger(__name__)

class ChatWebSocket(BaseWebSocketHandler):
    utils: ChatUtils
    
    @register_route("/")
    @ws_auth_required(mode=AuthMode.PROJECT)
    async def ws_chat_with_llm(self, websocket: WebSocket):
        # TODO: to implement rate limiting and token limiting for websockets
        params = websocket.query_params
        projectId: Optional[str] = params.get("projectId")
        convId: Optional[str] = params.get("convId")
        
        user = websocket.state.user
        if not user:
            await websocket.accept()
            await websocket.close(code=1008)
            return
    
        if not convId:
            await websocket.accept()
            await websocket.close(code=1006)
            return
        
        if not projectId:
            projectId = await self.utils.get_project_from_convo(convId)
            if not projectId:
                await websocket.accept()
                await websocket.close(code=1006)
                return

        await websocket.accept()
        session_id = str(uuid4())
        logger.info(f"WebSocket opened with session ID: {session_id}")

        steps, messages = [], []
        try:
            while True:
                try:
                    message = await websocket.receive_text()
                except WebSocketDisconnect:
                    logger.info(f"Client disconnected: {session_id}")
                    break
                except Exception as e:
                    logger.error(f"Error receiving message from {session_id}: {e}")
                    break

                if not message:
                    try:
                        await websocket.send_text("__END__")
                    except RuntimeError:
                        break
                    continue

                project_id = await self.utils.get_project_from_convo(convId)
                
                # parse the json message to get agentsSelected and message string
                msg_obj  = await self.utils.parse_ws_message(message)
                agents_selected = msg_obj.get("agents_selected", [])
                message = msg_obj.get("message", "")

                # Save prompt
                prompt_data = PromptData(
                    user_id=str(user.get("_id")),
                    conversation_id=convId,
                    model="gpt-5",
                    session_id=session_id,
                    project_id=project_id,
                    type='prompt',
                    content=message
                )
                await self.utils.save_prompt(prompt_data)
                
                # validate token limit for protecting websocket usage
                # TODO: make the limit configurable per project and per user plan
                has_quota = await self.utils.check_ws_token_limit(project_id, "100000/tpm", websocket)
                if not has_quota:
                    error_msg = "Token quota exceeded for the project."
                    logger.warning(f"Quota exceeded for project {project_id} in session {session_id}")
                    try:
                        await websocket.send_json({"error": error_msg, "error_code": 429})
                        await websocket.send_text("__END__")
                    except RuntimeError:
                        logger.error(f"Cannot send, WebSocket closed: {session_id}")
                    break
                    
                # new agent router with provider
                agent_router = AgentRouter(provider=OpenAIProvider)
                router_response = await agent_router.handle_request(
                    query=message,
                    project_id=project_id,
                    agent_scope=agents_selected if agents_selected else [],
                    messages=[], 
                    conversation_id=convId
                )
                token_usage = router_response.get("token_usage", {})
                response = router_response.get("response_text", "")
                agent_responses = router_response.get("agent_responses", {})
                
                followup = ""
                steps = []
                messages = []
                graph_data = {}
                serializable_steps = jsonable_encoder(steps)

                response_data = {
                    "agent_responses": agent_responses
                }

                try:
                    await websocket.send_json(response_data)
                    await websocket.send_text("__END__")
                except RuntimeError:
                    logger.error(f"Cannot send, WebSocket closed: {session_id}")
                    break

                # Save response
                resp_data = PromptData(
                    user_id=str(user.get("_id")),
                    conversation_id=convId,
                    model="gpt-5",
                    session_id=session_id,
                    project_id=project_id,
                    type='response',
                    content=response,
                    agent_responses=agent_responses,
                    followup=followup,
                    steps=serializable_steps,
                    messages=messages,
                    token_usage=token_usage,
                    graph_data=graph_data
                )
                await self.utils.save_prompt(resp_data)
                await self.utils.generate_title_and_summary(convId)

        except Exception as e:
            logger.error(f"Unexpected error for session {session_id}: {e}")

        finally:
            logger.info(f"WebSocket closed for session ID: {session_id}")

# Register it globally
ServiceRegistry.register_websocket("web_chat", ChatWebSocket())
