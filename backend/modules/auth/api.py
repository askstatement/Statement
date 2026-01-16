import os
import json
import httpx
import secrets
import hashlib
import pyotp
from jose import jwt
from bson import ObjectId
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests
from core.base_api import BaseAPI, get, post
from core.registry import ServiceRegistry
from core.decorators import auth_required
from fastapi import HTTPException, Request, Query
from fastapi.responses import JSONResponse

from .utils import AuthUtils
from modules.user.models import UserModel
from .models import (
    UserSignup, UserLogin, TokenResponse, GoogleAuthRequest, MSAuthRequest
)
from core.emails.service import send_welcome_email, send_verification_email, send_password_reset_email

HOST_URL = os.getenv("HOST_URL", "localhost:3000")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID", "")

class AuthAPI(BaseAPI):
    utils: AuthUtils
    
    @post("/signup")
    async def signup(self, user: UserSignup):
        hashed = self.utils.hash_password(user.password)
        users_collection = self.mongodb.get_collection("users")
        existing_user = await users_collection.find_one({"email": user.email})
        new_user = None
        new_user_id = None
        email = user.email.lower()
        email_token = str(ObjectId())
        token_expiry = datetime.utcnow() + timedelta(hours=24)
        if existing_user and existing_user.get("archived", False) is False:
            # existing active user
            raise HTTPException(status_code=400, detail="Email already registered")
        elif existing_user and existing_user.get("archived", False) is True:
            # reset password flow and unrchive user
            new_user = await users_collection.update_one(
                {"_id": ObjectId(existing_user["_id"])},
                {"$set": {
                    "hashed_password": hashed,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "archived": False,
                    "email_token": email_token,
                    "email_token_expiry": token_expiry,
                    "is_email_verified": False,
                }}
            )
            new_user_id = existing_user["_id"]
        else:
            # new user creation
            user_obj = UserModel(
                email=email,
                hashed_password=hashed,
                firstname=user.firstname,
                lastname=user.lastname,
                email_token=email_token,
                email_token_expiry=token_expiry,
                is_email_verified=False
            )
            new_user = await users_collection.insert_one(user_obj.dict())
            new_user_id = new_user.inserted_id
        if not new_user:
            raise HTTPException(status_code=500, detail="Error creating user")
        # create default project
        new_project_id = await self.utils.create_user_default_project(str(new_user_id))
        send_verification_email(
            email,
            user.firstname,
            f"{HOST_URL}/verify-email?email={email}&token={email_token}",
        )
        return {"msg": "User registered successfully", "project_id": str(new_project_id.inserted_id)}
    
    @get("/verify-email")
    async def verify_email(self, email: str = Query(None), token: str = Query(None)):
        users_collection = self.mongodb.get_collection("users")
        user = await users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.get("is_email_verified"):
            return {"msg": "Email already verified"}
        if user.get("email_token") != token or user.get("email_token_expiry") < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid verification token")
        await users_collection.update_one(
            {"email": email},
            {"$set": {"is_email_verified": True}, "$unset": {"email_token": "", "email_token_expiry": ""}},
        )
        send_welcome_email(user)
        return {"msg": "Email verified successfully"}
    
    @post("/forgot-password")
    async def forgot_password(self, request: dict):
        email = request.get("email", "").lower()

        # Always return success to prevent email enumeration
        msg = "If the email exists, a password reset link has been sent to your email address.Please check your inbox"
        users_collection = self.mongodb.get_collection("users")
        existing_user = await users_collection.find_one({"email": email})
        if not existing_user:
            return {"msg": msg}

        # Generate secure token
        reset_token = secrets.token_urlsafe(64)
        token_expiry = datetime.utcnow() + timedelta(hours=1)

        # Hash token before storing (like passwords)
        hashed_token = hashlib.sha256(reset_token.encode()).hexdigest()

        # Store in database
        await users_collection.update_one(
            {"email": email},
            {"$set": {"passwordResetToken": hashed_token, "pwdTokenExpiry": token_expiry}},
        )

        # Send email with reset link
        reset_link = f"http://localhost:3000/reset-password?token={reset_token}&email={email}"
        send_password_reset_email(email, existing_user.get("firstname"), reset_link)

        return {"msg": msg}
    
    @post("/reset-password")
    @auth_required
    async def reset_password(self, request: dict):
        email = request.get("email", "").lower()
        token = request.get("token")
        new_password = request.get("new_password")
        confirm_password = request.get("confirm_password")
        
        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        
        # Find user and validate token
        users_collection = self.mongodb.get_collection("users")
        user = await users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        
        if (user.get("passwordResetToken") != hashed_token or user.get("pwdTokenExpiry") < datetime.utcnow()):
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
        # Update password and clear reset token
        hashed_password = self.utils.hash_password(new_password)
        await users_collection.update_one(
            {"email": email},
            {"$set": {"hashed_password": hashed_password},
            "$unset": {"passwordResetToken": "", "pwdTokenExpiry": ""}}
        )
        
        return {"msg": "Password reset successful"}   
    
    @post("/login", response_model=TokenResponse)
    async def login(self, credentials: UserLogin, request: Request):
        user = await self.utils.authenticate_user(credentials.email, credentials.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if user.get("two_factor_enabled", False):
            return {"two_factor_enabled": True}
        
        token, session_id = await self.utils.create_access_token(user=user, request=request)
        return {"access_token": token, "session_id": session_id}
    
    @post("/2fa_login")
    async def login_2fa(self, credentials: UserLogin, request: Request):
        token = credentials.token    

        if not credentials.email or not credentials.password or not credentials.token:
            raise HTTPException(status_code=400, detail="Email, password, and token are required")
        
        user = await self.utils.authenticate_user(credentials.email, credentials.password)

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        secret = user.get("two_factor_secret")
        totp = pyotp.TOTP(secret)
        if not totp.verify(token, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid 2FA token")
        else:
            token, session_id = await self.utils.create_access_token(user=user, request=request)
            return {"access_token": token, "session_id": session_id}
    
    @get("/session")
    @auth_required
    async def read_users_me(self, request: Request):
        sid = request.query_params.get("sid")  # get session id from query
        if not request.state.user or not await self.utils.is_valid_session(sid):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return {"user": self.utils.sanitize_mongo_doc(request.state.user)}

    @post("/logout-session")
    @auth_required
    async def logout_session(self, request: Request, data: dict):
        async def invalidate_session(session_id: str):
            """Invalidate a session by setting is_active to False"""
            sessions_collection = self.mongodb.get_collection("sessions")
            await sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"is_active": False}}
            )
            login_activity_collection = self.mongodb.get_collection("login_activities")
            await login_activity_collection.update_many(
                {"session_id": session_id},
                {"$set": {"success": False}}
            )
            return {"message": "Session invalidated"}
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        session_id = data.get("sessionId")
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # session logout logic
        await invalidate_session(session_id) 
        
        return {"message": "Session logged out successfully"}
    
    @post("/google")
    async def auth_google(self, request: Request, payload: GoogleAuthRequest):
        try:
            # Verify token with Google
            idinfo = id_token.verify_oauth2_token(
                payload.id_token, requests.Request(), GOOGLE_CLIENT_ID
            )

            # Extract user info
            email = idinfo["email"]
            name = idinfo.get("name")
            is_signup = payload.is_signup or False
            
            users_collection = self.mongodb.get_collection("users")
            user = await users_collection.find_one({"email": email})
            
            is_deleted = user.get("archived", False) if user else False
            
            new_project_id = None
            
            if not user:
                # Create new user if not exists
                user_obj = UserModel(
                    email=email,
                    firstname=name,
                    lastname="",
                    hashed_password="",
                    is_email_verified=True
                )
                result = await users_collection.insert_one(user_obj.dict())
                user = await users_collection.find_one({"_id": result.inserted_id})
                # create default project for user
                new_project_id = await self.utils.create_user_default_project(str(result.inserted_id))
                # send welcome email
                send_welcome_email(user)
            
            if user and is_deleted and not is_signup:
                raise HTTPException(status_code=403, detail="Can't find any account with this email. Please sign up first.")
            
            elif user and is_deleted and is_signup:
                user_updated = await users_collection.update_one(
                    {"email": email},
                    {"$set": {"archived": False, "name": name}}
                )
                if user_updated.modified_count == 0:
                    raise HTTPException(status_code=500, detail="Failed to restore archived user")
                user = await users_collection.find_one({"email": email})
                # create default project for user
                new_project_id = await self.utils.create_user_default_project(str(user.get("_id")))
                # send welcome email
                send_welcome_email(user)
            
            token, session_id = await self.utils.create_access_token(user=user, request=request)

            return {"access_token": token, "user": {"email": email, "name": name}, "session_id": session_id, "project_id": str(new_project_id)}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid token")
        
    @post("/microsoft")
    async def auth_microsoft(self, request: Request, payload: MSAuthRequest):
        try:
            id_token = payload.id_token
            # Decode without verification to get tenant id
            decoded = jwt.get_unverified_claims(id_token)
            tenant_id = decoded["tid"]

            jwks_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
            async with httpx.AsyncClient() as client:
                jwks_resp = await client.get(jwks_url)
                jwks_resp.raise_for_status()
                jwks = jwks_resp.json()

            kid = jwt.get_unverified_header(id_token)["kid"]
            public_key = None

            for key in jwks["keys"]:
                if key["kid"] == kid:
                    public_key = json.dumps(key)
                    break

            if public_key is None:
                raise HTTPException(status_code=401, detail="Public key not found in JWKS")

            # Validate token signature and claims
            decoded = jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256"],
                audience=MS_CLIENT_ID,
            )

            name = decoded.get("name") or decoded.get("preferred_username")
            email = decoded.get("email") or decoded.get("preferred_username")
            is_signup = payload.is_signup

            # Query user from database (example)
            users_collection = self.mongodb.get_collection("users")
            user = await users_collection.find_one({"email": email})
            is_deleted = user.get("archived", False) if user else False
            new_project_id = None

            if not user:
                # Create new user if not exists
                user_obj = UserModel(
                    email=email,
                    firstname=name,
                    lastname="",
                    hashed_password="",
                    is_email_verified=True
                )
                result = await users_collection.insert_one(user_obj.dict())
                user = await users_collection.find_one({"_id": result.inserted_id})
                # create default project for user
                new_project_id = await self.utils.create_user_default_project(str(user.get("_id")))
                # send welcome email
                send_welcome_email(user)

            if user and is_deleted and not is_signup:
                raise HTTPException(
                    status_code=403,
                    detail="Can't find any account with this email. Please sign up first.",
                )
            elif user and is_deleted and is_signup:
                user_updated = await users_collection.update_one(
                    {"email": email}, {"$set": {"archived": False, "name": name}}
                )
                if user_updated.modified_count == 0:
                    raise HTTPException(
                        status_code=500, detail="Failed to restore archived user"
                    )
                user = await users_collection.find_one({"email": email})
                # create default project for user
                new_project_id = await self.utils.create_user_default_project(str(user.get("_id")))
                # send welcome email
                send_welcome_email(user)

            token, session_id = await self.utils.create_access_token(user=user, request=request)

            return {"access_token": token, "user": {"email": email, "name": name}, "session_id": session_id, "project_id": str(new_project_id)}

        except jwt.JWTError as e:
            raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")

# Register globally
ServiceRegistry.register_api("auth", AuthAPI("/auth").router)
