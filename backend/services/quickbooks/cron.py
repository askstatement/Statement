import asyncio
from datetime import datetime
from cron.base_cron import BaseCronJob
from cron.registry import cron_job
from core.logger import Logger
from .service import QuickbooksService

logger = Logger(__name__)

@cron_job
class QuickbooksDataSyncJob(BaseCronJob):
    name = "Quickbooks Daily Data Sync"
    schedule = "1d"
    active = False
    
    def __init__(self, params = None):
        super().__init__(params)
        self.service = QuickbooksService()

    async def run(self):
        try:
            logger.info(f"[{datetime.utcnow()}] Starting quickbooks data sync...")
            logger.info("Starting quickbooks data sync")
            active_projects = await self.get_all_active_projects()

            # Limit concurrent projects to avoid hitting Stripe limits
            project_concurrency = 3
            project_semaphore = asyncio.Semaphore(project_concurrency)

            async def process_project(project):
                async with project_semaphore:
                    access_token = str(project.get("quickbooks_refresh_key", ""))
                    # TODO: implement token refresh logic
                    if not access_token:
                        logger.info(f"Skipping project {project.get('_id')} (no quickbooks key)")
                        return

                    project_id = str(project["_id"])
                    logger.info(f"Starting sync for project {project_id}")

                    # Define steps to keep DRY
                    steps = [
                        ("tenants", self.service.sync_xero_tenants),
                        ("invoices", self.service.sync_xero_invoices),
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
            logger.error(f"Quickbooks sync error: {e}")
            return False
        
    async def get_all_active_projects(self):
        projects_collection = self.mongodb.get_collection("projects")
        projects = await projects_collection.find({"archived": False}).to_list(length=None)
        return projects if projects else []
