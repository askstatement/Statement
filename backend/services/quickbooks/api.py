from fastapi import HTTPException, Request
from core.base_api import BaseAPI, post
from core.registry import ServiceRegistry
from core.decorators import auth_required
from .service import QuickbooksService
from .sync import qb_handler
from core.logger import Logger

logger = Logger(__name__)

class QuickbooksAPI(BaseAPI):

    def __init__(self, prefix: str = ""):
        super().__init__(prefix)
        self.service = QuickbooksService()

    @post("/oauth/callback")
    async def oauth_callback(self, data: dict):
        code = data.get("code")
        realm_id = data.get("realm_id")
        project_id = data.get("project_id")
        access_token, refresh_token = await self.service.quickbooks_oauth_callback(code, realm_id)
        if not access_token or not refresh_token:
            raise HTTPException(status_code=400, detail="OAuth callback failed.")
        
        # Trigger the sync in the background immediately after auth
        await qb_handler.trigger_sync(project_id, access_token, realm_id=realm_id)
        
        await self.service.update_quickbooks_secret_key(project_id, refresh_token)
        return {"status": "connected", "access_token": access_token}

    @post("/disconnect")
    @auth_required
    async def disconnect_quickbooks_account(self, request: Request):
        data = await request.json()
        project_id = data.get("project_id")
        if not project_id:
            raise ValueError("No project_id provided.")
        await self.service.remove_quickbooks_secret_key(project_id)
        await self.service.disconnect_quickbooks(project_id)
        return {"status": "disconnected"}

# Register it globally
ServiceRegistry.register_api("quickbooks", QuickbooksAPI("/quickbooks").router)
