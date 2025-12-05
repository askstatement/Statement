from datetime import datetime
from collections import defaultdict
from datetime import datetime, timedelta

from core.registry import ServiceRegistry
from dateutil.relativedelta import relativedelta
from core.base_tools import BaseTool
from core.logger import Logger

logger = Logger(__name__)

class ReactDatabaseTools(BaseTool):
    """Tool class to interact with MongoDB and Elasticsearch databases"""
        
    def convert_date_to_timestamp(self, date_string: str) -> int:
        """
        Convert ISO date string (YYYY-MM-DD) to Unix timestamp

        Args:
            date_string: Date in format 'YYYY-MM-DD'

        Returns:
            Unix timestamp (seconds since epoch)

        Raises:
            ValueError: If date format is invalid
        """
        try:
            dt = datetime.strptime(date_string, "%Y-%m-%d")
            # Set to end of day to include all subscriptions created on that day
            dt = dt.replace(hour=23, minute=59, second=59)
            return int(dt.timestamp())
        except ValueError as e:
            raise ValueError(
                f"Invalid date format: {date_string}. Expected 'YYYY-MM-DD'"
            ) from e


    def calculate_monthly_revenue(self, project_id: str, start_date: str, end_date: str):
        """
        Calculate monthly revenue using a data range.
        Use this function if the user is asking for monthly revenue for a specific month or in a date dange.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            Unix timestamp (seconds since epoch)

        Raises:
            ValueError: If date format is invalid
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            filters = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
                {"term": {"cleaned_data.status.keyword": "paid"}},
            ]

            all_docs = self._query_elasticsearch(index="stripe_invoices", filters=filters)

            monthly_totals = 0
            for doc in all_docs:
                data = doc["_source"].get("cleaned_data", {})
                amount_paid = float(data.get("amount_paid", 0))
                monthly_totals += amount_paid

            return {
                "revenue": monthly_totals,
                "start_date": start_date,
                "end_date": end_date,
            }

        except Exception as e:
            logger.error(f"Errorcalculating monthly revenue: {str(e)}")
            return {"revenue": 0, "start_date": start_date, "end_date": end_date}


    def calculate_net_mrr_from_invoices(self, project_id: str):
        """
        Calculate Net MRR (after coupons/discounts, ignoring prorations).
        Only use this function if the user is looking for MRR specifically without a date range.
        Args:
            project_id: The project identifier
        Returns:
            float: Net MRR calculation result
        """
        try:
            # set start_date as start of current month and end_date as end of current month
            filters = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "active"}},
            ]
            subscriptions = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters
            )

            subscription_ids = []
            latest_invoice_map = {}  # Map subscription_id -> latest_invoice_id
            for hit in subscriptions:
                sub = hit["_source"]["cleaned_data"]
                sub_id = sub.get("id")
                subscription_ids.append(sub_id)
                # Get latest invoice ID
                latest_invoice_id = sub.get("latest_invoice")
                if latest_invoice_id:
                    latest_invoice_map[sub_id] = latest_invoice_id

            if not latest_invoice_map:
                return 0.0

            # Step 2: Query invoices using these latest_invoice_ids
            invoice_ids = list(latest_invoice_map.values())
            es_query = {
                "bool": {
                    "filter": [
                        {"term": {"project_id": project_id}},
                        {
                            "terms": {"invoice_id": invoice_ids}
                        },  # fetch only latest invoices
                        {"term": {"cleaned_data.status.keyword": "paid"}},
                    ]
                }
            }
            invoices = self._query_elasticsearch(index="stripe_invoices", query=es_query)
            start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")
            end_date = (
                datetime.now().replace(day=1) + relativedelta(months=1) - timedelta(days=1)
            ).strftime("%Y-%m-%d")
            total_net_mrr = self._calculate_mrr_from_invoices(
                invoices, project_id, start_date, end_date
            )
            result = round(total_net_mrr, 2)
            logger.info(f"result: {result}")

            return result

        except Exception as e:
            logger.error(f"Errorcalculating MRR: {str(e)}")
            return 0.0


    def _calculate_mrr_from_invoices(
        self, invoices: list, project_id: str, start_date: str, end_date: str
    ):
        """
        Private function to calculate MRR using invoices provided.
        Args:
            project_id: The project identifier
            invoices: List of invoice documents from Elasticsearch
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')
        Returns:
            MRR value (float)
        """
        try:
            # Convert input dates to epoch timestamps
            start_ts = self.convert_date_to_timestamp(start_date)
            end_ts = self.convert_date_to_timestamp(end_date)

            total_monthly_mrr = 0.0
            seen_lines = set()

            # --- Process invoices ---
            for hit in invoices:
                inv = hit.get("_source", {}).get("cleaned_data", {})
                amount_paid = inv.get("amount_paid", inv.get("total", 0.0)) or 0.0
                lines = inv.get("lines", {}).get("data", [])
                inv_date = inv.get("created", None)
                customer = inv.get("customer", "")

                # --- Preload refunds and credit notes for same time period ---
                if inv_date:
                    refund_query = {
                        "bool": {
                            "filter": [
                                {"term": {"project_id": project_id}},
                                {"term": {"cleaned_data.customer.keyword": customer}},
                                {"term": {"cleaned_data.status.keyword": "succeeded"}},
                                {"range": {"cleaned_data.created": {"gte": inv_date}}},
                            ]
                        }
                    }

                    refunds = self._query_elasticsearch(
                        index="stripe_charges", query=refund_query
                    )

                    # Map refund/credit totals per customer
                    refund_map = {}
                    for r in refunds:
                        data = r.get("_source", {}).get("cleaned_data", {})
                        cust = data.get("customer")
                        amount = data.get("amount") or data.get("amount_captured") or 0.0
                        amount_refunded = data.get("amount_refunded") or 0.0
                        # match the invoice amount refunded
                        if cust and amount_refunded > 0 and amount_paid == amount:
                            refund_map[f"{cust}-{amount}"] = refund_map.get(
                                cust, 0
                            ) + float(amount_refunded)

                if not lines:
                    continue

                # collect recurring/subscription lines
                recurring_lines = []
                for line in lines:
                    parent = line.get("parent", {})
                    parent_type = parent.get("type") or parent.get("parent_type")
                    subscription_item_details = parent.get("subscription_item_details", {})
                    subscription_id = (
                        subscription_item_details.get("subscription")
                        if isinstance(subscription_item_details, dict)
                        else None
                    )
                    is_subscription_line = (
                        parent_type in ("subscription_details", "subscription_item_details")
                        or "subscription_item_details" in parent
                    )

                    if not is_subscription_line:
                        continue

                    period = line.get("period", {})
                    p_start = period.get("start")
                    p_end = period.get("end")
                    p_start_dt = datetime.fromtimestamp(p_start)
                    p_end_dt = datetime.fromtimestamp(p_end)
                    if not (p_start and p_end):
                        continue

                    if p_start > end_ts or p_end < start_ts:
                        continue

                    # Avoid double-counting same subscription line in overlapping invoices
                    if subscription_id:
                        unique_key_start = (subscription_id, p_start_dt.month)
                        unique_key_end = (subscription_id, p_end_dt.month)
                        if unique_key_start in seen_lines or unique_key_end in seen_lines:
                            continue
                        seen_lines.add(unique_key_start)
                        seen_lines.add(unique_key_end)

                    line_amount = line.get("amount")
                    if line_amount is None:
                        pricing = line.get("pricing", {})
                        price_details = (
                            pricing.get("price_details", {})
                            if isinstance(pricing, dict)
                            else {}
                        )
                        unit_amount_decimal = price_details.get(
                            "unit_amount_decimal"
                        ) or pricing.get("unit_amount_decimal")
                        if unit_amount_decimal:
                            try:
                                line_amount = float(unit_amount_decimal) / 100.0
                            except Exception:
                                line_amount = 0.0
                        else:
                            line_amount = 0.0

                    recurring_lines.append(
                        {
                            "amount": float(line_amount or 0.0),
                            "period_start": int(p_start),
                            "period_end": int(p_end),
                        }
                    )

                if not recurring_lines:
                    continue

                total_line_amount = sum(l["amount"] for l in recurring_lines)
                if total_line_amount <= 0:
                    continue

                customer_refund = refund_map.get(f"{customer}-{amount_paid}", 0.0)

                for rl in recurring_lines:
                    period_days = max(1, (rl["period_end"] - rl["period_start"]) / 86400.0)
                    line_share = rl["amount"] / total_line_amount
                    allocated_paid = (amount_paid - customer_refund) * line_share
                    monthly_equivalent = allocated_paid * (30.0 / period_days)

                    total_monthly_mrr += monthly_equivalent

            result = round(total_monthly_mrr, 2)
            return result

        except Exception as e:
            logger.error(f"Errorcalculating MRR from invoices: {e}")
            return 0.0


    def calculate_mrr_in_a_period(self, project_id: str, start_date: str, end_date: str):
        """
        Calculate MRR for a given date range using invoices, including refunds & credit notes.

        Logic:
        - Query invoices whose line-item periods overlap the requested date range.
        - Include only 'paid' invoices.
        - Consider only recurring/subscription lines.
        - Allocate invoice.amount_paid proportionally across recurring lines.
        - Normalize each line's revenue to a 30-day month equivalent.
        - Subtract refunds and credit notes from the MRR for the same customer & period.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            MRR value for the specified period (float)
        """
        try:
            # Convert input dates to epoch timestamps
            start_ts = self.convert_date_to_timestamp(start_date)
            end_ts = self.convert_date_to_timestamp(end_date)

            # Query invoices overlapping the requested window
            es_query = {
                "bool": {
                    "filter": [
                        {"term": {"project_id": project_id}},
                        {"term": {"cleaned_data.status.keyword": "paid"}},
                        {
                            "range": {
                                "cleaned_data.lines.data.period.start": {"lte": end_ts}
                            }
                        },
                        {
                            "range": {
                                "cleaned_data.lines.data.period.end": {"gte": start_ts}
                            }
                        },
                    ]
                }
            }

            invoices = self._query_elasticsearch(index="stripe_invoices", query=es_query)
            result = self._calculate_mrr_from_invoices(
                invoices, project_id, start_date, end_date
            )
            logger.info(f"MRR result: {result}")
            return result

        except Exception as e:
            logger.error(f"Errorcalculating MRR from invoices: {e}")
            return 0.0


    def calculate_arr(self, project_id: str):
        """
        ARR (Annual Recurring Revenue) = self._calculate_mrr_from_invoices(project_id) * 12.

        Args:
            project_id: The project identifier

        Returns:
            float: Basic ARR calculation result
        """
        try:
            total_arr = self._calculate_mrr_from_invoices(project_id) * 12
            result = round(total_arr, 2)
            logger.info(f"result: {result}")

            return result

        except Exception as e:
            logger.error(f"Errorcalculating ARR: {str(e)}")
            return 0.0


    def calculate_active_customers(self, project_id: str, start_date: str, end_date: str):
        """
        Calculate count of distinct active customers based on invoices (not subscriptions).
        A customer is considered active if they have at least one 'paid' invoice
        that includes a recurring/subscription line overlapping the given period.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            tuple: (int: Active customer count, list: Customer details)
        """
        try:
            # Convert dates to timestamps
            start_ts = self.convert_date_to_timestamp(start_date)
            end_ts = self.convert_date_to_timestamp(end_date)

            # --- Query invoices that overlap the given window ---
            es_query = {
                "bool": {
                    "filter": [
                        {"term": {"project_id": project_id}},
                        {"term": {"cleaned_data.status.keyword": "paid"}},
                        {
                            "range": {
                                "cleaned_data.lines.data.period.start": {"lte": end_ts}
                            }
                        },
                        {
                            "range": {
                                "cleaned_data.lines.data.period.end": {"gte": start_ts}
                            }
                        },
                    ]
                }
            }

            invoices = self._query_elasticsearch(index="stripe_invoices", query=es_query)

            active_customer_ids = set()

            # --- Extract customers from invoices that have recurring/subscription lines ---
            for hit in invoices:
                inv = hit.get("_source", {}).get("cleaned_data", {})
                customer = inv.get("customer")
                if not customer:
                    continue

                lines = inv.get("lines", {}).get("data", [])
                if not lines:
                    continue

                # Check if the invoice has at least one subscription/recurring line
                for line in lines:
                    parent = line.get("parent", {})
                    parent_type = parent.get("type") or parent.get("parent_type")
                    is_subscription_line = (
                        parent_type in ("subscription_details", "subscription_item_details")
                        or "subscription_item_details" in parent
                    )
                    if is_subscription_line:
                        active_customer_ids.add(customer)
                        break  # No need to check more lines for this invoice

            active_customers_count = len(active_customer_ids)
            logger.info(f"active_customers_count: {active_customers_count}")

            # --- Fetch customer details from stripe_customers index (limit 20) ---
            customer_info = []
            first_20 = list(active_customer_ids)[:20]
            for customer_id in first_20:
                customer_hits = self._query_elasticsearch(
                    index="stripe_customers",
                    filters=[{"term": {"customer_id": customer_id}}],
                    source=["name", "email", "customer_id"],
                )
                for hit in customer_hits:
                    customer_info.append(hit["_source"])

            return active_customers_count, customer_info

        except Exception as e:
            logger.error(f"Errorcalculating active customers (invoice-based): {str(e)}")
            return 0, []


    def calculate_arpu(self, project_id: str, start_date: str, end_date: str):
        """
        Calculate ARPU (Average Revenue per User) = MRR / Active Customers.

        Args:
            project_id: The project identifier
            start_date: Optional period start date (ISO format: 'YYYY-MM-DD')
            end_date: Optional period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            int: ARPU calculation result
        """
        try:
            active_customers_count, customers = self.calculate_active_customers(
                project_id, start_date, end_date
            )
            if active_customers_count == 0:
                return 0.0
            mrr = (
                self.calculate_mrr_in_a_period(project_id, start_date, end_date)
                if start_date and end_date
                else self._calculate_mrr_from_invoices(project_id)
            )
            arpu = mrr / active_customers_count if active_customers_count > 0 else 0.0
            result = round(arpu, 2)
            logger.info(f"Average Revenue per User - result: {result}")
            return result
        except Exception as e:
            logger.error(f"Errorcalculating ARPU: {str(e)}")
            return 0.0


    def calculate_churn_rate(self, project_id: str, start_date: str, end_date: str) -> float:
        """
        Calculate Churn Rate (Customer) = Churned Customers / Active Customers at Start.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Churn rate as a percentage
        """
        try:
            # Convert dates to timestamps
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)
            # Get active customers at start of period
            # A subscription is active at start_timestamp if:
            # 1. It was created before start_timestamp
            # 2. AND either it hasn't ended yet OR it ended on/after start_timestamp
            filters_start = [
                {"term": {"project_id": project_id}},
                {"range": {"cleaned_data.created": {"lt": start_timestamp}}},
            ]

            query_start = {
                "bool": {
                    "filter": filters_start,
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "cleaned_data.ended_at"}}
                            }
                        },
                        {"range": {"cleaned_data.ended_at": {"gte": start_timestamp}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

            subs_start = self._query_elasticsearch(
                index="stripe_subscriptions", query=query_start
            )
            active_start_customers = set()
            for hit in subs_start:
                customer_id = hit["_source"]["cleaned_data"].get("customer")
                if customer_id:
                    active_start_customers.add(customer_id)
            active_start_count = len(active_start_customers)
            if active_start_count == 0:
                logger.info("no active_start_customers")
                return 0.0

            # Get churned customers in period (subscriptions that were canceled in period)
            filters_churned = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.ended_at": {
                            "gte": start_timestamp,
                            "lt": end_timestamp,
                        }
                    }
                },
            ]
            subs_churned = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters_churned
            )
            churned_customers = set()
            for hit in subs_churned:
                customer_id = hit["_source"]["cleaned_data"].get("customer")
                if customer_id and customer_id in active_start_customers:
                    churned_customers.add(customer_id)
            churned_count = len(churned_customers)

            churn_rate = churned_count / active_start_count
            result = round(churn_rate * 100, 2)
            logger.info(f"Churn Rate (%): {result}")
            return result

        except Exception as e:
            logger.error(f"Errorcalculating churn rate: {str(e)}")
            return 0.0


    def calculate_revenue_churn(self, project_id: str, start_date: str, end_date: str) -> float:
        """
        Calculate Revenue Churn Rate = Churned MRR / MRR at Start.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Revenue churn rate as a percentage
        """
        try:
            # Convert dates to timestamps
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)
            # Get active customers at start of period
            # A subscription is active at start_timestamp if:
            # 1. It was created before start_timestamp
            # 2. AND either it hasn't ended yet OR it ended on/after start_timestamp
            filters_start = [
                {"term": {"project_id": project_id}},
                {"range": {"cleaned_data.created": {"lt": start_timestamp}}},
            ]

            query_start = {
                "bool": {
                    "filter": filters_start,
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "cleaned_data.ended_at"}}
                            }
                        },
                        {"range": {"cleaned_data.ended_at": {"gte": start_timestamp}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

            subs_start = self._query_elasticsearch(
                index="stripe_subscriptions", query=query_start
            )
            active_start_sub_ids = set()
            mrr_at_start = 0.0

            for hit in subs_start:
                sub_data = hit["_source"]["cleaned_data"]
                sub_id = sub_data.get("id")
                active_start_sub_ids.add(sub_id)
                # Calculate MRR for this subscription
                sub_mrr = 0.0
                items = sub_data.get("items", {}).get("data", [])
                for item in items:
                    plan = item.get("plan", {})
                    amount_cents = plan.get("amount", 0)
                    interval = plan.get("interval", "month")
                    interval_count = plan.get("interval_count", 1)
                    quantity = item.get("quantity", 1)
                    base_amount = amount_cents * quantity
                    if interval == "day":
                        monthly_amount = (base_amount * 30) / interval_count  # 30-day month
                    elif interval == "week":
                        monthly_amount = (base_amount * 4) / interval_count  # 4-week month
                    elif interval == "month":
                        monthly_amount = base_amount / interval_count
                    elif interval == "year":
                        monthly_amount = (base_amount / 12) / interval_count
                    else:
                        monthly_amount = 0
                    sub_mrr += monthly_amount
                discount = sub_data.get("discount")
                if discount:
                    coupon = discount.get("coupon", {})
                    if "percent_off" in coupon and coupon["percent_off"]:
                        percent_off = coupon["percent_off"] / 100.0
                        sub_mrr = sub_mrr * (1 - percent_off)
                    elif "amount_off" in coupon and coupon["amount_off"]:
                        amount_off = coupon["amount_off"]
                        duration = coupon.get("duration")
                        if duration in ["forever", "repeating"]:
                            sub_mrr = max(0, sub_mrr - amount_off)
                mrr_at_start += sub_mrr

            # Get canceled subscriptions in period that were active at start
            filters_churned = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "canceled"}},
                {
                    "range": {
                        "cleaned_data.canceled_at": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]
            subs_churned = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters_churned
            )
            churned_mrr = 0.0
            for hit in subs_churned:
                sub_data = hit["_source"]["cleaned_data"]
                sub_id = sub_data.get("id")
                if sub_id not in active_start_sub_ids:
                    continue
                sub_mrr = 0.0
                items = sub_data.get("items", {}).get("data", [])
                for item in items:
                    plan = item.get("plan", {})
                    amount_cents = plan.get("amount", 0)
                    interval = plan.get("interval", "month")
                    interval_count = plan.get("interval_count", 1)
                    quantity = item.get("quantity", 1)
                    base_amount = amount_cents * quantity
                    if interval == "day":
                        monthly_amount = (base_amount * 30) / interval_count  # 30-day month
                    elif interval == "week":
                        monthly_amount = (base_amount * 4) / interval_count  # 4-week month
                    elif interval == "month":
                        monthly_amount = base_amount / interval_count
                    elif interval == "year":
                        monthly_amount = (base_amount / 12) / interval_count
                    else:
                        monthly_amount = 0
                    sub_mrr += monthly_amount
                discount = sub_data.get("discount")
                if discount:
                    coupon = discount.get("coupon", {})
                    if "percent_off" in coupon and coupon["percent_off"]:
                        percent_off = coupon["percent_off"] / 100.0
                        sub_mrr = sub_mrr * (1 - percent_off)
                    elif "amount_off" in coupon and coupon["amount_off"]:
                        amount_off = coupon["amount_off"]
                        duration = coupon.get("duration")
                        if duration in ["forever", "repeating"]:
                            sub_mrr = max(0, sub_mrr - amount_off)
                churned_mrr += sub_mrr

            if mrr_at_start == 0:
                logger.info("Revenue Churn Rate (%):", 0.0)
                return 0.0

            revenue_churn_rate = churned_mrr / mrr_at_start
            result = round(revenue_churn_rate * 100, 2)
            logger.info(f"Revenue Churn Rate (%): {result}")
            return result

        except Exception as e:
            logger.error(f"Errorcalculating revenue churn rate: {str(e)}")
            return 0.0


    def calculate_customer_retension_rate(
        self, project_id: str, start_date: str, end_date: str
    ) -> float:
        """
        Calculate Customer Retension Rate, calculation : 100 - Churn rate.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: retension rate as a percentage
        """
        try:
            churn_rate = self.calculate_churn_rate(project_id, start_date, end_date)
            retension_rate = 100 - churn_rate
            result = round(retension_rate, 2)
            logger.info(f"Retension Rate (%): {result}")
            return result
        except Exception as e:
            logger.error(f"Errorcalculating retension rate: {str(e)}")
            return 0.0


    def calculate_customer_ltv(self, project_id: str, start_date: str, end_date: str) -> float:
        """
        Calculate Customer Lifetime Value (LTV) = ARPU / Churn Rate.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: LTV calculation result
        """
        try:
            arpu = self.calculate_arpu(project_id)
            churn_rate = self.calculate_churn_rate(project_id, start_date, end_date)
            if churn_rate == 0:
                return 0.0
            ltv = arpu / (churn_rate / 100)
            result = round(ltv, 2)
            logger.info(f"Lifetime Value (LTV): {result}")
            return result
        except Exception as e:
            logger.error(f"Errorcalculating LTV: {str(e)}")
            return 0.0


    def calculate_expansion_mrr(self, project_id: str, start_date: str, end_date: str) -> float:
        """
        Calculate Expansion MRR - Extra MRR gained from existing customers upgrading.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Expansion MRR calculation result
        """
        try:
            # Convert dates to timestamps
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            # Get subscription change events during the period
            filters = [
                {"term": {"project_id": project_id}},
                {
                    "terms": {
                        "cleaned_data.type": [
                            "customer.subscription.updated",
                            "invoice.payment_succeeded",
                        ]
                    }
                },
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]

            events = self._query_elasticsearch(index="stripe_events", filters=filters)

            # Track MRR changes per customer
            customer_mrr_changes = {}

            for event_hit in events:
                event_data = event_hit["_source"]["cleaned_data"]
                event_type = event_data.get("type")

                if event_type == "customer.subscription.updated":
                    subscription_data = event_data.get("data", {}).get("object", {})
                    customer_id = subscription_data.get("customer")

                    if customer_id:
                        # Calculate MRR difference (simplified approach)
                        current_mrr = self.calculate_subscription_mrr(subscription_data)

                        if customer_id not in customer_mrr_changes:
                            customer_mrr_changes[customer_id] = 0

                        # This is a simplified calculation - in reality you'd need to track
                        # the previous MRR value to get the exact difference
                        customer_mrr_changes[customer_id] = current_mrr

            # Sum positive changes (expansions)
            expansion_mrr = sum(
                change for change in customer_mrr_changes.values() if change > 0
            )

            result = round(expansion_mrr, 2)
            logger.info(f"Expansion MRR: {result}")
            return result

        except Exception as e:
            logger.error(f"Errorcalculating Expansion MRR: {str(e)}")
            return 0.0


    def calculate_contraction_mrr(self, project_id: str, start_date: str, end_date: str) -> float:
        """
        Calculate Contraction MRR - MRR lost from downgrades (not churn).

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Contraction MRR calculation result (positive number representing loss)
        """
        try:
            # Convert dates to timestamps
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            # Get subscription change events during the period
            filters = [
                {"term": {"project_id": project_id}},
                {"terms": {"cleaned_data.type": ["customer.subscription.updated"]}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]

            events = self._query_elasticsearch(index="stripe_events", filters=filters)

            # Track MRR changes per customer
            customer_mrr_changes = {}

            for event_hit in events:
                event_data = event_hit["_source"]["cleaned_data"]
                subscription_data = event_data.get("data", {}).get("object", {})
                customer_id = subscription_data.get("customer")

                if customer_id:
                    # Calculate MRR difference (simplified approach)
                    current_mrr = self.calculate_subscription_mrr(subscription_data)

                    if customer_id not in customer_mrr_changes:
                        customer_mrr_changes[customer_id] = 0

                    # This is a simplified calculation - in reality you'd need to track
                    # the previous MRR value to get the exact difference
                    customer_mrr_changes[customer_id] = current_mrr

            # Sum negative changes (contractions) - return as positive number
            contraction_mrr = abs(
                sum(change for change in customer_mrr_changes.values() if change < 0)
            )

            result = round(contraction_mrr, 2)
            logger.info(f"Contraction MRR: {result}")
            return result

        except Exception as e:
            logger.error(f"Errorcalculating Contraction MRR: {str(e)}")
            return 0.0


    def calculate_new_customer_mrr(
        self, project_id: str, start_date: str, end_date: str
    ) -> float:
        """
        Calculate MRR from new customers acquired in the period.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: New customer MRR
        """
        try:
            # Convert dates to timestamps
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            # Get new subscriptions created in the period
            filters = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "active"}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]

            new_subscriptions = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters
            )

            new_customer_mrr = 0.0

            for sub_hit in new_subscriptions:
                sub_data = sub_hit["_source"]["cleaned_data"]
                sub_mrr = self.calculate_subscription_mrr(sub_data)
                new_customer_mrr += sub_mrr

            result = round(new_customer_mrr, 2)
            return result

        except Exception as e:
            logger.error(f"Errorcalculating new customer MRR: {str(e)}")
            return 0.0


    def calculate_churned_mrr(self, project_id: str, start_date: str, end_date: str) -> float:
        """
        Calculate MRR lost from churned customers in the period.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Churned MRR (positive number representing loss)
        """
        try:
            # Convert dates to timestamps
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            # Get churned subscriptions in the period
            filters = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "canceled"}},
                {
                    "range": {
                        "cleaned_data.canceled_at": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]

            churned_subscriptions = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters
            )

            churned_mrr = 0.0

            for sub_hit in churned_subscriptions:
                sub_data = sub_hit["_source"]["cleaned_data"]
                sub_mrr = self.calculate_subscription_mrr(sub_data)
                churned_mrr += sub_mrr

            result = round(churned_mrr, 2)
            return result

        except Exception as e:
            logger.error(f"Errorcalculating churned MRR: {str(e)}")
            return 0.0


    def calculate_net_new_mrr(self, project_id: str, start_date: str, end_date: str) -> float:
        """
        Calculate Net New MRR = New MRR + Expansion MRR - Contraction MRR - Churned MRR.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Net New MRR calculation result
        """
        try:
            new_mrr = self.calculate_new_customer_mrr(project_id, start_date, end_date)
            expansion_mrr = self.calculate_expansion_mrr(project_id, start_date, end_date)
            contraction_mrr = self.calculate_contraction_mrr(project_id, start_date, end_date)
            churned_mrr = self.calculate_churned_mrr(project_id, start_date, end_date)

            net_new_mrr = new_mrr + expansion_mrr - contraction_mrr - churned_mrr

            result = round(net_new_mrr, 2)
            logger.info(
                f"Net New MRR: {result} (New: {new_mrr}, Expansion: {expansion_mrr}, Contraction: -{contraction_mrr}, Churned: -{churned_mrr})"
            )
            return result

        except Exception as e:
            logger.error(f"Errorcalculating Net New MRR: {str(e)}")
            return 0.0


    def calculate_subscription_mrr(self, subscription_data: dict) -> float:
        """
        Helper function to calculate MRR for a single subscription.

        Args:
            subscription_data: Subscription data from Stripe

        Returns:
            float: Monthly recurring revenue for the subscription
        """
        try:
            sub_mrr = 0.0
            items = subscription_data.get("items", {}).get("data", [])

            for item in items:
                plan = item.get("plan", {})
                amount = plan.get("amount", 0)
                interval = plan.get("interval", "month")
                interval_count = plan.get("interval_count", 1)
                quantity = item.get("quantity", 1)

                # Base amount
                base_amount = amount * quantity

                # Normalize to monthly
                if interval == "day":
                    monthly_amount = (base_amount * 30) / interval_count  # 30-day month
                elif interval == "week":
                    monthly_amount = (base_amount * 4) / interval_count  # 4-week month
                elif interval == "month":
                    monthly_amount = base_amount / interval_count
                elif interval == "year":
                    monthly_amount = (base_amount / 12) / interval_count
                else:
                    monthly_amount = 0

                sub_mrr += monthly_amount

            # Apply subscription-level discounts
            discount = subscription_data.get("discount")
            if discount:
                coupon = discount.get("coupon", {})
                if "percent_off" in coupon and coupon["percent_off"]:
                    percent_off = coupon["percent_off"] / 100.0
                    sub_mrr = sub_mrr * (1 - percent_off)
                elif "amount_off" in coupon and coupon["amount_off"]:
                    amount_off = coupon["amount_off"]
                    duration = coupon.get("duration")
                    if duration in ["forever", "repeating"]:
                        sub_mrr = max(0, sub_mrr - amount_off)

            return sub_mrr

        except Exception as e:
            logger.error(f"Errorcalculating subscription MRR: {str(e)}")
            return 0.0


    def calculate_net_revenue_retention(
        self, project_id: str, start_date: str, end_date: str
    ) -> float:
        """
        Calculate Net Revenue Retention (NRR).
        NRR = (Starting MRR + Expansion MRR - Churned MRR) / Starting MRR * 100

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Net Revenue Retention as a percentage
        """
        try:
            # Convert dates to timestamps
            start_timestamp = self.convert_date_to_timestamp(start_date)

            # Get active subscriptions at start of period
            filters_start = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "active"}},
                {"range": {"cleaned_data.created": {"lte": start_timestamp}}},
            ]
            subs_start = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters_start
            )
            starting_mrr = 0.0
            for hit in subs_start:
                sub_data = hit["_source"]["cleaned_data"]
                starting_mrr += self.calculate_subscription_mrr(sub_data)

            expansion_mrr = self.calculate_expansion_mrr(project_id, start_date, end_date)
            churned_mrr = self.calculate_churned_mrr(project_id, start_date, end_date)

            if starting_mrr == 0:
                return 0.0

            nrr = (starting_mrr + expansion_mrr - churned_mrr) / starting_mrr * 100
            result = round(nrr, 2)
            logger.info(f"Net Revenue Retention (NRR %): {result}")
            return result

        except Exception as e:
            logger.error(f"Errorcalculating Net Revenue Retention: {str(e)}")
            return 0.0


    def calculate_gross_revenue_retention(
        self, project_id: str, start_date: str, end_date: str
    ) -> float:
        """
        Calculate Gross Revenue Retention (GRR).
        GRR = (Starting MRR - Churned MRR) / Starting MRR * 100

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Gross Revenue Retention as a percentage
        """
        try:
            # Convert dates to timestamps
            start_timestamp = self.convert_date_to_timestamp(start_date)

            # Get active subscriptions at start of period
            filters_start = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "active"}},
                {"range": {"cleaned_data.created": {"lte": start_timestamp}}},
            ]
            subs_start = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters_start
            )
            starting_mrr = 0.0
            for hit in subs_start:
                sub_data = hit["_source"]["cleaned_data"]
                starting_mrr += self.calculate_subscription_mrr(sub_data)

            churned_mrr = self.calculate_churned_mrr(project_id, start_date, end_date)

            if starting_mrr == 0:
                return 0.0

            grr = (starting_mrr - churned_mrr) / starting_mrr * 100
            result = round(grr, 2)
            logger.info(f"Gross Revenue Retention (GRR %): {result}")
            return result

        except Exception as e:
            logger.error(f"Errorcalculating Gross Revenue Retention: {str(e)}")
            return 0.0


    def calculate_cohort_retention_rate(
        self,
        project_id: str,
        cohort_start_date: str,
        cohort_end_date: str,
        period_end_date: str,
    ) -> float:
        """
        Calculate Cohort Retention Rate (% of a customer group acquired in the same period).
        Retention Rate = Active customers in period_end_date / original cohort size

        Args:
            project_id: The project identifier
            cohort_start_date: Cohort acquisition start date (ISO format: 'YYYY-MM-DD')
            cohort_end_date: Cohort acquisition end date (ISO format: 'YYYY-MM-DD')
            period_end_date: Date to measure retention (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Cohort retention rate as a percentage
        """
        try:
            # Convert dates to timestamps
            cohort_start_ts = self.convert_date_to_timestamp(cohort_start_date)
            cohort_end_ts = self.convert_date_to_timestamp(cohort_end_date)
            period_end_ts = self.convert_date_to_timestamp(period_end_date)

            # Find cohort: customers who started ACTIVE subscriptions in cohort period
            filters_cohort = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": cohort_start_ts,
                            "lte": cohort_end_ts,
                        }
                    }
                },
            ]
            cohort_subs = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters_cohort
            )
            cohort_customer_ids = set()
            for hit in cohort_subs:
                customer_id = hit["_source"]["cleaned_data"].get("customer")
                if customer_id:
                    cohort_customer_ids.add(customer_id)
            cohort_size = len(cohort_customer_ids)
            if cohort_size == 0:
                return 0.0

            # Find which cohort customers are still active at period_end_date
            filters_active = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "active"}},
                {"range": {"cleaned_data.created": {"lte": period_end_ts}}},
            ]
            active_subs = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters_active
            )
            active_customer_ids = set()
            for hit in active_subs:
                customer_id = hit["_source"]["cleaned_data"].get("customer")
                if customer_id and customer_id in cohort_customer_ids:
                    active_customer_ids.add(customer_id)
            retained_count = len(active_customer_ids)

            retention_rate = retained_count / cohort_size * 100
            result = round(retention_rate, 2)
            logger.info(f"Cohort Retention Rate (%): {result}")
            return result

        except Exception as e:
            logger.error(f"Errorcalculating Cohort Retention Rate: {str(e)}")
            return 0.0


    def calculate_logo_churn(self, project_id: str, start_date: str, end_date: str) -> int:
        """
        Calculate Logo Churn (Number of customer accounts lost).
        Count of distinct customers that cancelled in the period.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            int: Number of distinct customers that cancelled
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)
            filters = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "canceled"}},
                {
                    "range": {
                        "cleaned_data.canceled_at": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]
            canceled_subs = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters
            )
            canceled_customers = set()
            for hit in canceled_subs:
                customer_id = hit["_source"]["cleaned_data"].get("customer")
                if customer_id:
                    canceled_customers.add(customer_id)
            result = len(canceled_customers)
            logger.info(f"Logo Churn (customer accounts lost): {result}")
            return result
        except Exception as e:
            logger.error(f"Errorcalculating Logo Churn: {str(e)}")
            return 0


    def calculate_mrr_growth_rate(
        self,
        project_id: str,
        prev_month_start: str = "",
        prev_month_end: str = "",
        curr_month_start: str = "",
        curr_month_end: str = "",
    ) -> float:
        """
        Calculate MRR Growth Rate (Month-over-month growth of MRR).

        Args:
            project_id: The project identifier
            prev_month_start: Previous month start date (ISO format: 'YYYY-MM-DD')
            prev_month_end: Previous month end date (ISO format: 'YYYY-MM-DD')
            curr_month_start: Current month start date (ISO format: 'YYYY-MM-DD')
            curr_month_end: Current month end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: MRR Growth Rate as a percentage
        """
        try:
            # If any date is missing, use last 6 months
            if not (
                prev_month_start and prev_month_end and curr_month_start and curr_month_end
            ):
                today = datetime.today()
                curr_month_start_dt = today.replace(day=1)
                curr_month_end_dt = today
                prev_month_end_dt = curr_month_start_dt - timedelta(days=1)
                prev_month_start_dt = prev_month_end_dt.replace(day=1)
                prev_month_start = (
                    prev_month_start_dt - timedelta(days=prev_month_start_dt.day - 1)
                ).strftime("%Y-%m-%d")
                prev_month_end = prev_month_end_dt.strftime("%Y-%m-%d")
                curr_month_start = curr_month_start_dt.strftime("%Y-%m-%d")
                curr_month_end = curr_month_end_dt.strftime("%Y-%m-%d")

            # Get MRR at end of previous month
            prev_mrr_filters = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "active"}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "lte": self.convert_date_to_timestamp(prev_month_end)
                        }
                    }
                },
            ]
            prev_subs = self._query_elasticsearch(
                index="stripe_subscriptions", filters=prev_mrr_filters
            )
            prev_mrr = sum(
                [
                    self.calculate_subscription_mrr(hit["_source"]["cleaned_data"])
                    for hit in prev_subs
                ]
            )

            # Get MRR at end of current month
            curr_mrr_filters = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "active"}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "lte": self.convert_date_to_timestamp(curr_month_end)
                        }
                    }
                },
            ]
            curr_subs = self._query_elasticsearch(
                index="stripe_subscriptions", filters=curr_mrr_filters
            )
            curr_mrr = sum(
                [
                    self.calculate_subscription_mrr(hit["_source"]["cleaned_data"])
                    for hit in curr_subs
                ]
            )

            if prev_mrr == 0:
                return 0.0

            growth_rate = ((curr_mrr - prev_mrr) / prev_mrr) * 100
            result = round(growth_rate, 2)
            logger.info(f"MRR Growth Rate (%): {result}")
            return result
        except Exception as e:
            logger.error(f"Errorcalculating MRR Growth Rate: {str(e)}")
            return 0.0


    def calculate_gross_payment_volume(
        self, project_id: str, start_date: str, end_date: str
    ) -> float:
        """
        Calculate Gross Payment Volume (GPV) - Total processed volume from all invoices.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Gross Payment Volume (sum of all invoice amounts)
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)
            filters = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]
            invoices = self._query_elasticsearch(
                index="stripe_invoices", filters=filters
            )
            total_volume = 0.0
            for hit in invoices:
                invoice_data = hit["_source"]["cleaned_data"]
                amount_paid = invoice_data.get("amount_paid", 0)
                total_volume += amount_paid
            result = round(total_volume, 2)
            logger.info(f"Gross Payment Volume (GPV): {result}")
            return result
        except Exception as e:
            logger.error(f"Errorcalculating Gross Payment Volume: {str(e)}")
            return 0.0


    def calculate_refund_rate(self, project_id: str, start_date: str, end_date: str) -> float:
        """
        Calculate Refund Rate (% of payments refunded).

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Refund Rate as a percentage
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)
            filters = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]
            invoices = self._query_elasticsearch(
                index="stripe_invoices", filters=filters
            )
            total_paid = 0.0
            total_refunded = 0.0
            for hit in invoices:
                invoice_data = hit["_source"]["cleaned_data"]
                amount_paid = invoice_data.get("amount_paid", 0)
                amount_refunded = invoice_data.get("amount_refunded", 0)
                total_paid += amount_paid
                total_refunded += amount_refunded
            if total_paid == 0:
                return 0.0
            refund_rate = (total_refunded / total_paid) * 100
            result = round(refund_rate, 2)
            logger.info(f"Refund Rate (%): {result}")
            return result
        except Exception as e:
            logger.error(f"Errorcalculating Refund Rate: {str(e)}")
            return 0.0


    def calculate_failed_payment_rate(
        self, project_id: str, start_date: str, end_date: str
    ) -> float:
        """
        Calculate Failed Payment Rate (% of invoices unpaid due to failed payment).

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Failed Payment Rate as a percentage
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)
            filters = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]
            invoices = self._query_elasticsearch(
                index="stripe_invoices", filters=filters
            )
            total_invoices = 0
            failed_invoices = 0
            for hit in invoices:
                invoice_data = hit["_source"]["cleaned_data"]
                status = invoice_data.get("status", "")
                total_invoices += 1
                if status == "unpaid":
                    failed_invoices += 1
            if total_invoices == 0:
                return 0.0
            failed_rate = (failed_invoices / total_invoices) * 100
            result = round(failed_rate, 2)
            logger.info(f"Failed Payment Rate (%): {result}")
            return result
        except Exception as e:
            logger.error(f"Errorcalculating Failed Payment Rate: {str(e)}")
            return 0.0


    def calculate_average_invoice_value(
        self, project_id: str, start_date: str, end_date: str
    ) -> float:
        """
        Calculate Average Invoice Value (AIV) - Average size of each paid invoice.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Average Invoice Value
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)
            filters = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "paid"}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]
            invoices = self._query_elasticsearch(
                index="stripe_invoices", filters=filters
            )
            total_paid = 0.0
            paid_invoice_count = 0
            for hit in invoices:
                invoice_data = hit["_source"]["cleaned_data"]
                amount_paid = invoice_data.get("amount_paid", 0)
                total_paid += amount_paid
                paid_invoice_count += 1
            if paid_invoice_count == 0:
                return 0.0
            average_value = total_paid / paid_invoice_count
            result = round(average_value, 2)
            logger.info(f"Average Invoice Value: {result}")
            return result
        except Exception as e:
            logger.error(f"Errorcalculating Average Invoice Value: {str(e)}")
            return 0.0


    def calculate_quick_ratio(self, project_id: str, start_date: str, end_date: str) -> float:
        """
        Calculate Quick Ratio = (New MRR + Expansion MRR) / (Churned MRR + Contraction MRR)

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            float: Quick Ratio
        """
        try:
            new_mrr = self.calculate_new_customer_mrr(project_id, start_date, end_date)
            expansion_mrr = self.calculate_expansion_mrr(project_id, start_date, end_date)
            churned_mrr = self.calculate_churned_mrr(project_id, start_date, end_date)
            contraction_mrr = self.calculate_contraction_mrr(project_id, start_date, end_date)

            denominator = churned_mrr + contraction_mrr
            if denominator == 0:
                return 0.0

            quick_ratio = (new_mrr + expansion_mrr) / denominator
            result = round(quick_ratio, 2)
            logger.info(f"Quick Ratio: {result}")
            return result
        except Exception as e:
            logger.error(f"Errorcalculating Quick Ratio: {str(e)}")
            return 0.0


    def calculate_revenue_per_plan(self, project_id: str, start_date: str, end_date: str) -> dict:
        """
        Calculate Revenue per Plan by grouping active subscriptions by plan.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            dict: {plan_id: total_revenue}
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            filters_start = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]

            query_start = {
                "bool": {
                    "filter": filters_start,
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "cleaned_data.ended_at"}}
                            }
                        },
                        {"range": {"cleaned_data.ended_at": {"gte": end_timestamp}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

            subscriptions = self._query_elasticsearch(
                index="stripe_subscriptions", query=query_start
            )

            # Collect all unique product IDs first
            product_ids = set()
            for hit in subscriptions:
                sub_data = hit["_source"]["cleaned_data"]
                items = sub_data.get("items", {}).get("data", [])
                for item in items:
                    plan = item.get("plan", {})
                    product_id = plan.get("product", "")
                    if product_id:
                        product_ids.add(product_id)

            # Batch query all products
            products_cache = {}
            if product_ids:
                try:
                    product_filters = [
                        {"term": {"project_id": project_id}},
                        {"terms": {"product_id": list(product_ids)}},
                    ]

                    product_docs = self._query_elasticsearch(
                        index="stripe_products",
                        filters=product_filters,
                    )

                    # Build products cache
                    for doc in product_docs:
                        product_data = doc["_source"].get("cleaned_data", {})
                        product_id = doc["_source"].get("product_id")
                        if product_id:
                            products_cache[product_id] = product_data.get(
                                "name", product_id
                            )

                except Exception as e:
                    logger.error(f"Errorbatch querying products: {str(e)}")

            revenue_by_plan = {}

            for hit in subscriptions:
                sub_data = hit["_source"]["cleaned_data"]
                items = sub_data.get("items", {}).get("data", [])

                for item in items:
                    plan = item.get("plan", {})
                    plan_id = plan.get("id")
                    product_id = plan.get("product", "")

                    # Get product name from cache
                    product_name = products_cache.get(product_id, plan_id)

                    amount_cents = plan.get("amount", 0)
                    interval = plan.get("interval", "month")
                    interval_count = plan.get("interval_count", 1)
                    quantity = item.get("quantity", 1)

                    base_amount = amount_cents * quantity

                    # Normalize to monthly
                    if interval == "day":
                        monthly_amount = (base_amount * 30) / interval_count  # 30-day month
                    elif interval == "week":
                        monthly_amount = (base_amount * 4) / interval_count  # 4-week month
                    elif interval == "month":
                        monthly_amount = base_amount / interval_count
                    elif interval == "year":
                        monthly_amount = (base_amount / 12) / interval_count
                    else:
                        monthly_amount = 0

                    # Apply subscription-level discounts
                    discount = sub_data.get("discount")
                    if discount:
                        coupon = discount.get("coupon", {})
                        if "percent_off" in coupon and coupon["percent_off"]:
                            percent_off = coupon["percent_off"] / 100.0
                            monthly_amount = monthly_amount * (1 - percent_off)
                        elif "amount_off" in coupon and coupon["amount_off"]:
                            amount_off = coupon["amount_off"]
                            duration = coupon.get("duration")
                            if duration in ["forever", "repeating"]:
                                monthly_amount = max(0, monthly_amount - amount_off)

                    if plan_id:
                        if plan_id not in revenue_by_plan:
                            revenue_by_plan[plan_id] = {
                                "plan_name": product_name,
                                "monthly_revenue": 0.0,
                                "currency": plan.get("currency", "usd"),
                                "interval": interval,
                                "interval_count": interval_count,
                            }

                        revenue_by_plan[plan_id]["monthly_revenue"] += monthly_amount

            # Round values
            for plan_id in revenue_by_plan:
                revenue_by_plan[plan_id]["monthly_revenue"] = round(
                    revenue_by_plan[plan_id]["monthly_revenue"], 2
                )

            logger.info(f"Revenue per Plan (optimized): {revenue_by_plan}")
            return revenue_by_plan
        except Exception as e:
            logger.error(f"Errorcalculating Revenue per Plan from subscriptions: {str(e)}")
            return {}


    def calculate_plan_mix(self, project_id: str, start_date: str, end_date: str) -> dict:
        """
        Calculate Plan Mix (% of revenue by plan type).

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            dict: {plan_id: {"plan_name": str, "mix_percent": float}}
        """
        try:
            revenue_by_plan = self.calculate_revenue_per_plan(project_id, start_date, end_date)
            total_revenue = sum(
                plan_info["monthly_revenue"] for plan_info in revenue_by_plan.values()
            )
            if total_revenue == 0:
                return {}

            plan_mix = {}
            for plan_id, plan_info in revenue_by_plan.items():
                mix_percent = (plan_info["monthly_revenue"] / total_revenue) * 100
                plan_mix[plan_id] = {
                    "plan_name": plan_info["plan_name"],
                    "mix_percent": round(mix_percent, 2),
                }
            logger.info(f"Plan Mix (% of revenue by plan): {plan_mix}")
            return plan_mix
        except Exception as e:
            logger.error(f"Errorcalculating Plan Mix: {str(e)}")
            return {}


    def get_active_customers_at_start(self, project_id: str, start_timestamp: int) -> set:
        """
        Helper function to get all customers who had active subscriptions at the start of the period

        Args:
            project_id: Project identifier
            start_timestamp: Timestamp at start of analysis period

        Returns:
            set: Customer IDs who were active at start
        """
        # Get subscriptions that were active at the start of the period
        filters_start = [
            {"term": {"project_id": project_id}},
            {"range": {"cleaned_data.created": {"lt": start_timestamp}}},
        ]

        query_start = {
            "bool": {
                "filter": filters_start,
                "should": [
                    {"bool": {"must_not": {"exists": {"field": "cleaned_data.ended_at"}}}},
                    {"range": {"cleaned_data.ended_at": {"gte": start_timestamp}}},
                ],
                "minimum_should_match": 1,
            }
        }

        subscriptions = self._query_elasticsearch(
            index="stripe_subscriptions", query=query_start
        )

        active_customers = set()
        for hit in subscriptions:
            sub_data = hit["_source"]["cleaned_data"]
            customer_id = sub_data.get("customer")
            if customer_id:
                active_customers.add(customer_id)

        return list(active_customers)


    def calculate_upgrade_rate(self, project_id: str, start_date: str, end_date: str) -> dict:
        """
        Calculate Upgrade Rate - % of Active Customers who upgraded

        Args:
            project_id: Project identifier
            start_date: Start date for analysis period
            end_date: End date for analysis period

        Returns:
            dict: Upgrade rate analysis with details
        """
        start_timestamp = self.convert_date_to_timestamp(start_date)
        end_timestamp = self.convert_date_to_timestamp(end_date)

        # Get all active customers at the start of the period
        active_customers = self.get_active_customers_at_start(project_id, start_timestamp)

        if not active_customers:
            return {
                "upgrade_rate": 0.0,
                "total_active_customers": 0,
                "upgraded_customers": 0,
                "upgrade_details": [],
            }

        # Find upgrades during the period using events
        upgrade_filters = [
            {"term": {"project_id": project_id}},
            {"terms": {"cleaned_data.type": ["customer.subscription.updated"]}},
            {
                "range": {
                    "cleaned_data.created": {
                        "gte": start_timestamp,
                        "lte": end_timestamp,
                    }
                }
            },
        ]

        upgrade_events = self._query_elasticsearch(
            index="stripe_events", filters=upgrade_filters
        )

        upgraded_customers = set()
        upgrade_details = []

        for hit in upgrade_events:
            event_data = hit["_source"]["cleaned_data"]

            # Get subscription data from event
            subscription_data = event_data.get("data", {}).get("object", {})
            customer_id = subscription_data.get("customer")

            # Skip if not an active customer at start
            if customer_id not in active_customers:
                continue

            # Get previous attributes to compare
            previous_attributes = event_data.get("data", {}).get("previous_attributes", {})

            # Check for plan/price changes indicating upgrade
            current_items = subscription_data.get("items", {}).get("data", [])

            if "items" in previous_attributes:
                prev_items = previous_attributes["items"]["data"]

                # Compare plan amounts to detect upgrades
                for curr_item, prev_item in zip(current_items, prev_items):
                    curr_plan = curr_item.get("plan", {}) or curr_item.get("price", {})
                    prev_plan = prev_item.get("plan", {}) or prev_item.get("price", {})

                    curr_amount = curr_plan.get("amount", 0) or curr_plan.get(
                        "unit_amount", 0
                    )
                    prev_amount = prev_plan.get("amount", 0) or prev_plan.get(
                        "unit_amount", 0
                    )

                    curr_quantity = curr_item.get("quantity", 1)
                    prev_quantity = prev_item.get("quantity", 1)

                    # Calculate total amounts
                    curr_total = curr_amount * curr_quantity
                    prev_total = prev_amount * prev_quantity

                    # If current amount is higher, it's an upgrade
                    if curr_total > prev_total:
                        upgraded_customers.add(customer_id)

                        upgrade_details.append(
                            {
                                "customer_id": customer_id,
                                "event_date": event_data.get("created"),
                                "previous_amount": prev_total,
                                "new_amount": curr_total,
                                "amount_increase": curr_total - prev_total,
                                "previous_plan_id": prev_plan.get("id"),
                                "new_plan_id": curr_plan.get("id"),
                            }
                        )
                        break

        total_active = len(active_customers)
        upgraded_count = len(upgraded_customers)
        upgrade_rate = (upgraded_count / total_active * 100) if total_active > 0 else 0.0

        result = {
            "upgrade_rate": round(upgrade_rate, 2),
            "total_active_customers": total_active,
            "upgraded_customers": upgraded_count,
            "upgrade_details": upgrade_details[:10],  # Limit to first 10 for readability
            "period": f"{start_date} to {end_date}",
        }

        logger.info(f"Upgrade Rate Analysis:")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Active Customers: {total_active}")
        logger.info(f"Upgraded Customers: {upgraded_count}")
        logger.info(f"Upgrade Rate: {upgrade_rate}%")

        return result


    def calculate_downgrade_rate(self, project_id: str, start_date: str, end_date: str) -> dict:
        """
        Calculate Downgrade Rate - % of Active Customers who downgraded

        Args:
            project_id: Project identifier
            start_date: Start date for analysis period
            end_date: End date for analysis period

        Returns:
            dict: Downgrade rate analysis with details
        """
        start_timestamp = self.convert_date_to_timestamp(start_date)
        end_timestamp = self.convert_date_to_timestamp(end_date)

        # Get all active customers at the start of the period
        active_customers = self.get_active_customers_at_start(project_id, start_timestamp)

        if not active_customers:
            return {
                "downgrade_rate": 0.0,
                "total_active_customers": 0,
                "downgraded_customers": 0,
                "downgrade_details": [],
            }

        # Find downgrades during the period using events
        downgrade_filters = [
            {"term": {"project_id": project_id}},
            {"terms": {"cleaned_data.type": ["customer.subscription.updated"]}},
            {
                "range": {
                    "cleaned_data.created": {
                        "gte": start_timestamp,
                        "lte": end_timestamp,
                    }
                }
            },
        ]

        downgrade_events = self._query_elasticsearch(
            index="stripe_events", filters=downgrade_filters
        )

        downgraded_customers = set()
        downgrade_details = []

        for hit in downgrade_events:
            event_data = hit["_source"]["cleaned_data"]

            # Get subscription data from event
            subscription_data = event_data.get("data", {}).get("object", {})
            customer_id = subscription_data.get("customer")

            # Skip if not an active customer at start
            if customer_id not in active_customers:
                continue

            # Get previous attributes to compare
            previous_attributes = event_data.get("data", {}).get("previous_attributes", {})

            # Check for plan/price changes indicating downgrade
            current_items = subscription_data.get("items", {}).get("data", [])

            if "items" in previous_attributes:
                prev_items = previous_attributes["items"]["data"]

                # Compare plan amounts to detect downgrades
                for curr_item, prev_item in zip(current_items, prev_items):
                    curr_plan = curr_item.get("plan", {}) or curr_item.get("price", {})
                    prev_plan = prev_item.get("plan", {}) or prev_item.get("price", {})

                    curr_amount = curr_plan.get("amount", 0) or curr_plan.get(
                        "unit_amount", 0
                    )
                    prev_amount = prev_plan.get("amount", 0) or prev_plan.get(
                        "unit_amount", 0
                    )

                    curr_quantity = curr_item.get("quantity", 1)
                    prev_quantity = prev_item.get("quantity", 1)

                    # Calculate total amounts
                    curr_total = curr_amount * curr_quantity
                    prev_total = prev_amount * prev_quantity

                    # If current amount is lower, it's a downgrade
                    if curr_total < prev_total:
                        downgraded_customers.add(customer_id)

                        downgrade_details.append(
                            {
                                "customer_id": customer_id,
                                "event_date": event_data.get("created"),
                                "previous_amount": prev_total,
                                "new_amount": curr_total,
                                "amount_decrease": prev_total - curr_total,
                                "previous_plan_id": prev_plan.get("id"),
                                "new_plan_id": curr_plan.get("id"),
                            }
                        )
                        break

        total_active = len(active_customers)
        downgraded_count = len(downgraded_customers)
        downgrade_rate = (
            (downgraded_count / total_active * 100) if total_active > 0 else 0.0
        )

        result = {
            "downgrade_rate": round(downgrade_rate, 2),
            "total_active_customers": total_active,
            "downgraded_customers": downgraded_count,
            "downgrade_details": downgrade_details[
                :10
            ],  # Limit to first 10 for readability
            "period": f"{start_date} to {end_date}",
        }

        logger.info(f"Downgrade Rate Analysis:")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Active Customers: {total_active}")
        logger.info(f"Downgraded Customers: {downgraded_count}")
        logger.info(f"Downgrade Rate: {downgrade_rate}%")

        return result


    def calculate_upgrade_downgrade_summary(
        self, project_id: str, start_date: str, end_date: str
    ) -> dict:
        """
        Get comprehensive upgrade/downgrade analysis

        Args:
            project_id: Project identifier
            start_date: Start date for analysis period
            end_date: End date for analysis period

        Returns:
            dict: Combined upgrade and downgrade metrics
        """
        upgrade_data = self.calculate_upgrade_rate(project_id, start_date, end_date)
        downgrade_data = self.calculate_downgrade_rate(project_id, start_date, end_date)

        # Calculate net upgrade rate (upgrades - downgrades)
        net_upgrade_rate = upgrade_data["upgrade_rate"] - downgrade_data["downgrade_rate"]

        summary = {
            "period": f"{start_date} to {end_date}",
            "total_active_customers": upgrade_data["total_active_customers"],
            "upgrade_metrics": {
                "upgrade_rate": upgrade_data["upgrade_rate"],
                "upgraded_customers": upgrade_data["upgraded_customers"],
            },
            "downgrade_metrics": {
                "downgrade_rate": downgrade_data["downgrade_rate"],
                "downgraded_customers": downgrade_data["downgraded_customers"],
            },
            "net_metrics": {
                "net_upgrade_rate": round(net_upgrade_rate, 2),
                "net_customer_movement": upgrade_data["upgraded_customers"]
                - downgrade_data["downgraded_customers"],
                "movement_direction": (
                    "Positive"
                    if net_upgrade_rate > 0
                    else "Negative"
                    if net_upgrade_rate < 0
                    else "Neutral"
                ),
            },
        }

        logger.info(f"\nUpgrade/Downgrade Summary:")
        logger.info(f"Upgrade Rate: {upgrade_data['upgrade_rate']}%")
        logger.info(f"Downgrade Rate: {downgrade_data['downgrade_rate']}%")
        logger.info(f"Net Upgrade Rate: {net_upgrade_rate}%")
        logger.info(f"Movement Direction: {summary['net_metrics']['movement_direction']}")

        return summary


    def calculate_mrr_by_country(self, project_id: str, start_date: str, end_date: str) -> dict:
        """
        Calculate MRR by Country - Total MRR grouped by customer's billing country.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            dict: {
                total_mrr: sum of mrr_by_country values),
                total_countries: number of unique countries,),
                mrr_by_country: dict: {country_code: total_mrr},
                period: {start_date} to {end_date}
            }
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            # Step 1: Get all active subscriptions with their customer IDs
            filters_start = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]

            query_start = {
                "bool": {
                    "filter": filters_start,
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "cleaned_data.ended_at"}}
                            }
                        },
                        {"range": {"cleaned_data.ended_at": {"gte": end_timestamp}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

            subscriptions = self._query_elasticsearch(
                index="stripe_subscriptions", query=query_start
            )
            logger.info(f"Found {len(subscriptions)} active subscriptions in period.")

            if not subscriptions:
                return {}

            # Step 2: Extract customer IDs and calculate subscription MRR
            customer_ids = set()
            subscriptions_with_mrr = []

            for hit in subscriptions:
                sub_data = hit["_source"]["cleaned_data"]
                customer_id = sub_data.get("customer")
                if customer_id:
                    customer_ids.add(customer_id)
                    sub_mrr = self.calculate_subscription_mrr(sub_data)
                    subscriptions_with_mrr.append(
                        {"customer_id": customer_id, "mrr": sub_mrr}
                    )

            # Step 3: Batch get customer countries
            customer_filters = [
                {"term": {"project_id": project_id}},
                {"terms": {"customer_id": list(customer_ids)}},
            ]

            customers = self._query_elasticsearch(
                index="stripe_customers", filters=customer_filters
            )

            # Step 4: Create customer to country mapping
            customer_to_country = {}
            for hit in customers:
                customer_data = hit["_source"]["cleaned_data"]
                customer_id = hit["_source"].get("customer_id")
                # print ("customer_data: ",customer_data)

                country = (
                    customer_data.get("address", {}).get("country")
                    or customer_data.get("shipping", {}).get("address", {}).get("country")
                    or "Unknown"
                )

                customer_to_country[customer_id] = country

            # Step 5: Aggregate MRR by country
            mrr_by_country = {}
            for subscription in subscriptions_with_mrr:
                customer_id = subscription["customer_id"]
                mrr = subscription["mrr"]
                country = customer_to_country.get(customer_id, "Unknown")

                mrr_by_country[country] = mrr_by_country.get(country, 0.0) + mrr

            # Step 6: Format results
            for country in mrr_by_country:
                mrr_by_country[country] = round(mrr_by_country[country], 2)

            # Sort by MRR (descending)
            mrr_by_country = dict(
                sorted(mrr_by_country.items(), key=lambda x: x[1], reverse=True)
            )

            result = {
                "total_mrr": sum(mrr_by_country.values()),
                "total_countries": len(mrr_by_country),
                "mrr_by_country": mrr_by_country,
                "period": f"{start_date} to {end_date}",
            }

            logger.info(f"MRR by Country Analysis:")
            logger.info(f"Total Countries: {len(mrr_by_country)}")
            logger.info(f"Total MRR: ${sum(mrr_by_country.values())}")
            logger.info(
                f"Top Country: {list(mrr_by_country.keys())[0] if mrr_by_country else 'N/A'}"
            )

            return result

        except Exception as e:
            logger.error(f"Errorcalculating MRR by Country: {str(e)}")
            return {"error": str(e)}


    def calculate_active_customer_count_by_country(
        self, project_id: str, start_date: str, end_date: str
    ) -> dict:
        """
        Calculate Count of Active Customers by Country (customers with active subscriptions)

        Args:
            project_id: Project identifier
            start_date: Start date for analysis period
            end_date: End date for analysis period

        Returns:
            dict: Active customer count by country
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            # Get active subscriptions in the period
            filters_start = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]

            query_start = {
                "bool": {
                    "filter": filters_start,
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "cleaned_data.ended_at"}}
                            }
                        },
                        {"range": {"cleaned_data.ended_at": {"gte": end_timestamp}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

            subscriptions = self._query_elasticsearch(
                index="stripe_subscriptions", query=query_start
            )

            if not subscriptions:
                return {
                    "total_active_customers": 0,
                    "total_countries": 0,
                    "active_customer_count_by_country": {},
                    "period": f"{start_date} to {end_date}",
                }

            # Get unique customer IDs from active subscriptions
            active_customer_ids = set()
            for hit in subscriptions:
                sub_data = hit["_source"]["cleaned_data"]
                customer_id = sub_data.get("customer")
                if customer_id:
                    active_customer_ids.add(customer_id)

            if not active_customer_ids:
                return {
                    "total_active_customers": 0,
                    "total_countries": 0,
                    "active_customer_count_by_country": {},
                    "period": f"{start_date} to {end_date}",
                }

            # Get customer details for active customers
            customer_filters = [
                {"term": {"project_id": project_id}},
                {"terms": {"customer_id": list(active_customer_ids)}},
            ]

            customers = self._query_elasticsearch(
                index="stripe_customers", filters=customer_filters
            )

            # Count active customers by country
            active_customer_count_by_country = {}

            for hit in customers:
                customer_data = hit["_source"]["cleaned_data"]

                # Get country from customer address
                country = (
                    customer_data.get("address", {}).get("country")
                    or customer_data.get("shipping", {}).get("address", {}).get("country")
                    or "Unknown"
                )

                active_customer_count_by_country[country] = (
                    active_customer_count_by_country.get(country, 0) + 1
                )

            # Sort by customer count (descending)
            active_customer_count_by_country = dict(
                sorted(
                    active_customer_count_by_country.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            )

            result = {
                "total_active_customers": len(active_customer_ids),
                "total_countries": len(active_customer_count_by_country),
                "active_customer_count_by_country": active_customer_count_by_country,
                "period": f"{start_date} to {end_date}",
            }

            logger.info(f"Active Customer Count by Country Analysis:")
            logger.info(f"Period: {start_date} to {end_date}")
            logger.info(f"Total Active Customers: {len(active_customer_ids)}")
            logger.info(f"Total Countries: {len(active_customer_count_by_country)}")
            logger.info(f"Active Customer Count by Country: {active_customer_count_by_country}")

            return result

        except Exception as e:
            logger.error(f"Errorcalculating Active Customer Count by Country: {str(e)}")
            return {"error": str(e)}


    def calculate_churn_rate_by_country(
        self, project_id: str, start_date: str, end_date: str
    ) -> dict:
        """
        Calculate Churn Rate by Country - % churn for each country
        Logic: Churned Customers / Active Customers at Start, filtered by customer_country

        Args:
            project_id: Project identifier
            start_date: Start date for analysis period
            end_date: End date for analysis period

        Returns:
            dict: {
                churn_rate_by_country: {country_code: churn_rate_percent},
                churned_customers_by_country: {country_code: churned_count},
                active_customers_by_country: {country_code: active_count},
                total_countries: int,
                period: str
            }
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            # Get active subscriptions at start of period
            filters_start = [
                {"term": {"project_id": project_id}},
                {"range": {"cleaned_data.created": {"lt": start_timestamp}}},
            ]

            query_start = {
                "bool": {
                    "filter": filters_start,
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "cleaned_data.ended_at"}}
                            }
                        },
                        {"range": {"cleaned_data.ended_at": {"gte": start_timestamp}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

            subs_start = self._query_elasticsearch(
                index="stripe_subscriptions", query=query_start
            )

            # Map customer_id to subscription
            active_customer_ids = set()
            for hit in subs_start:
                customer_id = hit["_source"]["cleaned_data"].get("customer")
                if customer_id:
                    active_customer_ids.add(customer_id)

            if not active_customer_ids:
                return {
                    "churn_rate_by_country": {},
                    "churned_customers_by_country": {},
                    "active_customers_by_country": {},
                    "total_countries": 0,
                    "period": f"{start_date} to {end_date}",
                }

            # Get customer details for active customers
            customer_filters = [
                {"term": {"project_id": project_id}},
                {"terms": {"customer_id": list(active_customer_ids)}},
            ]
            customers = self._query_elasticsearch(
                index="stripe_customers", filters=customer_filters
            )

            # Map customer_id to country
            customer_to_country = {}
            for hit in customers:
                customer_data = hit["_source"]["cleaned_data"]
                customer_id = hit["_source"].get("customer_id")
                country = (
                    customer_data.get("address", {}).get("country")
                    or customer_data.get("shipping", {}).get("address", {}).get("country")
                    or "Unknown"
                )
                customer_to_country[customer_id] = country

            # Count active customers by country
            active_customers_by_country = {}
            for customer_id in active_customer_ids:
                country = customer_to_country.get(customer_id, "Unknown")
                active_customers_by_country[country] = (
                    active_customers_by_country.get(country, 0) + 1
                )

            # Get churned subscriptions in period
            filters_churned = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "canceled"}},
                {
                    "range": {
                        "cleaned_data.canceled_at": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]
            subs_churned = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters_churned
            )

            churned_customers_by_country = {}
            churned_customers = set()
            for hit in subs_churned:
                customer_id = hit["_source"]["cleaned_data"].get("customer")
                if customer_id and customer_id in active_customer_ids:
                    country = customer_to_country.get(customer_id, "Unknown")
                    churned_customers_by_country[country] = (
                        churned_customers_by_country.get(country, 0) + 1
                    )
                    churned_customers.add(customer_id)

            # Calculate churn rate by country
            churn_rate_by_country = {}
            for country in active_customers_by_country:
                active_count = active_customers_by_country[country]
                churned_count = churned_customers_by_country.get(country, 0)
                churn_rate = (
                    (churned_count / active_count * 100) if active_count > 0 else 0.0
                )
                churn_rate_by_country[country] = round(churn_rate, 2)

            # Sort by churn rate descending
            churn_rate_by_country = dict(
                sorted(churn_rate_by_country.items(), key=lambda x: x[1], reverse=True)
            )

            result = {
                "churn_rate_by_country": churn_rate_by_country,
                "churned_customers_by_country": churned_customers_by_country,
                "active_customers_by_country": active_customers_by_country,
                "total_countries": len(churn_rate_by_country),
                "period": f"{start_date} to {end_date}",
            }

            logger.info(f"Churn Rate by Country Analysis:")
            logger.info(f"Period: {start_date} to {end_date}")
            logger.info(f"Total Countries: {len(churn_rate_by_country)}")
            logger.info(f"Churn Rate by Country: {churn_rate_by_country}")

            return result

        except Exception as e:
            logger.error(f"Errorcalculating Churn Rate by Country: {str(e)}")
            return {"error": str(e)}


    def calculate_revenue_concentration_by_country(
        self, project_id: str, start_date: str, end_date: str
    ) -> dict:
        """
        Calculate Revenue Concentration by Country.
        Formula: (MRR by Country / Total MRR) * 100

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            dict: {
                country_code: concentration_percent,
                ...
                total_mrr: float,
                period: str
            }
        """
        try:
            mrr_country_result = self.calculate_mrr_by_country(project_id, start_date, end_date)
            total_mrr = mrr_country_result.get("total_mrr", 0.0)
            mrr_by_country = mrr_country_result.get("mrr_by_country", {})

            if not mrr_by_country or total_mrr == 0:
                return {
                    "revenue_concentration_by_country": {},
                    "total_mrr": total_mrr,
                    "period": f"{start_date} to {end_date}",
                }

            concentration_by_country = {
                country: round((mrr / total_mrr) * 100, 2)
                for country, mrr in mrr_by_country.items()
            }

            # Sort by concentration descending
            concentration_by_country = dict(
                sorted(concentration_by_country.items(), key=lambda x: x[1], reverse=True)
            )

            result = {
                "revenue_concentration_by_country": concentration_by_country,
                "total_mrr": total_mrr,
                "period": f"{start_date} to {end_date}",
            }

            logger.info(f"Revenue Concentration by Country Analysis:")
            logger.info(f"Period: {start_date} to {end_date}")
            logger.info(f"Total MRR: {total_mrr}")
            logger.info(f"Revenue Concentration by Country: {concentration_by_country}")

            return result

        except Exception as e:
            logger.error(f"Errorcalculating Revenue Concentration by Country: {str(e)}")
            return {"error": str(e)}


    def get_top_5_countries_by_revenue(
        self, project_id: str, start_date: str, end_date: str
    ) -> dict:
        """
        Get Top 5 Countries by Revenue (MRR).

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            dict: {
                top_5_countries: {country_code: revenue},
                total_mrr: overall total MRR for the period,
                period: start_date to end_date
            }
        """
        try:
            # Step 1: Call the existing function
            mrr_result = self.calculate_mrr_by_country(project_id, start_date, end_date)

            if "error" in mrr_result or not mrr_result.get("mrr_by_country"):
                return {"error": "No MRR data available for this period"}

            # Step 2: Extract sorted mrr_by_country
            mrr_by_country = mrr_result["mrr_by_country"]

            # Step 3: Take Top 5
            top_5 = dict(list(mrr_by_country.items())[:5])

            # Step 4: Format result
            result = {
                "top_5_countries": top_5,
                "total_mrr": mrr_result["total_mrr"],
                "period": mrr_result["period"],
            }

            logger.info("Top 5 Countries by Revenue:")
            for country, revenue in top_5.items():
                logger.info(f"{country}: ${revenue}")

            return result

        except Exception as e:
            logger.error(f"Errorcalculating Top 5 Countries by Revenue: {str(e)}")
            return {"error": str(e)}


    def calculate_mrr_growth_rate_by_country(
        self,
        project_id: str,
        curr_start: str,
        curr_end: str,
        prev_start: str,
        prev_end: str,
    ) -> dict:
        """
        Calculate Month-over-Month Growth Rate by Country.

        Args:
            project_id: The project identifier
            curr_start: Current period start date (YYYY-MM-DD)
            curr_end: Current period end date (YYYY-MM-DD)
            prev_start: Previous period start date (YYYY-MM-DD)
            prev_end: Previous period end date (YYYY-MM-DD)

        Returns:
            dict: {
                growth_by_country: {country_code: growth_rate %},
                current_mrr_by_country: {...},
                previous_mrr_by_country: {...},
                period: f"{prev_start} to {prev_end}" -> f"{curr_start} to {curr_end}"
            }
        """
        try:
            # Step 1: Get current and previous period MRR by country
            curr_mrr_result = self.calculate_mrr_by_country(project_id, curr_start, curr_end)
            prev_mrr_result = self.calculate_mrr_by_country(project_id, prev_start, prev_end)

            curr_mrr_by_country = curr_mrr_result.get("mrr_by_country", {})
            prev_mrr_by_country = prev_mrr_result.get("mrr_by_country", {})

            # Step 2: Collect all countries across both periods
            all_countries = set(curr_mrr_by_country.keys()) | set(
                prev_mrr_by_country.keys()
            )

            # Step 3: Calculate Growth Rates
            growth_by_country = {}
            for country in all_countries:
                curr_val = curr_mrr_by_country.get(country, 0.0)
                prev_val = prev_mrr_by_country.get(country, 0.0)

                if prev_val == 0 and curr_val > 0:
                    growth = None  # new country (could also mark as "New")
                elif prev_val > 0 and curr_val == 0:
                    growth = -100.0  # churned
                elif prev_val == 0 and curr_val == 0:
                    growth = 0.0
                else:
                    growth = ((curr_val - prev_val) / prev_val) * 100

                growth_by_country[country] = (
                    round(growth, 2) if growth is not None else "New"
                )

            # Step 4: Format result
            result = {
                "growth_by_country": growth_by_country,
                "current_mrr_by_country": curr_mrr_by_country,
                "previous_mrr_by_country": prev_mrr_by_country,
                "period": f"{prev_start} to {prev_end} -> {curr_start} to {curr_end}",
            }

            logger.info("Growth Rate by Country:")
            for country, growth in growth_by_country.items():
                logger.info(f"{country}: {growth}%")

            return result

        except Exception as e:
            logger.error(f"Errorcalculating Growth Rate by Country: {str(e)}")
            return {"error": str(e)}


    def calculate_geo_mix_over_time(
        self, project_id: str, start_date: str, end_date: str
    ) -> dict:
        """
        Calculate Geo Mix Over Time (monthly % revenue share by country).

        Args:
            project_id: The project identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            dict: {
                "geo_mix": {
                    "YYYY-MM": {country_code: %share, ...},
                    ...
                },
                "period": "start_date to end_date"
            }
        """
        try:
            # Step 1: Setup date range (month by month)
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            current = start_dt
            geo_mix = {}

            while current <= end_dt:
                # Get start and end of month
                month_start = current.replace(day=1)
                month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

                month_start_str = month_start.strftime("%Y-%m-%d")
                month_end_str = month_end.strftime("%Y-%m-%d")
                month_key = month_start.strftime("%Y-%m")

                # Step 2: Get MRR by country for this month
                mrr_result = self.calculate_mrr_by_country(
                    project_id, month_start_str, month_end_str
                )
                mrr_by_country = mrr_result.get("mrr_by_country", {})
                total_mrr = mrr_result.get("total_mrr", 0.0)

                # Step 3: Calculate % share
                if total_mrr > 0:
                    geo_mix[month_key] = {
                        country: round((value / total_mrr) * 100, 2)
                        for country, value in mrr_by_country.items()
                    }
                else:
                    geo_mix[month_key] = {}

                current += relativedelta(months=1)

            result = {"geo_mix": geo_mix, "period": f"{start_date} to {end_date}"}

            logger.info("Geo Mix Over Time:")
            for month, shares in geo_mix.items():
                logger.info(f"{month}: {shares}")

            return result

        except Exception as e:
            logger.error(f"Errorcalculating Geo Mix Over Time: {str(e)}")
            return {"error": str(e)}


    def calculate_mrr_by_plan(self, project_id: str, start_date: str, end_date: str) -> dict:
        """
        Calculate MRR by Plan - Total MRR grouped by subscription plan.

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            dict: {
                total_mrr: sum of mrr_by_plan values,
                mrr_by_plan: dict: {plan_id: {"plan_name": str, "mrr": float}},
                period: "start_date to end_date"
            }
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            # Step 1: Get active subscriptions
            filters_start = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]

            query_start = {
                "bool": {
                    "filter": filters_start,
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "cleaned_data.ended_at"}}
                            }
                        },
                        {"range": {"cleaned_data.ended_at": {"gte": end_timestamp}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

            subs = self._query_elasticsearch(index="stripe_subscriptions", query=query_start)

            if not subs:
                return {
                    "mrr_by_plan": {},
                    "total_mrr": 0.0,
                    "period": f"{start_date} to {end_date}",
                }

            # Step 2: Collect product IDs
            product_ids = set()
            subscription_rows = []

            for hit in subs:
                sub = hit["_source"]["cleaned_data"]
                plan = sub.get("plan", {})
                product_id = plan.get("product")
                amount = plan.get("amount", 0) or 0
                interval = plan.get("interval", "month")
                interval_count = plan.get("interval_count", 1)

                if not product_id:
                    product_id = "unknown_product"

                # Normalize amount to monthly
                if interval == "year":
                    mrr = amount / 12
                elif interval == "month":
                    mrr = amount / interval_count
                else:
                    mrr = amount  # fallback

                subscription_rows.append((product_id, mrr))
                if product_id != "unknown_product":
                    product_ids.add(product_id)

            # Step 3: Query product names once
            product_name_map = {}
            if product_ids:
                product_filters = [
                    {"term": {"project_id": project_id}},
                    {"terms": {"product_id": list(product_ids)}},
                ]
                products = self._query_elasticsearch(
                    index="stripe_products", filters=product_filters
                )

                for hit in products:
                    pdata = hit["_source"]["cleaned_data"]
                    pid = pdata.get("id")
                    pname = pdata.get("name") or pid
                    product_name_map[pid] = pname

            # Step 4: Aggregate by product
            mrr_by_plan = {}
            total_mrr = 0.0

            for product_id, mrr in subscription_rows:
                pname = product_name_map.get(product_id, product_id)
                mrr_by_plan[pname] = mrr_by_plan.get(pname, 0.0) + mrr
                total_mrr += mrr

            # Step 5: Round results
            mrr_by_plan = {k: round(v, 2) for k, v in mrr_by_plan.items()}
            result = {
                "mrr_by_plan": mrr_by_plan,
                "total_mrr": round(total_mrr, 2),
                "period": f"{start_date} to {end_date}",
            }
            logger.info(f"MRR by Plan Analysis:", result)

            return result

        except Exception as e:
            logger.error(f"Errorcalculating MRR by Plan: {str(e)}")
            return {"error": str(e)}


    def calculate_customer_count_by_plan(
        self, project_id: str, start_date: str, end_date: str
    ) -> dict:
        """
        Active customers per plan (product).

        Args:
            project_id: The project identifier
            start_date: Period start date (ISO format: 'YYYY-MM-DD')
            end_date: Period end date (ISO format: 'YYYY-MM-DD')

        Returns:
            dict: {
                customer_count_by_plan: sum of mrr_by_plan values,
                total_customers: dict: {plan_id: {"plan_name": str, "mrr": float}},
                period: "start_date to end_date"
            }
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            # Step 1: Get active subscriptions in period
            filters_start = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]

            query_start = {
                "bool": {
                    "filter": filters_start,
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "cleaned_data.ended_at"}}
                            }
                        },
                        {"range": {"cleaned_data.ended_at": {"gte": end_timestamp}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

            subscriptions = self._query_elasticsearch(
                index="stripe_subscriptions", query=query_start
            )

            if not subscriptions:
                return {
                    "customer_count_by_plan": {},
                    "total_customers": 0,
                    "period": f"{start_date} to {end_date}",
                }

            # Step 2: Collect customer_ids grouped by product_id
            plan_customer_map = defaultdict(set)  # product_id → set of customer_ids
            product_ids = set()

            for hit in subscriptions:
                sub_data = hit["_source"]["cleaned_data"]
                product_id = sub_data.get("plan", {}).get("product", "unknown_product")
                customer_id = sub_data.get("customer")

                if product_id and customer_id:
                    plan_customer_map[product_id].add(customer_id)
                    product_ids.add(product_id)

            if not product_ids:
                return {
                    "customer_count_by_plan": {},
                    "total_customers": 0,
                    "period": f"{start_date} to {end_date}",
                }

            # Step 3: Query product names in one go
            product_filters = [
                {"term": {"project_id": project_id}},
                {"terms": {"product_id": list(product_ids)}},
            ]

            products = self._query_elasticsearch(
                index="stripe_products", filters=product_filters
            )

            product_name_map = {}
            for hit in products:
                pdata = hit["_source"]["cleaned_data"]
                product_id = pdata.get("id")
                pname = pdata.get("name") or product_id
                product_name_map[product_id] = pname

            # Step 4: Build final result
            customer_count_by_plan = {}
            total_customers = 0

            for product_id, customers in plan_customer_map.items():
                pname = product_name_map.get(product_id, product_id)
                count = len(customers)
                customer_count_by_plan[pname] = count
                total_customers += count

            result = {
                "customer_count_by_plan": customer_count_by_plan,
                "total_customers": total_customers,
                "period": f"{start_date} to {end_date}",
            }
            logger.info(f"Customer count by Plan:", result)

            return result

        except Exception as e:
            logger.error(f"Errorcalculating MRR by Plan: {str(e)}")
            return {"error": str(e)}


    def calculate_churn_rate_by_plan(
        self, project_id: str, start_date: str, end_date: str
    ) -> dict:
        """
        Calculate Churn Rate by Plan - % churn for each subscription plan
        Logic: Churned Customers / Active Customers at Start, grouped by product name

        Args:
            project_id: Project identifier
            start_date: Start date for analysis period
            end_date: End date for analysis period

        Returns:
            dict: {
                churn_rate_by_plan: {product_name: churn_rate_percent},
                total_plans: int,
                period: str
            }
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            end_timestamp = self.convert_date_to_timestamp(end_date)

            # Get active subscriptions at start of period
            filters_start = [
                {"term": {"project_id": project_id}},
                {"range": {"cleaned_data.created": {"lt": start_timestamp}}},
            ]

            query_start = {
                "bool": {
                    "filter": filters_start,
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "cleaned_data.ended_at"}}
                            }
                        },
                        {"range": {"cleaned_data.ended_at": {"gte": start_timestamp}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

            subs_start = self._query_elasticsearch(
                index="stripe_subscriptions", query=query_start
            )

            # Collect product IDs and map customer to plan/product
            product_ids = set()
            customer_to_product_id = {}

            for hit in subs_start:
                data = hit["_source"]["cleaned_data"]
                customer_id = data.get("customer")

                # Get product ID from plan or items
                product_id = None
                if "plan" in data and data["plan"]:
                    product_id = data["plan"].get("product")
                elif "items" in data and data["items"]["data"]:
                    first_item = data["items"]["data"][0]
                    plan = first_item.get("plan", {})
                    product_id = plan.get("product")

                if customer_id and product_id:
                    customer_to_product_id[customer_id] = product_id
                    product_ids.add(product_id)

            if not customer_to_product_id:
                return {
                    "churn_rate_by_plan": {},
                    "total_plans": 0,
                    "period": f"{start_date} to {end_date}",
                }

            # Batch query products to get product names
            product_filters = [
                {"term": {"project_id": project_id}},
                {"terms": {"product_id": list(product_ids)}},
            ]

            products = self._query_elasticsearch(
                index="stripe_products", filters=product_filters
            )

            # Build product_id to name mapping
            product_id_to_name = {}
            for hit in products:
                product_data = hit["_source"]["cleaned_data"]
                product_id = hit["_source"].get("product_id")
                product_name = product_data.get("name", product_id or "Unknown Product")
                if product_id:
                    product_id_to_name[product_id] = product_name

            # Map customer to product name and count active customers by plan
            customer_to_product_name = {}
            active_customers_by_plan = {}

            for customer_id, product_id in customer_to_product_id.items():
                product_name = product_id_to_name.get(
                    product_id, product_id or "Unknown Product"
                )
                customer_to_product_name[customer_id] = product_name
                active_customers_by_plan[product_name] = (
                    active_customers_by_plan.get(product_name, 0) + 1
                )

            # Get churned subscriptions in period
            filters_churned = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "canceled"}},
                {
                    "range": {
                        "cleaned_data.canceled_at": {
                            "gte": start_timestamp,
                            "lte": end_timestamp,
                        }
                    }
                },
            ]
            subs_churned = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters_churned
            )

            churned_customers_by_plan = {}
            churned_customers = set()

            for hit in subs_churned:
                data = hit["_source"]["cleaned_data"]
                customer_id = data.get("customer")
                if customer_id and customer_id in customer_to_product_name:
                    product_name = customer_to_product_name[customer_id]
                    churned_customers_by_plan[product_name] = (
                        churned_customers_by_plan.get(product_name, 0) + 1
                    )
                    churned_customers.add(customer_id)

            # Calculate churn rate by plan (product name)
            churn_rate_by_plan = {}
            for product_name, active_count in active_customers_by_plan.items():
                churned_count = churned_customers_by_plan.get(product_name, 0)
                churn_rate = (
                    (churned_count / active_count * 100) if active_count > 0 else 0.0
                )
                churn_rate_by_plan[product_name] = round(churn_rate, 2)

            # Sort by churn rate descending
            churn_rate_by_plan = dict(
                sorted(churn_rate_by_plan.items(), key=lambda x: x[1], reverse=True)
            )

            result = {
                "churn_rate_by_plan": churn_rate_by_plan,
                "total_plans": len(churn_rate_by_plan),
                "period": f"{start_date} to {end_date}",
            }

            logger.info(f"Churn Rate by Plan Analysis:")
            logger.info(f"Period: {start_date} to {end_date}")
            logger.info(f"Total Plans: {len(churn_rate_by_plan)}")
            logger.info(f"Churn Rate by Plan: {churn_rate_by_plan}")

            return result

        except Exception as e:
            logger.error(f"Errorin calculate_churn_rate_by_plan: {str(e)}")
            return {}


    def calculate_high_value_customers_count(self, project_id: str, threshold: float) -> int:
        """
        Count of customers with ARPU/MRR above a given threshold.

        Args:
            project_id: The project identifier
            threshold: ARPU/MRR threshold value

        Returns:
            int: Number of high-value customers
        """
        try:
            # Get all active subscriptions
            filters = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "active"}},
            ]
            subscriptions = self._query_elasticsearch(
                index="stripe_subscriptions", filters=filters
            )
            if not subscriptions:
                return 0

            # Group subscriptions by customer to get total MRR per customer
            customer_mrr = {}
            for hit in subscriptions:
                sub_data = hit["_source"]["cleaned_data"]
                customer_id = sub_data.get("customer")
                if not customer_id:
                    continue
                sub_mrr = self.calculate_subscription_mrr(sub_data)
                customer_mrr[customer_id] = customer_mrr.get(customer_id, 0.0) + sub_mrr

            # Calculate ARPU for each customer and count those above threshold
            # Since ARPU is per customer, for an individual customer: ARPU = their total MRR
            # (Because we're averaging across 1 customer: MRR/1 = MRR)
            high_value_count = sum(1 for mrr in customer_mrr.values() if mrr > threshold)
            logger.info(f"High-Value Customers (ARPU > {threshold}): {high_value_count}")
            return high_value_count

        except Exception as e:
            logger.error(f"Errorcalculating High-Value Customers count: {str(e)}")
            return 0


    def calculate_at_risk_customers_count(self, project_id: str, start_date: str) -> int:
        """
        Count customers who have recently downgraded their subscriptions.

        Args:
            project_id: The project identifier
            start_date: Start date for lookback period (ISO format: 'YYYY-MM-DD')

        Returns:
            int: Number of at-risk customers
        """
        try:
            start_timestamp = self.convert_date_to_timestamp(start_date)
            filters = [
                {"term": {"project_id": project_id}},
                {"range": {"cleaned_data.created": {"gte": start_timestamp}}},
                {
                    "terms": {
                        "cleaned_data.type": [
                            "customer.subscription.updated",
                            "customer.subscription.deleted",
                        ]
                    }
                },
            ]

            events = self._query_elasticsearch(index="stripe_events", filters=filters)
            at_risk_customers = set()

            for event in events:
                event_data = (
                    event["_source"]["cleaned_data"].get("data", {}).get("object", {})
                )
                prev_attrs = (
                    event["_source"]["cleaned_data"]
                    .get("data", {})
                    .get("previous_attributes", {})
                )

                customer_id = event_data.get("customer")
                if not customer_id:
                    continue

                # Cancellation check
                canceled_at = event_data.get("canceled_at")
                if canceled_at and canceled_at >= start_timestamp:
                    at_risk_customers.add(customer_id)
                    continue

                # Plan downgrade?
                old_price = (
                    prev_attrs.get("items", {})
                    .get("data", [{}])[0]
                    .get("plan", {})
                    .get("amount")
                )
                new_price = (
                    event_data.get("items", {})
                    .get("data", [{}])[0]
                    .get("plan", {})
                    .get("amount")
                )

                if (
                    old_price is not None
                    and new_price is not None
                    and new_price < old_price
                ):
                    at_risk_customers.add(customer_id)
                    continue

                # Quantity reduction?
                old_qty = prev_attrs.get("quantity")
                new_qty = event_data.get("quantity")

                if old_qty is not None and new_qty is not None and new_qty < old_qty:
                    at_risk_customers.add(customer_id)
                    continue

            logger.info(f"Number of at-risk customers: {len(at_risk_customers)}")
            return len(at_risk_customers)

        except Exception as e:
            logger.error(f"Errorcalculating at-risk customers: {str(e)}")
            return 0


    def calculate_average_payment_delay(
        self, project_id: str, start_date: str, end_date: str
    ) -> float:
        """
        Calculate the average delay (in days) between invoice creation and payment.

        Args:
            project_id: Your project identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            float: Average payment delay in days (rounded to 2 decimals)
        """
        try:
            # Convert dates to ISO format or timestamps as needed
            start_ts = self.convert_date_to_timestamp(start_date)
            end_ts = self.convert_date_to_timestamp(end_date)

            # Query for paid invoices in the specified period
            filters = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "paid"}},
                {"range": {"cleaned_data.created": {"gte": start_ts, "lte": end_ts}}},
            ]

            invoices = self._query_elasticsearch(index="stripe_invoices", filters=filters)

            if not invoices:
                logger.info("No paid invoices found for period.")
                return 0.0

            total_delay = 0.0
            count = 0

            for hit in invoices:
                inv = hit["_source"]["cleaned_data"]
                created_ts = inv.get("created")
                paid_at_ts = inv.get("status_transitions", {}).get("paid_at")

                if created_ts and paid_at_ts and paid_at_ts >= created_ts:
                    delay_secs = paid_at_ts - created_ts
                    delay_days = delay_secs / 86400  # seconds in a day
                    total_delay += delay_days
                    count += 1
                else:
                    # Log anomalies or skip invalid data
                    logger.info(f"Skipping invoice with invalid dates: {hit['_id']}")

            if count == 0:
                return 0.0

            avg_delay = total_delay / count
            result = round(avg_delay, 2)
            logger.info(f"Average Payment Delay: {result} days over {count} invoices")
            return result

        except Exception as e:
            logger.error(f"Errorcalculating average payment delay: {str(e)}")
            return 0


    def calculate_failed_payment_rate_by_country(
        self, project_id: str, start_date: str, end_date: str
    ) -> dict:
        """
        Calculate failed invoice rate by country: (failed_invoices ÷ total_invoices) per customer country.

        Args:
            project_id: Your project identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            dict: {
                "failed_rate_by_country": {country_code: failed_rate_percent},
                "failed_invoices_by_country": {country_code: failed_count},
                "total_invoices_by_country": {country_code: total_count},
                "period": "start_date to end_date"
            }
        """
        try:
            start_ts = self.convert_date_to_timestamp(start_date)
            end_ts = self.convert_date_to_timestamp(end_date)

            # 1. Query all invoices in period
            filters = [
                {"term": {"project_id": project_id}},
                {"range": {"cleaned_data.created": {"gte": start_ts, "lte": end_ts}}},
            ]
            invoices = self._query_elasticsearch(index="stripe_invoices", filters=filters)

            if not invoices:
                return {
                    "failed_rate_by_country": {},
                    "failed_invoices_by_country": {},
                    "total_invoices_by_country": {},
                    "period": f"{start_date} to {end_date}",
                }

            # 2. Collect customer_ids
            customer_ids = set()
            invoice_info = []
            for hit in invoices:
                inv = hit["_source"]["cleaned_data"]
                cid = inv.get("customer")
                status = inv.get("status")
                invoice_info.append((cid, status))
                if cid:
                    customer_ids.add(cid)

            # 3. Fetch customer countries in bulk
            filters_cust = [
                {"term": {"project_id": project_id}},
                {"terms": {"customer_id": list(customer_ids)}},
            ]
            customers = self._query_elasticsearch(index="stripe_customers", filters=filters_cust)

            cust_country = {}
            for hit in customers:
                data = hit["_source"]["cleaned_data"]
                cid = hit["_source"].get("customer_id")
                country = (
                    data.get("address", {}).get("country")
                    or data.get("shipping", {}).get("address", {}).get("country")
                    or "Unknown"
                )
                cust_country[cid] = country

            # 4. Tally invoice counts by country: total vs failed
            total_by_country = {}
            failed_by_country = {}
            for cid, status in invoice_info:
                country = cust_country.get(cid, "Unknown")
                total_by_country[country] = total_by_country.get(country, 0) + 1
                if status in ("open", "unpaid"):
                    failed_by_country[country] = failed_by_country.get(country, 0) + 1

            # 5. Compute rates
            failed_rate_by_country = {}
            for country, total in total_by_country.items():
                failed = failed_by_country.get(country, 0)
                rate = (failed / total * 100) if total > 0 else 0.0
                failed_rate_by_country[country] = round(rate, 2)

            # 6. Return structured result
            result = {
                "failed_rate_by_country": dict(
                    sorted(failed_rate_by_country.items(), key=lambda x: x[1], reverse=True)
                ),
                "failed_invoices_by_country": failed_by_country,
                "total_invoices_by_country": total_by_country,
                "period": f"{start_date} to {end_date}",
            }
            logger.info(f"Failed Payment Rate by Country Analysis:", result)
            return result

        except Exception as e:
            logger.error(f"Errorcalculating failed payment rate by country: {str(e)}")
            return 0


    def calculate_refund_rate_by_country(
        self, project_id: str, start_date: str, end_date: str
    ) -> dict:
        """
        Calculate Refund Rate by Country:
        Refund rate (%) per country = (total_refunded_amount ÷ total_paid_amount) * 100

        Args:
            project_id: Your project identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            dict: {
                "refund_rate_by_country": {country_code: refund_rate_percent},
                "refund_invoices_by_country": {country_code: refund_count},
                "total_paid_by_country": {country_code: total_value},
                "period": "start_date to end_date"
            }
        """
        try:
            start_ts = self.convert_date_to_timestamp(start_date)
            end_ts = self.convert_date_to_timestamp(end_date)

            # 1. Fetch invoices in the given period
            filters = [
                {"term": {"project_id": project_id}},
                {"range": {"cleaned_data.created": {"gte": start_ts, "lte": end_ts}}},
            ]
            invoices = self._query_elasticsearch(index="stripe_invoices", filters=filters)

            if not invoices:
                return {
                    "refund_rate_by_country": {},
                    "total_refunded_by_country": {},
                    "total_paid_by_country": {},
                    "period": f"{start_date} to {end_date}",
                }

            # 2. Aggregate paid/refunded amounts per customer
            customer_ids = set()
            invoice_data = []  # (customer_id, amount_paid, amount_refunded)
            for hit in invoices:
                inv = hit["_source"]["cleaned_data"]
                cid = inv.get("customer")
                paid = inv.get("amount_paid", 0)
                refunded = inv.get("amount_refunded", 0)
                invoice_data.append((cid, paid, refunded))
                if cid:
                    customer_ids.add(cid)

            # 3. Retrieve customer countries in bulk
            cust_filters = [
                {"term": {"project_id": project_id}},
                {"terms": {"customer_id": list(customer_ids)}},
            ]
            customers = self._query_elasticsearch(index="stripe_customers", filters=cust_filters)

            customer_to_country = {}
            for hit in customers:
                data = hit["_source"]["cleaned_data"]
                cid = hit["_source"].get("customer_id")
                country = (
                    data.get("address", {}).get("country")
                    or data.get("shipping", {}).get("address", {}).get("country")
                    or "Unknown"
                )
                customer_to_country[cid] = country

            # 4. Summarize totals by country
            paid_by_country = {}
            refunded_by_country = {}
            for cid, paid, refunded in invoice_data:
                country = customer_to_country.get(cid, "Unknown")
                paid_by_country[country] = paid_by_country.get(country, 0) + paid
                refunded_by_country[country] = (
                    refunded_by_country.get(country, 0) + refunded
                )

            # 5. Compute refund rate per country
            refund_rate_by_country = {}
            for country, total_paid in paid_by_country.items():
                total_refunded = refunded_by_country.get(country, 0)
                rate = (total_refunded / total_paid * 100) if total_paid > 0 else 0.0
                refund_rate_by_country[country] = round(rate, 2)
            # 6. Return structured result
            result = {
                "refund_rate_by_country": dict(
                    sorted(refund_rate_by_country.items(), key=lambda x: x[1], reverse=True)
                ),
                "total_refunded_by_country": refunded_by_country,
                "total_paid_by_country": paid_by_country,
                "period": f"{start_date} to {end_date}",
            }
            logger.info(f"Refund Rate by Country Analysis:", result)
            return result

        except Exception as e:
            logger.error(f"Errorcalculating refund rate by country: {str(e)}")
            return 0


    def calculate_mrr_by_currency(self, project_id: str, start_date: str, end_date: str) -> dict:
        """
        Distribution of revenue by currency.
        Calculate MRR grouped by currency.

        Args:
            project_id: The project identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            dict: {
                total_mrr: overall MRR sum across currencies (in base units),
                mrr_by_currency: {currency: mrr_value},
                period: "start_date to end_date"
            }
        """
        try:
            start_ts = self.convert_date_to_timestamp(start_date)
            end_ts = self.convert_date_to_timestamp(end_date)

            # Step 1: Query active subscriptions in period
            filters_start = [
                {"term": {"project_id": project_id}},
                {
                    "range": {
                        "cleaned_data.created": {
                            "gte": start_ts,
                            "lte": end_ts,
                        }
                    }
                },
            ]

            query_start = {
                "bool": {
                    "filter": filters_start,
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "cleaned_data.ended_at"}}
                            }
                        },
                        {"range": {"cleaned_data.ended_at": {"gte": end_ts}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

            subs = self._query_elasticsearch(index="stripe_subscriptions", query=query_start)

            if not subs:
                return {
                    "total_mrr": 0.0,
                    "mrr_by_currency": {},
                    "period": f"{start_date} to {end_date}",
                }

            # Step 2: Aggregate MRR per currency
            mrr_by_currency = {}
            total_mrr = 0.0

            for hit in subs:
                sub = hit["_source"]["cleaned_data"]
                currency = sub.get("currency", "unknown").lower()
                items = sub.get("items", {}).get("data", [])

                sub_mrr = 0.0
                for item in items:
                    plan = item.get("plan", {})
                    amount_cents = plan.get("amount", 0)
                    interval = plan.get("interval", "month")
                    interval_count = plan.get("interval_count", 1)
                    quantity = item.get("quantity", 1)

                    base_amount = amount_cents * quantity
                    # Normalize to monthly (cents)
                    if interval == "year":
                        monthly_amount = base_amount / 12
                    elif interval == "month":
                        monthly_amount = base_amount / interval_count
                    elif interval == "week":
                        monthly_amount = (base_amount * 4) / interval_count  # 4-week month
                    elif interval == "day":
                        monthly_amount = (base_amount * 30) / interval_count  # 30-day month
                    else:
                        monthly_amount = 0

                    sub_mrr += monthly_amount

                mrr_by_currency[currency] = mrr_by_currency.get(currency, 0.0) + sub_mrr
                total_mrr += sub_mrr

            # round
            mrr_by_currency = {cur: round(val, 2) for cur, val in mrr_by_currency.items()}
            result = {
                "total_mrr": round(total_mrr, 2),
                "mrr_by_currency": dict(
                    sorted(mrr_by_currency.items(), key=lambda x: x[1], reverse=True)
                ),
                "period": f"{start_date} to {end_date}",
            }

            logger.info(
                f"MRR by Currency from {start_date} to {end_date}: {result['mrr_by_currency']}"
            )
            return result

        except Exception as e:
            logger.error(f"Errorcalculating mrr by currency: {str(e)}")
            return 0


    def calculate_average_time_to_first_payment(
        self, project_id: str, start_date: str, end_date: str
    ) -> float:
        """
        Calculate the average time (in days) from customer signup to their first paid invoice.

        Args:
            project_id: The project identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            AVG(invoice_date - signup_date) for all customers who paid in the period.
        """
        try:
            start_ts = self.convert_date_to_timestamp(start_date)
            end_ts = self.convert_date_to_timestamp(end_date)

            # 1. Fetch all invoices that were paid during the period
            filters = [
                {"term": {"project_id": project_id}},
                {"term": {"cleaned_data.status": "paid"}},
                {"range": {"cleaned_data.created": {"gte": start_ts, "lte": end_ts}}},
            ]
            paid_invoices = self._query_elasticsearch(
                index="stripe_invoices", filters=filters
            )

            if not paid_invoices:
                return 0.0  # No paid invoices → no meaningful result

            # 2. Collect unique customer IDs and invoice dates
            customer_invoice_map = {}  # customer_id → earliest invoice timestamp
            for hit in paid_invoices:
                inv = hit["_source"]["cleaned_data"]
                cid = inv.get("customer")
                inv_date = inv.get("created")
                if cid and inv_date:
                    if (
                        cid not in customer_invoice_map
                        or inv_date < customer_invoice_map[cid]
                    ):
                        customer_invoice_map[cid] = inv_date

            if not customer_invoice_map:
                return 0.0

            # 3. Fetch signup (created) date for each customer in bulk
            customer_ids = list(customer_invoice_map.keys())
            cust_filters = [
                {"term": {"project_id": project_id}},
                {"terms": {"customer_id": customer_ids}},
            ]
            customers = self._query_elasticsearch(
                index="stripe_customers",
                filters=cust_filters,
            )

            # Map customer to signup timestamp
            signup_map = {}
            for hit in customers:
                data = hit["_source"]["cleaned_data"]
                cid = hit["_source"].get("customer_id")
                created_ts = data.get("created")
                if cid and created_ts:
                    signup_map[cid] = created_ts

            # 4. Compute time differences
            total_days = 0.0
            count = 0
            for cid, invoice_ts in customer_invoice_map.items():
                signup_ts = signup_map.get(cid)
                if signup_ts and invoice_ts >= signup_ts:
                    days_diff = (invoice_ts - signup_ts) / 86400  # seconds → days
                    total_days += days_diff
                    count += 1

            if count == 0:
                return 0.0

            avg_days = round(total_days / count, 2)
            logger.info(f"Average Time to First Payment: {avg_days} days over {count} customers")
            return avg_days

        except Exception as e:
            logger.error(f"Errorcalculating average time to fist payment: {str(e)}")
            return 0

ServiceRegistry.register_toolset("stripe", ReactDatabaseTools)