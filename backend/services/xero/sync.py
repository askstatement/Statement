from typing import Optional, List, Tuple, Callable
from core.base_handler import BaseSyncHandler
from .service import XeroService
from core.logger import Logger

logger = Logger(__name__)


class XeroSyncHandler(BaseSyncHandler):
    """
    Handles Xero data synchronization using the base sync framework.
    """

    service_name = "xero"
    concurrency_limit = 1  # Sync steps sequentially

    def __init__(self):
        super().__init__()
        self.service = XeroService()

    def get_steps(self) -> List[Tuple[str, Callable]]:
        """
        Define all Xero sync steps.
        """
        return [
            ("tenants", self.service.sync_xero_tenants),
            ("accounts", self.service.sync_xero_accounts),
            ("invoices", self.service.sync_xero_invoices),
            ("bank transactions", self.service.sync_xero_bank_transactions),
            ("bank transfers", self.service.sync_xero_bank_transfers),
            ("batch payments", self.service.sync_xero_batch_payments),
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
            # for future use ("payroll employees", self.service.sync_xero_payroll_employees),
            # for future use ("payroll pay runs", self.service.sync_xero_payroll_pay_runs),
            # for future use ("payroll pay slips", self.service.sync_xero_payroll_payslips),
            # for future use ("payroll time sheets", self.service.sync_xero_payroll_timesheets),
            # for future use ("payroll leaves", self.service.sync_xero_payroll_leave_applications),
        ]


xero_handler = XeroSyncHandler()
