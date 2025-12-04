from bson import ObjectId
from fastapi import HTTPException
from fastapi import HTTPException, Query, Request
from core.base_api import BaseAPI, get
from core.registry import ServiceRegistry
from core.decorators import auth_required
from .utils import ChatUtils
from core.logger import Logger
from agents.agent_router import AgentRouter

logger = Logger(__name__)

agent_router = AgentRouter()

class ChatAPI(BaseAPI):
    utils: ChatUtils

    @get("/agents")
    @auth_required
    async def get_agents_available(self, request: Request, projectId: str = Query(...)):
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.find_one({"_id": ObjectId(projectId)})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        available_agents = await agent_router.get_available_agents_by_project_scope(projectId)
        return {"available_agents": available_agents}
        

# Register globally
ServiceRegistry.register_api("web_chat", ChatAPI("/web_chat").router)
