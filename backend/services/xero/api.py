from fastapi import HTTPException, Request
from core.base_api import BaseAPI, post
from core.registry import ServiceRegistry
from core.decorators import auth_required
from .service import XeroService
from .sync import xero_handler
from core.logger import Logger

logger = Logger(__name__)

class XeroAPI(BaseAPI):

    def __init__(self, prefix: str = ""):
        super().__init__(prefix)
        self.service = XeroService()

    @post("/oauth/callback")
    async def oauth_callback(self, data: dict):
        code = data.get("code")
        code_verifier = data.get("code_verifier")
        project_id = data.get("project_id")
        access_token, refresh_token = await self.service.xero_oauth_callback(code, code_verifier)
        if not access_token or not refresh_token:
            raise HTTPException(status_code=400, detail="OAuth callback failed.")
        await self.service.update_xero_secret_key(project_id, refresh_token)
        
        # Trigger the sync in the background immediately after auth
        await xero_handler.trigger_sync(project_id, access_token)
        
        return {"status": "connected", "access_token": access_token}

    @post("/disconnect")
    @auth_required
    async def disconnect_xero_account(self, request: Request):
        data = await request.json()
        project_id = data.get("project_id")
        if not project_id:
            raise ValueError("No project_id provided.")
        await self.service.remove_xero_secret_key(project_id)
        await self.service.disconnect_xero(project_id)
        return {"status": "disconnected"}


# Register it globally
ServiceRegistry.register_api("xero", XeroAPI("/xero").router)
