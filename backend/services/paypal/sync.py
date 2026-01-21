from typing import Optional, List, Tuple, Callable
from core.base_handler import BaseSyncHandler
from .service import PaypalService
from core.logger import Logger

logger = Logger(__name__)


class PaypalSyncHandler(BaseSyncHandler):
    """
    Handles Paypal data synchronization using the base sync framework.
    """

    service_name = "paypal"
    concurrency_limit = 1  # Sync steps sequentially

    def __init__(self):
        super().__init__()
        self.service = PaypalService()

    def get_steps(self) -> List[Tuple[str, Callable]]:
        """
        Define all Paypal sync steps.
        """
        return [
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


paypal_handler = PaypalSyncHandler()
