from typing import Optional, List, Tuple, Callable
from core.base_handler import BaseSyncHandler
from .service import QuickbooksService
from core.logger import Logger

logger = Logger(__name__)


class QuickbooksSyncHandler(BaseSyncHandler):
    """
    Handles Quickbooks data synchronization using the base sync framework
    triggered via API.
    """

    service_name = "quickbooks"
    concurrency_limit = 1  # Sync steps sequentially

    def __init__(self):
        super().__init__()
        self.service = QuickbooksService()

    def get_steps(self) -> List[Tuple[str, Callable]]:
        """
        Define all Quickbooks sync steps.
        """
        return [
            ("accounts", self.service.sync_quickbooks_accounts),
            ("bills", self.service.sync_quickbooks_bills),
            ("budgets", self.service.sync_quickbooks_budgets),
            ("cashflows", self.service.sync_quickbooks_cashflows),
            ("company info", self.service.sync_quickbooks_company_info),
            ("customers", self.service.sync_quickbooks_customers),
            ("employees", self.service.sync_quickbooks_employees),
            ("estimates", self.service.sync_quickbooks_estimates),
            ("invoices", self.service.sync_quickbooks_invoices),
            ("items", self.service.sync_quickbooks_items),
            ("payments", self.service.sync_quickbooks_payments),
            ("preferences", self.service.sync_quickbooks_preferences),
            ("profit and loss", self.service.sync_quickbooks_profit_and_loss),
            ("purchase orders", self.service.sync_quickbooks_purchase_orders),
            ("credit memos", self.service.sync_quickbooks_credit_memos),
            ("sales receipts", self.service.sync_quickbooks_sales_receipts),
            ("refund receipts", self.service.sync_quickbooks_refund_receipts),
            ("journal entries", self.service.sync_quickbooks_journal_entries),
            ("vendors", self.service.sync_quickbooks_vendors),
            ("transfers", self.service.sync_quickbooks_transfers),
            ("deposits", self.service.sync_quickbooks_deposits),
            ("bill payments", self.service.sync_quickbooks_bill_payments),
            ("vendor credits", self.service.sync_quickbooks_vendor_credits),
        ]


# Initialize the handler
qb_handler = QuickbooksSyncHandler()
