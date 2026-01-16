from fastapi import Request
from core.base_api import BaseAPI, get, post
from core.registry import ServiceRegistry
from core.decorators import auth_required
from .service import StripeService
from .sync import stripe_handler
from core.logger import Logger

logger = Logger(__name__)

class StripeAPI(BaseAPI):

    def __init__(self, prefix: str = ""):
        super().__init__(prefix)
        self.service = StripeService()

    @post("/oauth/callback")
    async def oauth_callback(self, request: Request):
        data = await request.json()
        code = data.get("code")
        project_id = data.get("project_id")
        stripe_user_id, access_token, refresh_token = await self.service.stripe_oauth_callback(code)
        await self.service.update_stripe_secret_key(project_id, access_token)
        # Trigger the sync in the background immediately after auth
        await stripe_handler.trigger_sync(project_id, access_token)
        return {"status": "connected", "stripe_user_id": stripe_user_id, "access_token": access_token}


    @post("/disconnect")
    @auth_required
    async def disconnect_stripe_account(self, request: Request):
        data = await request.json()
        project_id = data.get("project_id")
        if not project_id:
            raise ValueError("No project_id provided.")
        await self.service.remove_stripe_secret_key(project_id)
        await self.service.disconnect_stripe(project_id)
        return {"status": "disconnected"}

# Register it globally
ServiceRegistry.register_api("stripe", StripeAPI("/stripe").router)
