from typing import Optional, List, Tuple, Callable
from core.base_handler import BaseSyncHandler
from .service import StripeService
from core.logger import Logger

logger = Logger(__name__)


class StripeSyncHandler(BaseSyncHandler):
    """
    Handles Stripe data synchronization using the base sync framework.
    """

    service_name = "stripe"
    concurrency_limit = 1  # Sync steps concurrently

    def __init__(self):
        super().__init__()
        self.service = StripeService()

    def get_steps(self) -> List[Tuple[str, Callable]]:
        """
        Define all Stripe sync steps.
        """
        return [
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


stripe_handler = StripeSyncHandler()
