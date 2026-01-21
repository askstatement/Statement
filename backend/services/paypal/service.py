import os
import requests
from bson import ObjectId
from typing import Optional
from datetime import datetime, timedelta
from elasticsearch import exceptions
from core.base_service import BaseService
from core.registry import ServiceRegistry
from core.logger import Logger
from core.base_utils import BaseUtils

logger = Logger(__name__)

paypal_env = os.getenv("PAYPAL_ENV", "live")
sandbox_url = os.getenv("PAYPAL_SANDBOX_URL", "https://api-m.sandbox.paypal.com")
live_url = os.getenv("PAYPAL_LIVE_URL", "https://api-m.paypal.com")
api_host_url = sandbox_url if paypal_env == "sandbox" else live_url
token_url = os.getenv("PAYPAL_TOKEN_URL", "/v1/oauth2/token")

class PaypalService(BaseService):
    name = "paypal"
    
    async def paypal_direct_auth(self, client_id, client_secret):
        try:
            get_token_url = f"{api_host_url}{token_url}"

            data = {"grant_type": "client_credentials"}
            headers = {"Accept": "application/json", "Accept-Language": "en_US"}

            response = requests.post(
                get_token_url,
                data=data,
                headers=headers,
                auth=(client_id, client_secret)
            )
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data.get("access_token")

            return access_token
        except Exception as e:
            logger.info(f"Error fetching PayPal access token: {e}")
            return None
        
    async def update_paypal_secret_key(self, project_id: str, client_id: str, client_secret: str) -> bool:
        utils = BaseUtils()
        encoded_id = utils.encode_secret(client_id)
        encoded_secret = utils.encode_secret(client_secret)
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"paypal_client_id": encoded_id, "paypal_client_secret": encoded_secret}},
        )
        return True if project.modified_count > 0 else False

    async def sync_paypal_invoices(self, access_token: str, project_id: str):
        """Fetches all Paypal invoices and indexes them to Elasticsearch"""
        indexed_count = 0
        try:
            paypal_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            invoice_url = os.getenv("PAYPAL_INVOICES_URL", "/v2/invoicing/invoices?page=1&page_size=10&total_required=true&fields=all")
            get_invoice_url = f"{api_host_url}{invoice_url}"
            # Get invoices
            while get_invoice_url:
                response = requests.get(get_invoice_url, headers=paypal_headers)
                response.raise_for_status()
                data = response.json()

                for invoice in data.get("items", []):
                    doc = {
                        "project_id": project_id,
                        "invoice_id": f"{project_id}_{invoice.get('id')}",
                        "invoice_number": invoice.get("detail", {}).get("invoice_number"),
                        "customer_name": None,  # Initialize as None
                        "data": invoice,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Safely extract customer name
                    primary_recipients = invoice.get("primary_recipients", [])
                    if primary_recipients and isinstance(primary_recipients, list):
                        first_recipient = primary_recipients[0]
                        billing_info = first_recipient.get("billing_info", {})
                        name_info = billing_info.get("name", {})
                        doc["customer_name"] = name_info.get("full_name") or name_info.get("given_name") 
                    # Upsert into MongoDB
                    paypal_invoices = self.mongodb.get_collection("paypal_invoices")
                    await paypal_invoices.update_one(
                        {
                            "project_id": project_id,
                            "invoice_id": doc["invoice_id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index document
                    es_id = self.generate_hash(f"{doc.get('invoice_id')}")
                    self.elastic.index_document(index="paypal_invoices", document=doc, id=es_id)
                    indexed_count += 1

                    logger.info(f"Indexed invoice {invoice.get('id')} Status: {invoice.get('status')}")

                # Pagination: Check for next link
                next_link = next((link["href"] for link in data.get("links", []) if link["rel"] == "next"), None)
                get_invoice_url = next_link

            return {
                "status": "success",
                "indexed": indexed_count,
            }

        except Exception as e:
            logger.error(f"Error fetching invoices: {e}")
            return {
                "status": "error",
                "message": str(e),
            }
            
    async def sync_paypal_balances(self, access_token: str, project_id: str):
        """Fetch PayPal balances and index to Elasticsearch / store in DB."""
        indexed_count = 0
        try:
            paypal_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            balances_path = os.getenv("PAYPAL_BALANCES_URL", "/v1/reporting/balances")
            get_balances_url = f"{api_host_url}{balances_path}"

            response = requests.get(get_balances_url, headers=paypal_headers)
            response.raise_for_status()
            body = response.json()

            for bal in body.get("balances", []):
                doc = {
                    "project_id": project_id,
                    "balance_id": f"{project_id}_{bal.get('currency')}",
                    "currency": bal.get("currency"),
                    "primary": bal.get("primary", False),
                    "total_balance": bal.get("total_balance"),
                    "available_balance": bal.get("available_balance"),
                    "withheld_balance": bal.get("withheld_balance"),
                    "data": bal,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                paypal_balances = self.mongodb.get_collection("paypal_balances")
                await paypal_balances.update_one(
                    {
                        "project_id": project_id,
                        "balance_id": doc["balance_id"]
                    },
                    {"$set": doc},
                    upsert=True,
                )

                # Index to ES
                es_id = self.generate_hash(f"{doc.get('balance_id')}")
                self.elastic.index_document(index="paypal_balances", document=doc, id=es_id)
                indexed_count += 1
                logger.info(f"Indexed PayPal balance for currency {bal.get('currency')}")

            return {
                "status": "success",
                "indexed": indexed_count,
            }

        except Exception as e:
            logger.error(f"Error fetching PayPal balances: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_paypal_user_info(self, access_token: str, project_id: str):
        """Fetch PayPal user info (via identity API) and index it / store it."""
        try:
            paypal_headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            userinfo_path = os.getenv("PAYPAL_USER_INFO_URL", "/v1/identity/oauth2/userinfo?schema=paypalv1.1")
            get_userinfo_url = f"{api_host_url}{userinfo_path}"

            response = requests.get(get_userinfo_url, headers=paypal_headers)
            response.raise_for_status()
            user = response.json()

            doc = {
                "project_id": project_id,
                "user_id": f"{project_id}_{user.get('payer_id')}",
                "name": user.get("name"),
                "emails": user.get("emails"),
                "address": user.get("address"),
                "data": user,
                "last_synced": datetime.utcnow().isoformat(),
            }

            # Upsert into MongoDB
            paypal_user_info = self.mongodb.get_collection("paypal_user_info")
            await paypal_user_info.update_one(
                {
                    "project_id": project_id,
                    "user_id": doc["user_id"]
                },
                {"$set": doc},
                upsert=True,
            )

            # Index to Elasticsearch
            es_id = self.generate_hash(f"{doc.get('user_id')}")
            self.elastic.index_document(index="paypal_user_info", document=doc, id=es_id)
            logger.info(f"Indexed PayPal user info for user: {user.get('user_id')}")
            return {
                "status": "success",
                "user": user,
            }
        except Exception as e:
            logger.error(f"Error fetching PayPal user info: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_paypal_subscriptions(self, access_token: str, project_id: str):
        """Fetch all PayPal subscriptions and index them to Elasticsearch"""
        indexed_count = 0
        try:
            paypal_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            subscription_url = os.getenv("PAYPAL_SUBSCRIPTION_URL", "/v1/billing/subscriptions?page=1&page_size=10")
            get_subscription_url = f"{api_host_url}{subscription_url}"

            # Fetch subscriptions (loop for pagination)
            while get_subscription_url:
                response = requests.get(get_subscription_url, headers=paypal_headers)
                response.raise_for_status()
                data = response.json()

                for subscription in data.get("subscriptions", []):
                    doc = {
                        "project_id": project_id,
                        "subscription_id": f"{project_id}_{subscription.get('id')}",
                        "status": subscription.get("status"),
                        "plan_id": subscription.get("plan_id"),
                        "start_time": subscription.get("start_time"),
                        "update_time": subscription.get("update_time"),
                        "subscriber_name": None,
                        "subscriber_email": None,
                        "data": subscription,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Extract subscriber info safely
                    subscriber = subscription.get("subscriber", {})
                    if isinstance(subscriber, dict):
                        name_info = subscriber.get("name", {})
                        doc["subscriber_name"] = name_info.get(
                            "full_name"
                        ) or name_info.get("given_name")
                        doc["subscriber_email"] = subscriber.get("email_address")

                    # Upsert into MongoDB
                    paypal_subscriptions = self.mongodb.get_collection("paypal_subscriptions")
                    await paypal_subscriptions.update_one(
                        {
                            "project_id": project_id,
                            "subscription_id": doc["subscription_id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index document to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('subscription_id')}")
                    self.elastic.index_document(index="paypal_subscriptions", document=doc, id=es_id)
                    indexed_count += 1

                    logger.info(
                        f"Indexed subscription {subscription.get('id')} Status: {subscription.get('status')}"
                    )

                # Pagination: check for next link
                next_link = next(
                    (
                        link["href"]
                        for link in data.get("links", [])
                        if link["rel"] == "next"
                    ),
                    None,
                )
                get_subscription_url = next_link

            return {
                "status": "success",
                "indexed": indexed_count,
            }

        except Exception as e:
            logger.error(f"Error fetching paypal subscriptions: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_paypal_payment_tokens(self, access_token: str, project_id: str):
        """Fetch all PayPal payment tokens and index them"""
        indexed_count = 0
        try:
            paypal_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            payment_tokens_url = os.getenv("PAYPAL_PAYMENT_TOKENS_URL", "/v3/vault/payment-tokens?page_size=5&page=1")
            tokens_url = f"{api_host_url}{payment_tokens_url}"
            get_tokens_url = tokens_url

            while get_tokens_url:
                response = requests.get(get_tokens_url, headers=paypal_headers)
                response.raise_for_status()
                data = response.json()

                for token in data.get("payment_tokens", []):
                    doc = {
                        "project_id": project_id,
                        "token_id": f"{project_id}_{token.get('id')}",
                        "payment_source": token.get("payment_source"),
                        "customer": token.get("customer"),
                        "status": token.get("status"),
                        "data": token,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Store in MongoDB
                    paypal_payment_tokens = self.mongodb.get_collection("paypal_payment_tokens")
                    await paypal_payment_tokens.update_one(
                        {
                            "project_id": project_id,
                            "token_id": doc["token_id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )
                    # Index document to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('token_id')}")
                    self.elastic.index_document(index="paypal_payment_tokens", document=doc, id=es_id)
                    indexed_count += 1

                next_page = data.get("links", [])
                get_tokens_url = next((link["href"] for link in next_page if link["rel"] == "next"), None)

            return {"status": "success", "indexed": indexed_count}

        except Exception as e:
            logger.error(f"Error fetching paypal payment tokens: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_paypal_products(self, access_token: str, project_id: str):
        """Fetch all PayPal products and index them"""
        indexed_count = 0
        try:
            paypal_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            products_api_path = os.getenv("PAYPAL_PRODUCTS_URL", "/v1/catalogs/products?page_size=10&page=1")
            products_url = f"{api_host_url}{products_api_path}"
            get_products_url = products_url

            while get_products_url:
                response = requests.get(get_products_url, headers=paypal_headers)
                response.raise_for_status()
                data = response.json()

                for product in data.get("products", []):
                    doc = {
                        "project_id": project_id,
                        "product_id": f"{project_id}_{product.get('id')}",
                        "name": product.get("name"),
                        "description": product.get("description"),
                        "type": product.get("type"),
                        "category": product.get("category"),
                        "data": product,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Store in MongoDB
                    paypal_products = self.mongodb.get_collection("paypal_products")
                    await paypal_products.update_one(
                        {
                            "project_id": project_id,
                            "product_id": doc["product_id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )
                    # Index document to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('product_id')}")
                    self.elastic.index_document(index="paypal_products", document=doc, id=es_id)
                    indexed_count += 1

                next_page = data.get("links", [])
                get_products_url = next((link["href"] for link in next_page if link["rel"] == "next"), None)

            return {"status": "success", "indexed": indexed_count}
        
        except Exception as e:
            logger.error(f"Error fetching paypal products: {e}")
            return {
                "status": "error",
                "message": str(e),
            }
            
            
    async def sync_paypal_plans(self, access_token: str, project_id: str):
        """Fetch all PayPal billing plans and index them"""
        indexed_count = 0
        try:
            paypal_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            plans_api_path = os.getenv("PAYPAL_PLANS_URL", "/v1/billing/plans?page_size=10&page=1")
            plans_url = f"{api_host_url}{plans_api_path}"
            params = {
                "page_size": 20,
                "page": 1,
                "total_required": "true"
            }
            
            get_plans_url = plans_url
            while get_plans_url:
                response = requests.get(get_plans_url, headers=paypal_headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                for plan in data.get("plans", []):
                    doc = {
                        "project_id": project_id,
                        "plan_id": f"{project_id}_{plan.get('id')}",
                        "product_id": plan.get("product_id"),
                        "name": plan.get("name"),
                        "description": plan.get("description"),
                        "status": plan.get("status"),
                        "usage_type": plan.get("usage_type"),
                        "billing_cycles": plan.get("billing_cycles", []),
                        "payment_preferences": plan.get("payment_preferences", {}),
                        "taxes": plan.get("taxes", {}),
                        "create_time": plan.get("create_time"),
                        "update_time": plan.get("update_time"),
                        "data": plan,
                        "last_synced": datetime.utcnow().isoformat(),
                    }
                    
                    paypal_plans = self.mongodb.get_collection("paypal_plans")
                    await paypal_plans.update_one(
                        {
                            "project_id": project_id,
                            "plan_id": doc["plan_id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )
                    es_id = self.generate_hash(f"{doc.get('plan_id')}")
                    self.elastic.index_document(index="paypal_plans", document=doc, id=es_id)
                    indexed_count += 1
                
                # Get next page link
                next_page = data.get("links", [])
                get_plans_url = next((link["href"] for link in next_page if link["rel"] == "next"), None)
                params = {}  # Clear params for subsequent requests as URL has them
            
            return {"status": "success", "indexed": indexed_count}
        
        except Exception as e:
            logger.error(f"Error fetching paypal plans: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_paypal_transactions(self, access_token: str, project_id: str, start_date: str, end_date: str):
        """Fetch all PayPal transactions and index them"""
        indexed_count = 0
        try:
            paypal_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            
            # Transaction Search requires date range (max 31 days)
            transactions_api_path = os.getenv("PAYPAL_TRANSACTIONS_URL", "/v1/reporting/transactions")
            transactions_url = f"{api_host_url}{transactions_api_path}"
            params = {
                "start_date": start_date,  # ISO 8601 format
                "end_date": end_date,
                "fields": "all",
                "page_size": 500
            }
            
            page = 1
            while True:
                params["page"] = page
                response = requests.get(transactions_url, headers=paypal_headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                transactions = data.get("transaction_details", [])
                if not transactions:
                    break
                
                for transaction in transactions:
                    trans_info = transaction.get("transaction_info", {})
                    doc = {
                        "project_id": project_id,
                        "transaction_id": f"{project_id}_{trans_info.get('transaction_id')}",
                        "transaction_info": trans_info,
                        "payer_info": transaction.get("payer_info", {}),
                        "shipping_info": transaction.get("shipping_info", {}),
                        "cart_info": transaction.get("cart_info", {}),
                        "data": transaction,
                        "last_synced": datetime.utcnow().isoformat(),
                    }
                    
                    paypal_transactions = self.mongodb.get_collection("paypal_transactions")
                    await paypal_transactions.update_one(
                        {
                            "project_id": project_id,
                            "transaction_id": doc["transaction_id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )
                    es_id = self.generate_hash(f"{doc.get('transaction_id')}")
                    self.elastic.index_document(index="paypal_transactions", document=doc, id=es_id)
                    indexed_count += 1
                
                # Check if there are more pages
                total_pages = data.get("total_pages", 1)
                if page >= total_pages:
                    break
                page += 1
            
            return {"status": "success", "indexed": indexed_count}
        
        except Exception as e:
            logger.error(f"Error fetching paypal transactions: {e}")
            return {"status": "error", "message": str(e)}
        
    async def sync_paypal_disputes(self, access_token: str, project_id: str):
        """Fetch all PayPal disputes and index them"""
        indexed_count = 0
        try:
            paypal_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            disputes_api_path = os.getenv("PAYPAL_DISPUTES_URL", "/v1/customer/disputes")
            disputes_url = f"{api_host_url}{disputes_api_path}"
            params = {
                "page_size": 50,
                "disputed_transaction_id": "",
                "start_time": (datetime.utcnow() - timedelta(days=180)).isoformat(),
            }
            
            get_disputes_url = disputes_url
            while get_disputes_url:
                response = requests.get(get_disputes_url, headers=paypal_headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                for dispute in data.get("items", []):
                    doc = {
                        "project_id": project_id,
                        "dispute_id": f"{project_id}_{dispute.get('dispute_id')}",
                        "reason": dispute.get("reason"),
                        "status": dispute.get("status"),
                        "dispute_state": dispute.get("dispute_state"),
                        "dispute_life_cycle_stage": dispute.get("dispute_life_cycle_stage"),
                        "dispute_channel": dispute.get("dispute_channel"),
                        "dispute_amount": dispute.get("dispute_amount"),
                        "create_time": dispute.get("create_time"),
                        "update_time": dispute.get("update_time"),
                        "disputed_transaction_id": dispute.get("disputed_transactions", [{}])[0].get("seller_transaction_id"),
                        "data": dispute,
                        "last_synced": datetime.utcnow().isoformat(),
                    }
                    
                    paypal_disputes = self.mongodb.get_collection("paypal_disputes")
                    await paypal_disputes.update_one(
                        {
                            "project_id": project_id,
                            "dispute_id": doc["dispute_id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )
                    es_id = self.generate_hash(f"{doc.get('dispute_id')}")
                    self.elastic.index_document(index="paypal_disputes", document=doc, id=es_id)
                    indexed_count += 1
                
                # Get next page link
                next_page = data.get("links", [])
                get_disputes_url = next((link["href"] for link in next_page if link["rel"] == "next"), None)
                params = {}  # Clear params for subsequent requests as URL has them
            
            return {"status": "success", "indexed": indexed_count}
        
        except Exception as e:
            logger.error(f"Error fetching paypal disputes: {e}")
            return {"status": "error", "message": str(e)}
        
    async def remove_paypal_secret_key(self, project_id: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$unset": {"paypal_client_id": 1, "paypal_client_secret": 1}},
        )
        return True if project.modified_count > 0 else False
    
    async def disconnect_paypal(self, project_id: str):
        # remove paypal data from elasticsearch and mongodb
        status = self.es_remove_paypal_data(project_id)
        prefix = "paypal_"
        collections = await self.mongodb.list_collections()

        collections = [c for c in collections if c.startswith(prefix)]
        # 3. Remove documents where project_id exists
        for col_name in collections:
            col = self.mongodb.get_collection(col_name)
            result = await col.delete_many({"project_id": project_id})
            logger.info(f"Deleted {result.deleted_count} documents from {col_name}")
        return status
    
    def es_remove_paypal_data(self, project_id: str) -> bool:
        """
        Remove all Paypal-related data for a given project from Elasticsearch.
        """
        if not project_id:
            return False
        indices = []
        indices = self.elastic.list_indices(pattern="paypal_*")

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
                logger.info(f"Deleted Paypal data from index: {index} for project_id: {project_id}")
            except exceptions.NotFoundError:
                logger.error(f"Index not found: {index}, skipping.")
            except Exception as e:
                logger.error(f"Error deleting data from index {index}: {str(e)}")
                return False
        return True
    
ServiceRegistry.register_service("paypal", PaypalService())
