import pyotp
import qrcode
import base64
from io import BytesIO
from core.base_api import BaseAPI, get, post
from core.registry import ServiceRegistry
from core.decorators import auth_required
from fastapi import Request, HTTPException

from .utils import SettingsUtils
from .models import PreferencesUpdate

class SettingsAPI(BaseAPI):
    utils: SettingsUtils
    
    @get("/")
    @auth_required
    async def get_settings(self, request: Request):
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        users_collection = self.mongodb.get_collection("users")
        existing_user = await users_collection.find_one({"email": user['email'], "$or": [{"archived": {"$exists": False}}, {"archived": False}]})
        if existing_user:
            password = existing_user.get('hashed_password')
            sso_signup = password is None or password == ""

            return {
                "email": existing_user.get("email"),
                "firstname": existing_user.get("firstname"),
                "lastname": existing_user.get("lastname"),
                "fullname": existing_user.get("fullname", ""),
                "companyname": existing_user.get("companyname", ""),
                "companyaddress": existing_user.get("companyaddress", ""),
                "currency": existing_user.get("currency", "USD"),
                "timezone": existing_user.get("timezone", "GMT+1"),
                "pwd": existing_user.get("hashed_password"),
                "street": existing_user.get("street", ""),
                "city": existing_user.get("city", ""),
                "state": existing_user.get("state", ""),
                "postcode": existing_user.get("postcode", ""),
                "two_factor_enabled": existing_user.get("two_factor_enabled", False),
                "is_sso_signup": sso_signup
            }
            
    @post("/profile")
    @auth_required
    async def update_profile(self, request: Request, profile_data: dict):
        users_collection = self.mongodb.get_collection("users")
        user = request.state.user
        if not user or 'email' not in user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Build update data dynamically 
        update_data = {}
        
        if 'fullname' in profile_data:
            update_data['fullname'] = profile_data['fullname']
        
        if 'street' in profile_data or 'city' in profile_data or 'state' in profile_data or 'postcode' in profile_data:
            if 'street' in profile_data and profile_data['street']:
                update_data['street'] = profile_data['street']
            if 'city' in profile_data and profile_data['city']:
                update_data['city'] = profile_data['city']
            if 'state' in profile_data and profile_data['state']:
                update_data['state'] = profile_data['state']
            if 'postcode' in profile_data and profile_data['postcode']:
                update_data['postcode'] = profile_data['postcode']
            
        if 'email' in profile_data:
            # Check if email already exists for another user
            existing_email = await users_collection.find_one({
                "email": profile_data['email'], "$or": [{"archived": {"$exists": False}}, {"archived": False}]
            })
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")
            
            update_data['email'] = profile_data['email']
            
        if 'companyname' in profile_data:
            update_data['companyname'] = profile_data['companyname']
        
        if 'companyaddress' in profile_data:
            update_data['companyaddress'] = profile_data['companyaddress']
        
        if 'currency' in profile_data:
            update_data['currency'] = profile_data['currency']
        
        if 'timezone' in profile_data:
            update_data['timezone'] = profile_data['timezone']
        
        # Only update if there's something to update
        if update_data:
            await users_collection.update_one(
                {"email": user['email']},
                {"$set": update_data}
            )
        
        return {"message": "Profile updated successfully"}
    
    @post("/password")
    @auth_required
    async def update_password(self, request: Request, password_data: dict):
        user = request.state.user
        if not user or 'email' not in user:
            raise HTTPException(status_code=401, detail="Unauthorized, no email")
        
        current_password = password_data.get("currentPassword")
        hashed_password = user.get('hashed_password')

        # Validate that newPassword is provided
        if hashed_password and not current_password :
            raise HTTPException(status_code=400, detail="Current password is required")
        
        if hashed_password:
            user = await self.utils.authenticate_user(user['email'], password_data['currentPassword'])
            if not user:
                raise HTTPException(status_code=401, detail="Invalid current password")
        
        # Validate that newPassword is provided
        if 'newPassword' not in password_data:
            raise HTTPException(status_code=400, detail="New password is required")
        
        # Update to new password
        new_hashed_password = self.utils.hash_password(password_data['newPassword'])
        users_collection = self.mongodb.get_collection("users")
        await users_collection.update_one(
            {"email": user['email']},
            {"$set": {"hashed_password": new_hashed_password}}
        )
        
        return {"message": "Password updated successfully"}
    
    @get("/activity")
    @auth_required
    async def get_user_activity(self, request: Request):
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Get user security settings
        users_collection = self.mongodb.get_collection("users")
        existing_user = await users_collection.find_one({"email": user['email'], "$or": [{"archived": {"$exists": False}}, {"archived": False}]})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get current sessions 
        current_sessions = await self.utils.get_user_sessions(user['email'])  
        
        # Get recent login activity
        recent_activity = await self.utils.get_recent_login_activity(user['email']) 
        
        return {
            "currentSessions": self.utils.sanitize_mongo_doc(current_sessions),
            "twoFactorEnabled": existing_user.get("two_factor_enabled", False),
            "notify": existing_user.get("notify", False),
            "recentActivity": recent_activity
        }
        
    @post("/preferences")
    @auth_required
    async def update_preferences(self, request: Request):
        user = request.state.user
        body = await request.json()
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        update_fields = {}

        for key, value in body["notify"].items():
            update_fields[f"notify.{key}"] = value

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields provided")

        users_collection = self.mongodb.get_collection("users")
        await users_collection.update_one(
            {"email": user["email"]},
            {"$set": update_fields}
        )

        return {"message": "Preferences updated successfully", "updated": update_fields}
    

    @get("/2fa_setup")
    @auth_required
    async def setup_2fa(self, request: Request):
        user = request.state.user
        users = self.mongodb.get_collection("users")

        if user.get("two_factor_enabled"):
            raise HTTPException(400, "2FA already enabled")

        secret = user.get("two_factor_secret")

        # Generate ONLY ONCE
        if not secret:
            secret = pyotp.random_base32()
            await users.update_one(
                {"email": user["email"]},
                {"$set": {"two_factor_secret": secret}}
            )

        totp = pyotp.TOTP(secret)
        otpauth_url = totp.provisioning_uri(
            name=user["email"],
            issuer_name="Statement"
        )

        img = qrcode.make(otpauth_url)
        buffer = BytesIO()
        img.save(buffer, format="PNG")

        qr_code = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

        return {"qrCode": qr_code, "secret": secret}
        
    @post("/2fa_verify")
    @auth_required
    async def verify_2fa(self, request: Request):
        user = request.state.user
        body = await request.json()

        token = body.get("token")
        action = body.get("twoFactorAuthValue")

        if not token:
            raise HTTPException(400, "Token required")

        if action not in ("enable", "disable"):
            raise HTTPException(400, "Invalid action")

        users = self.mongodb.get_collection("users")

        secret = user.get("two_factor_secret")
        if not secret:
            raise HTTPException(400, "2FA not setup")

        totp = pyotp.TOTP(secret)
        if not totp.verify(token, valid_window=1):
            raise HTTPException(400, "Invalid code")

        if action == "enable":
            await users.update_one(
                {"email": user["email"]},
                {"$set": {"two_factor_enabled": True}}
            )
        else:
            await users.update_one(
                {"email": user["email"]},
                {
                    "$set": {"two_factor_enabled": False},
                    "$unset": {"two_factor_secret": ""}
                }
            )

        return {"success": True}
            
    @get("/usage")
    @auth_required
    async def get_usage(self, request: Request):
        project_id = request.query_params.get("projectId")
        project = await self.utils.get_project_from_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        usage_data = {
            "credits_used": project.get("credits_used", 0),
            "credits_allowed": project.get("credits_allowed", 0)
        }
        return {"usage": usage_data}

# Register globally
ServiceRegistry.register_api("settings", SettingsAPI("/settings").router)
