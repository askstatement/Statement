from typing import Optional
from bson import ObjectId
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

from core.base_utils import BaseUtils

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class SettingsUtils(BaseUtils):
    
    def hash_password(self, password: str):
        return pwd_context.hash(password)
    
    async def authenticate_user(self, email: str, password: str):
        users_collection = self.mongodb.get_collection("users")
        user = await users_collection.find_one({"email": email, "$or": [{"archived": {"$exists": False}}, {"archived": False}]})
        if not user or not self.verify_password(password, user["hashed_password"]):
            return False
        return user
    
    async def get_user_sessions(self, email: str):
        """Get all active sessions for a user"""
        sessions_collection = self.mongodb.get_collection("sessions")
        cursor = sessions_collection.find({
            "user_email": email,
            "is_active": True
        }).sort("last_active", -1).limit(5)
        
        sessions = []
        async for session in cursor:
            sessions.append({
                "id": session["session_id"],
                "device": session["device"],
                "location": session["location"],
                "isCurrent": True,
                "lastActive": session["last_active"].isoformat() + "Z"
            })
        return sessions
    
    async def get_recent_login_activity(self, email: str):
        """Get recent login activity for a user"""
        login_activity_collection = self.mongodb.get_collection("login_activity")
        cursor = login_activity_collection.find({
            "user_email": email
        }).sort("login_time", -1).limit(5)
        
        activities = []
        async for activity in cursor:
            activities.append({
                "loginTime": activity["login_time"].isoformat() + "Z",
                "browser": activity["browser"],
                "location": activity["location"],
                "success": activity["success"]
            })
        return activities
    
    async def get_project_from_id(self, project_id: str) -> Optional[dict]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        return project
