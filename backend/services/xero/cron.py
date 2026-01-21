import asyncio
from datetime import datetime
from cron.base_cron import BaseCronJob
from cron.registry import cron_job
from core.logger import Logger
from .service import XeroService

logger = Logger(__name__)

@cron_job
class XeroDataSyncJob(BaseCronJob):
    name = "Xero Daily Data Sync"
    schedule = "1d"
    active = False
    
    def __init__(self, params = None):
        super().__init__(params)
        self.service = XeroService()

    async def run(self):
        try:
            logger.info(f"[{datetime.utcnow()}] Starting xero data sync...")
            logger.info("Starting xero data sync")
            active_projects = await self.get_all_active_projects()

            # Limit concurrent projects to avoid hitting Stripe limits
            project_concurrency = 3
            project_semaphore = asyncio.Semaphore(project_concurrency)

            async def process_project(project):
                async with project_semaphore:
                    access_token = str(project.get("xero_refresh_key", ""))
                    # TODO: implement token refresh logic
                    if not access_token:
                        logger.info(f"Skipping project {project.get('_id')} (no xero key)")
                        return

                    project_id = str(project["_id"])
                    logger.info(f"Starting sync for project {project_id}")

                    # Define steps to keep DRY
                    steps = [
                        ("tenants", self.service.sync_xero_tenants),
                        ("accounts", self.service.sync_xero_accounts),
                        ("invoices", self.service.sync_xero_invoices),
                        ("bank transactions", self.service.sync_xero_bank_transactions),
                        ("bank transfers", self.service.sync_xero_bank_transfers),
                        ("batch payments", self.service.sync_xero_batch_payments),
                        ("budgets", self.service.sync_xero_budgets),
                        ("budgets", self.service.sync_xero_budgets),
                        ("contact groups", self.service.sync_xero_contact_groups),
                        ("contacts", self.service.sync_xero_contacts),
                        ("credit notes", self.service.sync_xero_credit_notes),
                        ("linked transactions", self.service.sync_xero_linked_transactions),
                        ("journals", self.service.sync_xero_journals),
                        ("items", self.service.sync_xero_items),
                        ("manual journals", self.service.sync_xero_manual_journals),
                        ("organisation", self.service.sync_xero_organisation),
                        ("over payments", self.service.sync_xero_overpayments),
                        ("payments", self.service.sync_xero_payments),
                        ("pre payments", self.service.sync_xero_prepayments),
                        ("purchase orders", self.service.sync_xero_purchase_orders),
                        ("quotes", self.service.sync_xero_quotes),
                        ("repeating invoices", self.service.sync_xero_repeating_invoices),
                        ("tax rates", self.service.sync_xero_tax_rates),
                        ("users", self.service.sync_xero_users),
                        ("asset types", self.service.sync_xero_asset_types),
                        ("assets", self.service.sync_xero_assets),
                        # needs elevated access ("feed connections", self.service.sync_xero_feed_connections),
                        # needs elevated access  ("statements", self.service.sync_xero_statements),
                        ("payroll employees", self.service.sync_xero_payroll_employees),
                        ("payroll pay runs", self.service.sync_xero_payroll_pay_runs),
                        ("payroll pay slips", self.service.sync_xero_payroll_payslips),
                        ("payroll time sheets", self.service.sync_xero_payroll_timesheets),
                        ("payroll leaves", self.service.sync_xero_payroll_leave_applications),
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
