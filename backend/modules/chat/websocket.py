import asyncio
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

    def __init__(self):
        super().__init__()
        self.utils = ChatUtils()

    @register_route("/sync-progress")
    @ws_auth_required
    async def ws_sync_progress(self, websocket: WebSocket):
        """
        Endpoint for clients to monitor the progress of ongoing data synchronization tasks.
        """
        try:
            await websocket.accept()
            params = websocket.query_params
            project_id: Optional[str] = params.get("project_id")
            
            logger.info(f"Progress WebSocket connected for project: {project_id}")
            
            if not project_id:
                await websocket.send_json(
                    {"status": "error", "message": "project_id is required."}
                )
                await websocket.close()
                return
            
            consecutive_empty_polls = 0
            max_empty_polls = 5
            has_sent_data = False
            poll_count = 0
            
            while True:
                poll_count += 1
                logger.info(f"[Poll {poll_count}] Checking progress for project: {project_id}")
                
                active_syncs = await self.utils.get_all_sync_progress(project_id)
                logger.info(f"[Poll {poll_count}] Found {len(active_syncs)} active syncs")
                
                if not active_syncs:
                    consecutive_empty_polls += 1
                    logger.info(f"[Poll {poll_count}] No syncs found. Consecutive empty: {consecutive_empty_polls}/{max_empty_polls}")
                    
                    if (has_sent_data and consecutive_empty_polls >= 3) or consecutive_empty_polls >= max_empty_polls:
                        logger.info(f"Closing progress WebSocket for project {project_id}")
                        await websocket.close()
                        return
                else:
                    consecutive_empty_polls = 0
                    has_sent_data = True
                    
                    for progress in active_syncs:
                        sanitized_progress = self.utils.sanitize_mongo_doc(
                            progress
                        )
                        logger.info(f"[Poll {poll_count}] Sending progress: {sanitized_progress}")
                        await websocket.send_json(sanitized_progress)
                        
                        if sanitized_progress.get("status") in ["done", "error"]:
                            logger.info(f"[Poll {poll_count}] Clearing completed/errored progress for service: {sanitized_progress.get('service')}")
                            await self.utils.clear_sync_progress(
                                project_id, sanitized_progress.get("service")
                            )
                
                await asyncio.sleep(2)
                
        except WebSocketDisconnect:
            logger.info(f"Client disconnected from progress socket for project: {project_id}")
        except Exception as e:
            logger.error(f"Error in progress websocket for project {project_id}: {e}", exc_info=True)

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
                question_prompt_id = await self.utils.save_prompt(prompt_data)
                
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
                    conversation_id=convId,
                    prompt_id=str(question_prompt_id)
                )
                response = router_response.get("response_text", "")
                agent_responses = router_response.get("agent_responses", [])
                                
                # save each agent response with pipeline id to db
                ws_agent_responses = []
                for response in agent_responses:
                    # Save response
                    finaliser_response = response.get("finaliser_response", {})
                    planner_response = response.get("planner_response", "")
                    token_usage = response.get("token_usage", {})
                    prompt_data = PromptData(
                        user_id=str(user.get("_id")),
                        conversation_id=convId,
                        model="gpt-5",
                        session_id=session_id,
                        project_id=project_id,
                        prompt_id=str(question_prompt_id),
                        pipeline_id=response.get("pipeline_id", None),
                        type='response',
                        planner_response=planner_response,
                        finaliser_response=finaliser_response,
                        content=finaliser_response.get("final_answer", ""),
                        agent=response.get("agent", "unknown"),
                        followup=response.get("follow_up", ""),
                        steps=jsonable_encoder(response.get("steps", [])),
                        messages=jsonable_encoder(response.get("messages", [])),
                        token_usage=token_usage,
                        graph_data=finaliser_response.get("graph_data", {}),
                        is_bookmarkable=finaliser_response.get("is_bookmarkable", False),
                    )
                    resp_mode_dump = prompt_data.model_dump()
                    resp_prompt_id = await self.utils.save_prompt(prompt_data)
                    resp_mode_dump["prompt_id"] = str(resp_prompt_id)
                    ws_agent_responses.append(resp_mode_dump)

                try:
                    await websocket.send_json({"agent_responses": self.utils.sanitize_mongo_doc(ws_agent_responses)})
                    await websocket.send_text("__END__")
                except RuntimeError:
                    logger.error(f"Cannot send, WebSocket closed: {session_id}")
                    break
                
                # Generate title and summary for the conversation
                await self.utils.generate_title_and_summary(convId)

        except Exception as e:
            logger.error(f"Unexpected error for session {session_id}: {e}")

        finally:
            logger.info(f"WebSocket closed for session ID: {session_id}")

# Register it globally
ServiceRegistry.register_websocket("web_chat", ChatWebSocket())
