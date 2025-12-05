import asyncio
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, Query
from core.decorators import ws_auth_required
from core.base_websocket import BaseWebSocketHandler, register_route
from core.registry import ServiceRegistry
from .service import StripeService
from core.logger import Logger

logger = Logger(__name__)

class StripeWebSocket(BaseWebSocketHandler):
    service: StripeService
    
    @register_route("/sync-stripe-data")
    @ws_auth_required
    async def ws_sync_stripe_data(self, websocket: WebSocket):
        await websocket.accept()
        try:
            params = websocket.query_params
            project_id: Optional[str] = params.get("project_id")
            access_token: Optional[str] = params.get("access_token")
            if not project_id:
                await websocket.send_json({"status": "error", "message": "No project_id provided"})
                await websocket.close()
                return

            if not access_token:
                await websocket.send_json({"status": "error", "message": "No stripe key provided"})
                await websocket.close()
                return
            
            steps = [
                ("invoices", self.service.sync_stripe_invoices),
                ("customers", self.service.sync_stripe_customers),
                ("products", self.service.sync_stripe_products),
                ("subscriptions", self.service.sync_stripe_subscriptions),
                ("balance_transactions", self.service.sync_stripe_balancetransactions),
                ("events", self.service.sync_stripe_events),
                ("charges", self.service.sync_stripe_charges),
                ("refunds", self.service.sync_stripe_refunds),
                ("payouts", self.service.sync_stripe_payouts),
                ("payment_intents", self.service.sync_stripe_payment_intents),
                ("plans", self.service.sync_stripe_plans),
                ("coupons", self.service.sync_stripe_coupons),
                ("balance", self.service.sync_stripe_balance),
                ("disputes", self.service.sync_stripe_disputes),
                ("payment_methods", self.service.sync_stripe_payment_methods),
                ("setup_intents", self.service.sync_stripe_setup_intents),
                ("tax_rates", self.service.sync_stripe_tax_rates),
                ("application_fees", self.service.sync_stripe_application_fees),
                ("transfers", self.service.sync_stripe_transfers),
            ]

            total_steps = len(steps) + 2
            completed = 0

            async def run_step(step_name, step_fn):
                nonlocal completed
                try:
                    await websocket.send_json({"status": "in-progress", "step": step_name, "progress": f"{completed}/{total_steps}"})
                    await step_fn(access_token, project_id)
                    completed += 1
                    await websocket.send_json({"status": "in-progress", "step": step_name, "progress": f"{completed}/{total_steps}"})
                except Exception as e:
                    await websocket.send_json({"status": "error", "step": step_name, "message": str(e)})

            # Run up to 4 sync tasks concurrently (you can tune this)
            concurrency_limit = 4
            semaphore = asyncio.Semaphore(concurrency_limit)

            async def limited_run(step_name, step_fn):
                async with semaphore:
                    await run_step(step_name, step_fn)

            # Start all tasks concurrently with a limit
            tasks = [limited_run(name, fn) for name, fn in steps]
            await asyncio.gather(*tasks)

            await websocket.send_json({"status": "in-progress", "step": "saving_creds", "progress": f"{total_steps - 2}/{total_steps}"})
            await self.service.update_stripe_secret_key(project_id, access_token)
            await websocket.send_json({"status": "in-progress", "step": "insights", "progress": f"{total_steps - 1}/{total_steps}"})

            await websocket.send_json({"status": "done", "message": "All sync steps completed."})
            await websocket.close()

        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            await websocket.send_json({"status": "error", "message": str(e)})
            await websocket.close()

# Register it globally
ServiceRegistry.register_websocket("stripe", StripeWebSocket())
