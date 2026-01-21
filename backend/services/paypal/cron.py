import asyncio
from datetime import datetime
from cron.base_cron import BaseCronJob
from cron.registry import cron_job
from core.logger import Logger
from .service import PaypalService

logger = Logger(__name__)

@cron_job
class PaypalDataSyncJob(BaseCronJob):
    name = "Paypal Daily Data Sync"
    schedule = "1d"
    active = False
    
    def __init__(self, params = None):
        super().__init__(params)
        self.service = PaypalService()

    async def run(self):
        try:
            logger.info(f"[{datetime.utcnow()}] Starting paypal data sync...")
            logger.info("Starting paypal data sync")
            active_projects = await self.get_all_active_projects()

            # Limit concurrent projects to avoid hitting Stripe limits
            project_concurrency = 3
            project_semaphore = asyncio.Semaphore(project_concurrency)

            async def process_project(project):
                async with project_semaphore:
                    client_secret = str(project.get("paypal_client_secret", ""))
                    client_id = str(project.get("paypal_client_id", ""))
                    if not client_id or not client_secret:
                        logger.info(f"Skipping project {project.get('_id')} (no paypal creds)")
                        return
                    access_token = await self.service.paypal_direct_auth(client_id, client_secret)
                    if not access_token:
                        logger.info(f"Skipping project {project.get('_id')} (no paypal key)")
                        return

                    project_id = str(project["_id"])
                    logger.info(f"Starting sync for project {project_id}")

                    steps = [
                        ("user information", self.service.sync_paypal_user_info),
                        ("invoices", self.service.sync_paypal_invoices),
                        ("balances", self.service.sync_paypal_balances),
                        ("subscriptions", self.service.sync_paypal_subscriptions),
                        ("products", self.service.sync_paypal_products),
                        ("plans", self.service.sync_paypal_plans),
                        # ("payment tokens", self.service.sync_paypal_payment_tokens),
                        # ("transactions", self.service.sync_paypal_transactions),
                        # ("disputes", self.service.sync_paypal_disputes),
                    ]

                    # Limit step concurrency per project
                    step_concurrency = 4
                    step_semaphore = asyncio.Semaphore(step_concurrency)

                    async def run_step(step_name, step_fn):
                        async with step_semaphore:
                            try:
                                logger.info(f"[{project_id}] Syncing {step_name}...")
                                await step_fn(access_token, project_id)
                                logger.info(f"[{project_id}] Completed {step_name}")
                            except Exception as e:
                                logger.info(f"[{project_id}] Error in {step_name}: {e}")

                    # Run all steps in parallel (with concurrency limit)
                    await asyncio.gather(*(run_step(name, fn) for name, fn in steps))

                    logger.info(f"Completed sync for project {project_id}")

            # Run all projects in parallel (with concurrency limit)
            await asyncio.gather(*(process_project(p) for p in active_projects))
        except Exception as e:
            logger.error(f"Paypal sync error: {e}")
            return False
        
    async def get_all_active_projects(self):
        projects_collection = self.mongodb.get_collection("projects")
        projects = await projects_collection.find({"archived": False}).to_list(length=None)
        return projects if projects else []
