from fastapi import Request
from core.base_api import BaseAPI, post
from core.registry import ServiceRegistry
from core.decorators import auth_required
from .service import PaypalService
from .sync import paypal_handler
from core.logger import Logger

logger = Logger(__name__)

class PaypalAPI(BaseAPI):

    def __init__(self, prefix: str = ""):
        super().__init__(prefix)
        self.service = PaypalService()

    @post("/oauth/callback")
    async def oauth_callback(self, data: dict):
        project_id = data.get("project_id")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        access_token = await self.service.paypal_direct_auth(client_id, client_secret)
        if access_token:
            await self.service.update_paypal_secret_key(project_id, client_id, client_secret)
            # Trigger the sync in the background immediately after auth
            await paypal_handler.trigger_sync(project_id, access_token)

        return {
            "status": "connected",
            "access_token": access_token,
        }

    @post("/disconnect")
    @auth_required
    async def disconnect_paypal_account(self, request: Request):
        data = await request.json()
        project_id = data.get("project_id")
        if not project_id:
            raise ValueError("No project_id provided.")
        await self.service.remove_paypal_secret_key(project_id)
        await self.service.disconnect_paypal(project_id)
        return {"status": "disconnected"}

# Register it globally
ServiceRegistry.register_api("paypal", PaypalAPI("/paypal").router)
