from bson import ObjectId
from typing import Optional
from datetime import datetime
from fastapi import HTTPException
from fastapi import HTTPException, Request, Query
from core.base_api import BaseAPI, get, post, delete
from core.registry import ServiceRegistry
from core.decorators import auth_required
from fastapi import Request
from .models import ProjectCreateRequest, UserConversation, PromptData
from modules.user.models import UserProjects
from .utils import UserUtils
from core.logger import Logger

logger = Logger(__name__)


class UserAPI(BaseAPI):
    utils: UserUtils

    @post("/projects")
    @auth_required
    async def create_project(self, request: Request, payload: ProjectCreateRequest):
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        project = UserProjects(name=payload.name, archived=False, user_id=str(user.get("_id")))
        doc = project.dict()
        doc["user_id"] = str(user.get("_id"))

        projects_collection = self.mongodb.get_collection("projects")
        result = await projects_collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return {"message": "Project created", "data": doc}
    
    @get("/projects")
    @auth_required
    async def list_projects(self, request: Request):
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        projects_collection = self.mongodb.get_collection("projects")
        cursor = projects_collection.find({"user_id": str(user.get("_id")), "archived": False}).sort("created_at", -1)
        projects = []
        async for doc in cursor:
            all_convos = await self.list_project_conversation(request, projectId=str(doc["_id"]))
            doc["_id"] = str(doc["_id"])
            doc["chats"] = list(all_convos.get("conversations", []) if all_convos else [])
            projects.append(doc)
        return {"projects": projects}
    
    @get("/project/api_key")
    @auth_required
    async def get_project_api_keys(self, request: Request, projectId: str = Query(...)):
        user = request.state.user
        keys_collection = self.mongodb.get_collection("api_keys")
        api_keys = await keys_collection.find({"project_id": projectId, "user_id": str(user.get("_id"))}).to_list(length=None)
        return {"message": "SUCCESS", "keys": self.utils.sanitize_mongo_doc(api_keys)}
    
    @post("/project/api_key")
    @auth_required
    async def create_project_api_key(self, request: Request):
        body = await request.json()
        projectId: str = body.get("projectId")
        name = body.get("name", "Default Key")
        user = request.state.user
        project_collection = self.mongodb.get_collection("projects")
        # Verify project ownership
        project = await project_collection.find_one({"_id": ObjectId(projectId), "user_id": str(user.get("_id"))})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized")

        key_document = await self.utils.generate_project_api_key(projectId, str(user.get("_id")), name)
        return {"message": "API key generated", "new_key": self.utils.sanitize_mongo_doc(key_document)}
    
    @delete("/project/api_key")
    @auth_required
    async def remove_project_api_key(self, request: Request, projectId: str = Query(...), apiKeyId: str = Query(...)):
        user = request.state.user
        projects_collection = self.mongodb.get_collection("projects")
        keys_collection = self.mongodb.get_collection("api_keys")
        # Verify project ownership
        project = await projects_collection.find_one({"_id": ObjectId(projectId), "user_id": str(user.get("_id"))})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized")
        result = await keys_collection.update_one({"_id": ObjectId(apiKeyId), "project_id": projectId}, {"$set": {"archived": True}})
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="API key not found or unauthorized")
        return {"message": "API key deleted successfully"}
    
    @post("/conversation")
    @auth_required
    async def create_conversation(self, request: Request, data: UserConversation):
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        insight_id = data.insight_id
        reason = data.reason
        project_id = data.project_id
        if not project_id:
            project_id = await self.utils.get_last_project_for_user(str(user.get("_id")))
            if not project_id:
                raise ValueError("No project_id provided and no existing project found for user.")

        if insight_id:
            insight = await self.utils.get_insight(insight_id)
            if not insight:
                raise HTTPException(status_code=404, detail="Insight not found")
            data.summary = insight.get("description")
            data.name = insight.get("title")
        convo = UserConversation(
            name=data.name,
            user_id=str(user.get("_id")),
            project_id=project_id,
            insight_id=insight_id,
            summary=data.summary or "",
        )
        conversations_collection = self.mongodb.get_collection("conversations")
        result = await conversations_collection.insert_one(convo.dict())
        if insight_id:
            await self.utils.save_prompt(PromptData(
                user_id=str(user.get("_id")),
                conversation_id=str(result.inserted_id),
                model="",
                session_id="",
                project_id=project_id,
                type='response',
                content=insight.get("explanation", "") if reason == "details" else insight.get("description", "")
            ))
        convo_dict = convo.dict()
        convo_dict["_id"] = str(result.inserted_id)
        logger.info(f"Conversation created with ID: {result.inserted_id}")
        return {"conversation": convo_dict}
    
    @delete("/conversation")
    @auth_required
    async def delete_conversation(self, request: Request, convId: str = Query(10)):
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        deleted = await self. utils.get_delete_convo(convId)
        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"message": "Conversation deleted successfully"}
    
    @get("/project-conversations")
    @auth_required
    async def list_project_conversation(self, request: Request, projectId: str = Query(...)):
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if not projectId:
            raise HTTPException(status_code=400, detail="Project ID is required")

        convos = await self.utils.get_all_convo_from_project(projectId)
        return {"conversations": convos}
    
    @get("/history")
    @auth_required
    async def list_chat_history(self, request: Request, convoId: str = Query(...)):
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        history = await self.utils.get_chat_history(convoId)
        return {"history": history}
    
    @get("/record_reactions")
    @auth_required
    async def record_user_reactions(self, request: Request, promptId: str = Query(...), reaction: str = Query(...)):
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        is_updated = await self.utils.update_user_reactions(promptId, reaction)
        return {"success": is_updated}
    
    @get("/insights")
    @auth_required
    async def get_cfo_insights(
        self,
        request: Request, 
        projectId: str = Query(...), 
        recreate: Optional[str] = Query(None)
    ):
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        insights = await self.utils.get_insights_for_project(projectId, recreate=recreate=="true")
        return {"insights": insights}
    
    @get("/conversations/search")
    @auth_required
    async def search_conversations(
        self,
        request: Request,
        q: str | None = Query(None, description="Search text (optional)"),
        pid: str = Query(..., description="Project ID")
    ):
        """
        Search conversations by name and summary within a given project.
        If no search query is provided, return the latest 4 conversations.
        """
        try:
            # Verify user is authenticated
            user = request.state.user
            if not user:
                raise HTTPException(status_code=401, detail="Unauthorized")

            # Verify project exists and belongs to user
            projects_collection = self.mongodb.get_collection("projects")
            conversations_collection = self.mongodb.get_collection("conversations")
            project = await projects_collection.find_one({
                "_id": ObjectId(pid),
                "user_id": str(user.get("_id"))
            })
            if not project:
                raise HTTPException(status_code=404, detail="Project not found or unauthorized")

            # Base query
            query = {"project_id": pid, "archived": False}

            # If search text is provided, add regex search condition
            if q:
                query["$or"] = [
                    {"name": {"$regex": q, "$options": "i"}},
                    {"summary": {"$regex": q, "$options": "i"}},
                ]

            # Limit results: 4 if no query, else 20
            limit = 4 if not q else 20

            cursor = conversations_collection.find(
                query, {"project_id": 1, "name": 1, "summary": 1, "updated_at": 1}
            ).sort("updated_at", -1).limit(limit)

            results = await cursor.to_list(length=limit)

            # Convert ObjectIds and dates
            for r in results:
                if isinstance(r.get("_id"), ObjectId):
                    r["_id"] = str(r["_id"])
                if isinstance(r.get("updated_at"), datetime):
                    r["updated_at"] = r["updated_at"].isoformat()

            return {"results": results}

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error searching conversations: {str(e)}"
            )
            
    @post("/delete_profile")
    @auth_required
    async def delete_profile(self, request: Request):
        """
        Delete user profile and all associated data.
        """
        try:
            # Verify user is authenticated
            user = request.state.user
            if not user:
                raise HTTPException(status_code=401, detail="Unauthorized")

            # delete user
            projects = await self.utils.get_all_project_for_user(str(user.get("_id")))
            for project in projects:
                # Delete all conversations for the project
                await self.utils.archive_convos_for_project(str(project.get("_id")))
                # Delete all insights for the project
                await self.utils.delete_insights_by_project(str(project.get("_id")))
                # Archive the project itself
                await self.utils.get_delete_project(str(project.get("_id")))
            
            users_collection = self.mongodb.get_collection("users")
            user = await users_collection.update_one({"_id": ObjectId(user.get("_id"))}, {"$set": {"archived": True}})
            if user.modified_count == 0:
                raise HTTPException(status_code=500, detail="User not found or already deleted")
            return {"status": 200, "message": "User profile and associated data deleted successfully."}

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error deleting profile: {str(e)}"
            )
            
    @get("/bookmark_prompt")
    @auth_required
    async def record_user_bookmark_prompt(self, request: Request, promptId: str = Query(...), status: str = Query(...)):
        status = status.lower() == "true"
        is_bookmarked = await self.utils.bookmark_prompt(promptId, status)
        return {status: 200, "message": "Prompt bookmark status updated", "is_bookmarked": is_bookmarked}

# Register globally
ServiceRegistry.register_api("user", UserAPI("/user").router)
