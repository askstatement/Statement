import os
import stripe
from bson import ObjectId
from typing import Optional
from datetime import datetime
from elasticsearch import exceptions
from core.base_service import BaseService
from core.registry import ServiceRegistry
from core.logger import Logger

logger = Logger(__name__)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

class StripeService(BaseService):
    name = "stripe"
    
    CURRENCY_EXPONENTS = {
        "bif": 0,
        "clp": 0,
        "djf": 0,
        "gnf": 0,
        "jpy": 0,
        "kmf": 0,
        "krw": 0,
        "mga": 0,
        "pyg": 0,
        "rwf": 0,
        "ugx": 0,
        "vnd": 0,
        "vuv": 0,
        "xaf": 0,
        "xof": 0,
        "xpf": 0,
    }

    async def sync_stripe_invoices(self, key: str, project_id: str):
        stripe.api_key = key
        """Fetches all Stripe invoices and indexes them to Elasticsearch"""
        try:
            invoices = stripe.Invoice.list(limit=100)

            for invoice in invoices.auto_paging_iter():
                cleaned_invoice = self.clean_dict(
                    invoice.to_dict()
                )  # Convert Stripe object to dict and clean it
                doc = {
                    "project_id": project_id,
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.number,
                    "customer_name": invoice.customer_name,
                    "cleaned_data": cleaned_invoice,
                    "last_synced": datetime.utcnow().isoformat(),
                }
                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_invoices",
                    query={"project_id": project_id, "invoice_number": invoice.number},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{invoice.id}")
                self.elastic.index_document(index="stripe_invoices", document=doc, id=es_id)

                logger.info(f"Indexed invoice {invoice.id} (Status: {invoice.status})")
            return { "status": "success", "indexed": invoices.data.count }

        except stripe.error.StripeError as e:
            return {"status": "stripe_error", "error": str(e)}


    async def sync_stripe_customers(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            # Get all Stripe customers
            customers = stripe.Customer.list(limit=100)

            # Process each customer
            for cust in customers.auto_paging_iter():
                cleaned_data = self.clean_dict(cust.to_dict())
                customer_data = {
                    "project_id": project_id,
                    "customer_id": cust.id,
                    "email": cust.email,
                    "name": cust.name,
                    "cleaned_data": cleaned_data,
                    "last_synced": datetime.utcnow(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_customers",
                    query={"project_id": project_id, "customer_id": cust.id},
                    update_values=customer_data,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{cust.id}")
                self.elastic.index_document(index="stripe_customers", document=customer_data, id=es_id)
                logger.info(f"Synced customer: {cust.id} - {cust.email}")

            return {"status": "success", "synced": customers.data.count}

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_stripe_products(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            products = stripe.Product.list(limit=100)
            for product in products.auto_paging_iter():
                cleaned_product = self.clean_dict(product.to_dict())
                doc = {
                    "project_id": project_id,
                    "product_id": product.id,  # reference field for products
                    "cleaned_data": cleaned_product,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_products",
                    query={"project_id": project_id, "product_id": product.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{product.id}")
                self.elastic.index_document(index="stripe_products", document=doc, id=es_id)
                logger.info(f"Synced product: {product.id}")

            return {"status": "success", "synced": products.data.count}

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_stripe_subscriptions(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            subscriptions = stripe.Subscription.list(limit=100, status='all' )
            for sub in subscriptions.auto_paging_iter():
                cleaned_sub = self.clean_dict(sub.to_dict())
                doc = {
                    "project_id": project_id,
                    "subscription_id": sub.id,  # reference field for subscriptions
                    "cleaned_data": cleaned_sub,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_subscriptions",
                    query={"project_id": project_id, "subscription_id": sub.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{sub.id}")
                self.elastic.index_document(index="stripe_subscriptions", document=doc, id=es_id)
                logger.info(f"Synced subscription: {sub.id}")

            return {"status": "success", "synced": subscriptions.data.count}

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_stripe_balancetransactions(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            transactions = stripe.BalanceTransaction.list(limit=100)
            for tx in transactions.auto_paging_iter():
                cleaned_tx = self.clean_dict(tx.to_dict())
                doc = {
                    "project_id": project_id,
                    "transaction_id": tx.id,  # reference field for balance transactions
                    "cleaned_data": cleaned_tx,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_balance_transactions",
                    query={"project_id": project_id, "transaction_id": tx.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{tx.id}")
                self.elastic.index_document(index="stripe_balancetransactions", document=doc, id=es_id)
                logger.info(f"Synced BalanceTransaction: {tx.id}")

            return {"status": "success", "synced": transactions.data.count}

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_stripe_events(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            events = stripe.Event.list(limit=100)
            for ev in events.auto_paging_iter():
                cleaned_ev = self.clean_dict(ev.to_dict())
                doc = {
                    "project_id": project_id,
                    "event_id": ev.id,  # reference field for events
                    "cleaned_data": cleaned_ev,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_events",
                    query={"project_id": project_id, "event_id": ev.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{ev.id}")
                self.elastic.index_document(index="stripe_events", document=doc, id=es_id)
                logger.info(f"Synced Events: {ev.id}")

            return {"status": "success", "synced": events.data.count}

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_stripe_charges(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            charges = stripe.Charge.list(limit=100)
            for ch in charges.auto_paging_iter():
                cleaned_ch = self.clean_dict(ch.to_dict())
                doc = {
                    "project_id": project_id,
                    "charge_id": ch.id,  # reference field for charges
                    "cleaned_data": cleaned_ch,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_charges",
                    query={"project_id": project_id, "charge_id": ch.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{ch.id}")
                self.elastic.index_document(index="stripe_charges", document=doc, id=es_id)
                logger.info(f"Synced Charges: {ch.id}")

            return {"status": "success", "synced": charges.data.count}

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_stripe_refunds(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            refunds = stripe.Refund.list(limit=100)
            for rf in refunds.auto_paging_iter():
                cleaned_rf = self.clean_dict(rf.to_dict())
                doc = {
                    "project_id": project_id,
                    "refund_id": rf.id,  # reference field for refunds
                    "cleaned_data": cleaned_rf,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_refunds",
                    query={"project_id": project_id, "refund_id": rf.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{rf.id}")
                self.elastic.index_document(index="stripe_refunds", document=doc, id=es_id)
                logger.info(f"Synced Refund: {rf.id}")

            return {"status": "success", "synced": refunds.data.count}

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_stripe_payouts(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            payouts = stripe.Payout.list(limit=100)
            for po in payouts.auto_paging_iter():
                cleaned_po = self.clean_dict(po.to_dict())
                doc = {
                    "project_id": project_id,
                    "payout_id": po.id,  # reference field for payouts
                    "cleaned_data": cleaned_po,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_payouts",
                    query={"project_id": project_id, "payout_id": po.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{po.id}")
                self.elastic.index_document(index="stripe_payouts", document=doc, id=es_id)
                logger.info(f"Synced Payout: {po.id}")

            return {"status": "success", "synced": payouts.data.count}

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {"status": "error", "message": str(e)}


    # Balance sync
    async def sync_stripe_balance(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            balance = stripe.Balance.retrieve()
            cleaned_balance = self.clean_dict(balance.to_dict())
            doc = {
                "project_id": project_id,
                "balance_id": f"{project_id}_balance",  # unique identifier for balance
                "cleaned_data": cleaned_balance,
                "last_synced": datetime.utcnow().isoformat(),
            }

            # Upsert into MongoDB
            await self.mongodb.update_one(
                collection_name="stripe_balance",
                query={"project_id": project_id, "balance_id": f"{project_id}_balance"},
                update_values=doc,
                upsert=True
            )

            # Index document
            es_id = self.generate_hash(f"{project_id}_balance")
            self.elastic.index_document(index="stripe_balance", document=doc, id=es_id)
            logger.info(f"Synced Balance: {project_id}_balance")

            return {"status": "success", "synced": 1}
        except Exception as e:
            logger.error(f"Error syncing balance: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Disputes sync
    async def sync_stripe_disputes(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            disputes = stripe.Dispute.list(limit=100)
            synced_count = 0
            for dispute in disputes.auto_paging_iter():
                cleaned_dispute = self.clean_dict(dispute.to_dict())
                doc = {
                    "project_id": project_id,
                    "dispute_id": dispute.id,
                    "cleaned_data": cleaned_dispute,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_disputes",
                    query={"project_id": project_id, "dispute_id": dispute.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{dispute.id}")
                self.elastic.index_document(index="stripe_disputes", document=doc, id=es_id)
                logger.info(f"Synced Dispute: {dispute.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing disputes: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Files sync
    async def sync_stripe_files(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            files = stripe.File.list(limit=100)
            synced_count = 0
            for file_obj in files.auto_paging_iter():
                cleaned_file = self.clean_dict(file_obj.to_dict())
                doc = {
                    "project_id": project_id,
                    "file_id": file_obj.id,
                    "cleaned_data": cleaned_file,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_files",
                    query={"project_id": project_id, "file_id": file_obj.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{file_obj.id}")
                self.elastic.index_document(index="stripe_files", document=doc, id=es_id)
                logger.info(f"Synced File: {file_obj.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing files: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Mandates sync
    async def sync_stripe_mandates(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            mandates = stripe.Mandate.list(limit=100)
            synced_count = 0
            for mandate in mandates.auto_paging_iter():
                cleaned_mandate = self.clean_dict(mandate.to_dict())
                doc = {
                    "project_id": project_id,
                    "mandate_id": mandate.id,
                    "cleaned_data": cleaned_mandate,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_mandates",
                    query={"project_id": project_id, "mandate_id": mandate.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{mandate.id}")
                self.elastic.index_document(index="stripe_mandates", document=doc, id=es_id)
                logger.info(f"Synced Mandate: {mandate.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing mandates: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Payment Intents sync
    async def sync_stripe_payment_intents(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            payment_intents = stripe.PaymentIntent.list(limit=100)
            synced_count = 0
            for pi in payment_intents.auto_paging_iter():
                cleaned_pi = self.clean_dict(pi.to_dict())
                doc = {
                    "project_id": project_id,
                    "payment_intent_id": pi.id,
                    "cleaned_data": cleaned_pi,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_payment_intents",
                    query={"project_id": project_id, "payment_intent_id": pi.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{pi.id}")
                self.elastic.index_document(index="stripe_payment_intents", document=doc, id=es_id)
                logger.info(f"Synced PaymentIntent: {pi.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing payment intents: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Plans sync
    async def sync_stripe_plans(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            plans = stripe.Plan.list(limit=100)
            synced_count = 0
            for plan in plans.auto_paging_iter():
                cleaned_plan = self.clean_dict(plan.to_dict())
                doc = {
                    "project_id": project_id,
                    "plan_id": plan.id,
                    "cleaned_data": cleaned_plan,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_plans",
                    query={"project_id": project_id, "plan_id": plan.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{plan.id}")
                self.elastic.index_document(index="stripe_plans", document=doc, id=es_id)
                logger.info(f"Synced Plan: {plan.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing plans: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Coupons sync
    async def sync_stripe_coupons(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            coupons = stripe.Coupon.list(limit=100)
            synced_count = 0
            for coupon in coupons.auto_paging_iter():
                cleaned_coupon = self.clean_dict(coupon.to_dict())
                doc = {
                    "project_id": project_id,
                    "coupon_id": coupon.id,
                    "cleaned_data": cleaned_coupon,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_coupons",
                    query={"project_id": project_id, "coupon_id": coupon.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{coupon.id}")
                self.elastic.index_document(index="stripe_coupons", document=doc, id=es_id)
                logger.info(f"Synced Coupon: {coupon.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing coupons: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Payment Methods sync
    async def sync_stripe_payment_methods(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            payment_methods = stripe.PaymentMethod.list(limit=100)
            synced_count = 0
            for pm in payment_methods.auto_paging_iter():
                cleaned_pm = self.clean_dict(pm.to_dict())
                doc = {
                    "project_id": project_id,
                    "payment_method_id": pm.id,
                    "cleaned_data": cleaned_pm,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_payment_methods",
                    query={"project_id": project_id, "payment_method_id": pm.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{pm.id}")
                self.elastic.index_document(index="stripe_payment_methods", document=doc, id=es_id)
                logger.info(f"Synced PaymentMethod: {pm.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing payment methods: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Setup Intents sync
    async def sync_stripe_setup_intents(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            setup_intents = stripe.SetupIntent.list(limit=100)
            synced_count = 0
            for si in setup_intents.auto_paging_iter():
                cleaned_si = self.clean_dict(si.to_dict())
                doc = {
                    "project_id": project_id,
                    "setup_intent_id": si.id,
                    "cleaned_data": cleaned_si,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_setup_intents",
                    query={"project_id": project_id, "setup_intent_id": si.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{si.id}")
                self.elastic.index_document(index="stripe_setup_intents", document=doc, id=es_id)
                logger.info(f"Synced SetupIntent: {si.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing setup intents: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Tax Rates sync
    async def sync_stripe_tax_rates(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            tax_rates = stripe.TaxRate.list(limit=100)
            synced_count = 0
            for tr in tax_rates.auto_paging_iter():
                cleaned_tr = self.clean_dict(tr.to_dict())
                doc = {
                    "project_id": project_id,
                    "tax_rate_id": tr.id,
                    "cleaned_data": cleaned_tr,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_tax_rates",
                    query={"project_id": project_id, "tax_rate_id": tr.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{tr.id}")
                self.elastic.index_document(index="stripe_tax_rates", document=doc, id=es_id)
                logger.info(f"Synced TaxRate: {tr.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing tax rates: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Application Fees sync
    async def sync_stripe_application_fees(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            application_fees = stripe.ApplicationFee.list(limit=100)
            synced_count = 0
            for af in application_fees.auto_paging_iter():
                cleaned_af = self.clean_dict(af.to_dict())
                doc = {
                    "project_id": project_id,
                    "application_fee_id": af.id,
                    "cleaned_data": cleaned_af,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_application_fees",
                    query={"project_id": project_id, "application_fee_id": af.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{af.id}")
                self.elastic.index_document(index="stripe_application_fees", document=doc, id=es_id)
                logger.info(f"Synced ApplicationFee: {af.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing application fees: {str(e)}")
            return {"status": "error", "error": str(e)}


    # Transfers sync
    async def sync_stripe_transfers(self, key: str, project_id: str):
        stripe.api_key = key
        try:
            transfers = stripe.Transfer.list(limit=100)
            synced_count = 0
            for transfer in transfers.auto_paging_iter():
                cleaned_transfer = self.clean_dict(transfer.to_dict())
                doc = {
                    "project_id": project_id,
                    "transfer_id": transfer.id,
                    "cleaned_data": cleaned_transfer,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                await self.mongodb.update_one(
                    collection_name="stripe_transfers",
                    query={"project_id": project_id, "transfer_id": transfer.id},
                    update_values=doc,
                    upsert=True
                )

                # Index document
                es_id = self.generate_hash(f"{project_id}{transfer.id}")
                self.elastic.index_document(index="stripe_transfers", document=doc, id=es_id)
                logger.info(f"Synced Transfer: {transfer.id}")
                synced_count += 1

            return {"status": "success", "synced": synced_count}
        except Exception as e:
            logger.error(f"Error syncing transfers: {str(e)}")
            return {"status": "error", "error": str(e)}
        
    async def stripe_oauth_callback(self, code: str):
        # Validate state to prevent CSRF
        stripe.api_key = STRIPE_SECRET_KEY
        resp = stripe.OAuth.token(
            grant_type="authorization_code",
            code=code,
        )
        stripe_user_id = resp["stripe_user_id"]
        access_token = resp["access_token"]
        refresh_token = resp["refresh_token"]
        return stripe_user_id, access_token, refresh_token
        
    async def remove_stripe_secret_key(self, project_id: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$unset": {"stripe_key": 1}},
        )
        return True if project.modified_count > 0 else False
    
    async def update_stripe_secret_key(self, project_id: str, key: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"stripe_key": key}},
        )
        return True if project.modified_count > 0 else False
    
    async def remove_stripe_secret_key(self, project_id: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$unset": {"stripe_key": 1}},
        )
        return True if project.modified_count > 0 else False
    
    async def disconnect_stripe(self, project_id: str):
        # remove stripe data from elasticsearch and mongodb
        status = self.es_remove_stripe_data(project_id)
        prefix = "stripe_"
        collections = await self.mongodb.list_collections()

        stripe_collections = [c for c in collections if c.startswith(prefix)]
        # 3. Remove documents where project_id exists
        for col_name in stripe_collections:
            col = self.mongodb.get_collection(col_name)
            result = await col.delete_many({"project_id": project_id})
            logger.info(f"Deleted {result.deleted_count} documents from {col_name}")
        return status
    
    def es_remove_stripe_data(self, project_id: str) -> bool:
        """
        Remove all Stripe-related data for a given project from Elasticsearch.
        """
        if not project_id:
            return False
        indices = self.elastic.list_indices(pattern="stripe_*")

        for index in indices:
            try:
                query = {
                    "query": {
                        "term": {
                            "project_id": project_id
                        }
                    }
                }
                self.elastic.delete_by_query(index=index, body=query)
                logger.info(f"Deleted Stripe data from index: {index} for project_id: {project_id}")
            except exceptions.NotFoundError:
                logger.error(f"Index not found: {index}, skipping.")
            except Exception as e:
                logger.error(f"Error deleting data from index {index}: {str(e)}")
                return False
        return True
    
ServiceRegistry.register_service("stripe", StripeService())
