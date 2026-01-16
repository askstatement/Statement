import requests
from bson import ObjectId
from typing import Optional
from user_agents import parse
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Request
from fastapi.security import OAuth2PasswordBearer

from core.config import JWT_SECRET_KEY, ALGORITHM, TOKEN_EXPIRES
from core.base_utils import BaseUtils
from modules.user.models import UserProjects

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class AuthUtils(BaseUtils):
    
    def hash_password(self, password: str):
        return pwd_context.hash(password)

    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    async def create_access_token(self, user: dict, request: Request, expires_delta: timedelta = None):
        # create session info
        session_id = await self.save_session_info(user, request)
        # payload with session id
        session_data = {"sub": str(user.get("_id")), "email": user.get("email"), "session_id": session_id}
        if user.get("is_admin", False):
            session_data["is_admin"] = True
        # create token
        to_encode = session_data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=TOKEN_EXPIRES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM), session_id

    async def authenticate_user(self, email: str, password: str):
        users_collection = self.mongodb.get_collection("users")
        user = await users_collection.find_one({"email": email, "$or": [{"archived": {"$exists": False}}, {"archived": False}]})
        hashed_password = user.get("hashed_password") if user else None
        if not user or not self.verify_password(password, hashed_password):
            return False
        return user

    def decode_token(self, token: str):
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
            return {"id": payload.get("sub"), "email": payload.get("email")}
        except JWTError:
            return None

    async def get_user_from_token_data(self, token_data: dict):
        # Example: fetch from DB using `sub` from token
        email = token_data.get("email")
        users_collection = self.mongodb.get_collection("users")
        user = await users_collection.find_one({"email": email, "$or": [{"archived": {"$exists": False}}, {"archived": False}]})
        return user

    async def is_valid_session(self, session_id: str) -> bool:
        """Check if the session is valid and active"""
        if not session_id:
            return False
        sessions_collection = self.mongodb.get_collection("sessions")
        session = await sessions_collection.find_one({"_id": ObjectId(session_id), "is_active": True})
        return session is not None
    
    async def save_session_info(self, user: dict, request: Request):
        """Save session information when user logs in"""
        
        # Get IP address
        ip = request.client.host
        
        # Get location info using ip-api
        try:
            ip_info = requests.get(f'http://ip-api.com/json/{ip}').json()
            city = ip_info.get('city', '')
            country = ip_info.get('country', '')
            location = f"{city}, {country}" if city or country else "Unknown"
        except:
            location = "Unknown"

        # Parse user agent
        user_agent = parse(request.headers.get("user-agent", ""))
        device = f"{user_agent.os.family}"
        browser = f"{user_agent.browser.family}"
        
        # Create session document
        session = {
            "user_email": user.get("email"),
            "user_id": user.get("_id"),
            "ip_address": ip,
            "device": device,
            "browser": browser,
            "location": location,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "is_active": True
        }

        # Save session
        sessions_collection = self.mongodb.get_collection("sessions")
        session_resp = await sessions_collection.insert_one(session)
        session_id = str(session_resp.inserted_id)

        # Log login activity
        activity = {
            "user_email": user.get("email"),
            "session_id": session_id,
            "user_id": user.get("_id"),
            "login_time": datetime.utcnow(),
            "browser": browser,
            "location": location,
            "success": True
        }
        login_activity_collection = self.mongodb.get_collection("login_activity")
        await login_activity_collection.insert_one(activity)
        return session_id

    async def create_user_default_project(self, user_id: str) -> Optional[str]:
        user_collection = self.mongodb.get_collection("users")
        user = await user_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None
        # get the plan slug from user
        subscription = user.get("subscription", {})
        plan_slug = subscription.get("plan_slug", "free")
        # get plan details
        plans_collection = self.mongodb.get_collection("plans")
        plan = await plans_collection.find_one({"slug": plan_slug})
        # create default project allowed credit
        credits_allowed = plan.get("monthly_credits_per_project", 0) if plan else 0
        project = UserProjects(
            name="Default Project", 
            archived=False, 
            user_id=str(user_id),
            credits_allowed=credits_allowed
        )
        project_doc = project.dict()
        project_doc["user_id"] = str(user_id)
        projects_collection = self.mongodb.get_collection("projects")
        new_project = await projects_collection.insert_one(project_doc)
        return new_project