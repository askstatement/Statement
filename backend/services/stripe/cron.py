import asyncio
from datetime import datetime
from cron.base_cron import BaseCronJob
from cron.registry import cron_job
from core.logger import Logger
from .service import StripeService

logger = Logger(__name__)

@cron_job
class StripeDataSyncJob(BaseCronJob):
    name = "Stripe Daily Data Sync"
    schedule = "1d"
    active = True
    
    def __init__(self, params = None):
        super().__init__(params)
        self.service = StripeService()

    async def run(self):
        try:
            logger.info(f"[{datetime.utcnow()}] Starting stripe data sync...")
            logger.info("Starting stripe data sync")
            active_projects = await self.get_all_active_projects()

            # Limit concurrent projects to avoid hitting Stripe limits
            project_concurrency = 3
            project_semaphore = asyncio.Semaphore(project_concurrency)

            async def process_project(project):
                async with project_semaphore:
                    access_token = str(project.get("stripe_key", ""))
                    if not access_token:
                        logger.info(f"Skipping project {project.get('_id')} (no stripe key)")
                        return

                    project_id = str(project["_id"])
                    logger.info(f"Starting sync for project {project_id}")

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

            logger.info("Stripe data sync complete.")
            return True

        except Exception as e:
            logger.error(f"Stripe sync error: {e}")
            return False
        
        
    async def get_all_active_projects(self):
        projects_collection = self.mongodb.get_collection("projects")
        projects = await projects_collection.find({"archived": False}).to_list(length=None)
        return projects if projects else []
