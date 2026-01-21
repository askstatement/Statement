import os
import base64
import requests
from bson import ObjectId
from typing import Optional
from datetime import datetime
from elasticsearch import exceptions
from core.base_service import BaseService
from core.registry import ServiceRegistry
from core.logger import Logger

logger = Logger(__name__)


class XeroService(BaseService):
    name = "xero"
    
    def parse_xero_date(self, date_string):
        """Parse Xero date format /Date(milliseconds+timezone)/ and return Unix timestamp (seconds)."""
        if not date_string:
            return None
        try:
            # Extract milliseconds:
            # Works for formats like: /Date(1762128000000+0000)/ or /Date(1762128000000-0500)/
            inner = date_string.split("(")[1].split(")")[0]

            # Strip timezone part (+0000 or -0500)
            if "+" in inner:
                millis = inner.split("+")[0]
            elif "-" in inner[1:]:  # ignore minus sign of a negative timestamp
                millis = inner.split("-")[0]
            else:
                millis = inner

            millis = int(millis)

            # Convert milliseconds → seconds for Stripe-style timestamps
            return int(millis / 1000)

        except:
            return None
    
    async def xero_oauth_callback(self, code: str, code_verifier: str):
        """Handles Xero OAuth callback to exchange code for access token."""
        try:
            redirect_uri = os.getenv("XERO_REDIRECT_URI")
            # Prepare Basic Auth credentials
            client_id = os.getenv("XERO_CLIENT_ID")
            client_secret = os.getenv("XERO_CLIENT_SECRET")
            credentials = f"{client_id}:{client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded_credentials}",
            }
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": os.getenv("XERO_CLIENT_ID"),
                "code_verifier": code_verifier,
            }

            response = requests.post(
                "https://identity.xero.com/connect/token", headers=headers, data=data
            )
            response.raise_for_status()
            token_data = response.json()
            logger.info(f"token_data: {token_data}")

            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            return access_token, refresh_token

        except Exception as e:
            logger.error(f"Error in Xero OAuth callback: {e}")
            return False, False
            
    async def sync_xero_tenants(self, access_token: str, project_id: str):
        """Fetch Xero tenants info (via connections API) and index it / store it."""
        try:
            xero_headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            tenants_path = os.getenv("XERO_TENANTS_URL", "https://api.xero.com/connections")

            response = requests.get(tenants_path, headers=xero_headers)
            response.raise_for_status()
            tenants = response.json()  # This returns an array of tenant connections

            # Store all tenants for this project
            stored_tenants = []
            for tenant in tenants:
                doc = {
                    "project_id": project_id,
                    "tenantId": tenant.get("tenantId"),
                    "tenantName": tenant.get("tenantName"),
                    "tenantType": tenant.get("tenantType"),
                    "createdDateUtc": tenant.get("createdDateUtc"),
                    "updatedDateUtc": tenant.get("updatedDateUtc"),
                    "cleaned_data": tenant,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                xero_tenants = self.mongodb.get_collection("xero_tenants")
                await xero_tenants.update_one(
                    {"project_id": project_id, "tenantId": doc["tenantId"]},
                    {"$set": doc},
                    upsert=True,
                )

                # Index to Elasticsearch
                es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('tenantId')}")
                self.elastic.index_document(index="xero_tenants", document=doc, id=es_id)
                stored_tenants.append(doc)
                logger.info(
                    f"Indexed Xero tenant: {tenant.get('tenantName')} ({tenant.get('tenantId')})"
                )

            return {
                "status": "success",
                "tenants": stored_tenants,
                "count": len(stored_tenants),
            }
        except Exception as e:
            logger.error(f"Error fetching Xero tenants: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def sync_xero_invoices(self, access_token: str, project_id: str):
        """Fetch Xero invoices for a tenant and index them / store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(
                length=None
            )
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            stored_invoices = []
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]

                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,  # CRITICAL: Required for all Xero API calls
                }

                # Xero supports pagination - fetch all invoices
                page = 1
                all_invoices = []

                while True:
                    # Note: page parameter is required to get line items
                    invoices_url = f"https://api.xero.com/api.xro/2.0/Invoices?page={page}"

                    response = requests.get(invoices_url, headers=xero_headers)
                    response.raise_for_status()
                    data = response.json()

                    invoices = data.get("Invoices", [])
                    if not invoices:
                        break

                    all_invoices.extend(invoices)

                    # If we got less than 100 invoices, we've reached the end
                    if len(invoices) < 100:
                        break

                    page += 1

                # Store all invoices for this tenant
                for invoice in all_invoices:
                    contact = invoice.get("Contact", {})

                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "InvoiceID": invoice.get("InvoiceID"),
                        "InvoiceNumber": invoice.get("InvoiceNumber"),
                        "type": invoice.get("Type"),
                        "status": invoice.get("Status"),
                        "ContactID": contact.get("ContactID"),
                        "ContactName": contact.get("Name"),
                        "date": self.parse_xero_date(invoice.get("Date")),
                        "DueDate": self.parse_xero_date(invoice.get("DueDate")),
                        "reference": invoice.get("Reference"),
                        "CurrencyCode": invoice.get("CurrencyCode"),
                        "CurrencyRate": invoice.get("CurrencyRate"),
                        "LineAmountTypes": invoice.get("LineAmountTypes"),
                        "SubTotal": invoice.get("SubTotal"),
                        "TotalTax": invoice.get("TotalTax"),
                        "total": invoice.get("Total"),
                        "AmountDue": invoice.get("AmountDue"),
                        "AmountPaid": invoice.get("AmountPaid"),
                        "AmountCredited": invoice.get("AmountCredited"),
                        "FullyPaidOnDate": self.parse_xero_date(
                            invoice.get("FullyPaidOnDate")
                        ),
                        "UpdatedDateUTC": self.parse_xero_date(invoice.get("UpdatedDateUTC")),
                        "HasAttachments": invoice.get("HasAttachments", False),
                        "IsDiscounted": invoice.get("IsDiscounted", False),
                        "LineItems": invoice.get("LineItems", []),
                        "Payments": invoice.get("Payments", []),
                        "cleaned_data": invoice,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_invoices = self.mongodb.get_collection("xero_invoices")
                    await xero_invoices.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "InvoiceID": doc["InvoiceID"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('InvoiceID')}")
                    self.elastic.index_document(index="xero_invoices", document=doc, id=es_id)
                    stored_invoices.append(doc)
                    logger.info(
                        f"Indexed Xero invoice: {invoice.get('InvoiceNumber')} ({invoice.get('InvoiceID')})"
                    )

            return {"status": "success", "count": len(stored_invoices)}
        except Exception as e:
            logger.error(f"Error fetching Xero invoices: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def sync_xero_accounts(self, access_token: str, project_id: str):
        """Fetch Xero chart of accounts for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(
                length=None
            )

            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored_accounts = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]

                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                # Fetch all accounts for this tenant
                accounts_url = "https://api.xero.com/api.xro/2.0/Accounts"

                response = requests.get(accounts_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()

                accounts = data.get("Accounts", [])

                # Store all accounts for this tenant
                stored_accounts = []
                for account in accounts:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "AccountID": account.get("AccountID"),
                        "Code": account.get("Code"),
                        "Name": account.get("Name"),
                        "Type": account.get("Type"),
                        "TaxType": account.get("TaxType"),
                        "Description": account.get("Description"),
                        "Status": account.get("Status"),
                        "Class": account.get("Class"),
                        "EnablePaymentsToAccount": account.get(
                            "EnablePaymentsToAccount", False
                        ),
                        "ShowInExpenseClaims": account.get("ShowInExpenseClaims", False),
                        "BankAccountNumber": account.get("BankAccountNumber"),
                        "BankAccountType": account.get("BankAccountType"),
                        "CurrencyCode": account.get("CurrencyCode"),
                        "ReportingCode": account.get("ReportingCode"),
                        "ReportingCodeName": account.get("ReportingCodeName"),
                        "HasAttachments": account.get("HasAttachments", False),
                        "UpdatedDateUTC": self.parse_xero_date(account.get("UpdatedDateUTC")),
                        "cleaned_data": account,  # Store complete raw account data
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_accounts = self.mongodb.get_collection("xero_accounts")
                    await xero_accounts.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "AccountID": doc["AccountID"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('AccountID')}")
                    self.elastic.index_document(index="xero_accounts", document=doc, id=es_id)
                    stored_accounts.append(doc)
                    logger.info(
                        f"Indexed Xero account: {account.get('Name')} ({account.get('Code')})"
                    )

                all_stored_accounts.extend(stored_accounts)
                logger.info(f"Synced {len(stored_accounts)} accounts for tenant {tenantId}")

            return {
                "status": "success",
                "accounts": all_stored_accounts,
                "count": len(all_stored_accounts),
                "tenants_synced": len(tenants_list),
            }
        except Exception as e:
            logger.error(f"Error fetching Xero accounts: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def sync_xero_bank_transactions(self, access_token: str, project_id: str):
        """Fetch Xero bank transactions for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(
                length=None
            )

            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored_transactions = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]

                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                # Xero supports pagination - fetch all bank transactions
                page = 1
                tenant_transactions = []

                while True:
                    # Use pagination to fetch bank transactions
                    bank_transactions_url = (
                        f"https://api.xero.com/api.xro/2.0/BankTransactions?page={page}"
                    )

                    response = requests.get(bank_transactions_url, headers=xero_headers)
                    response.raise_for_status()
                    data = response.json()

                    transactions = data.get("BankTransactions", [])
                    if not transactions:
                        break

                    tenant_transactions.extend(transactions)

                    # If we got less than 100 transactions, we've reached the end
                    if len(transactions) < 100:
                        break

                    page += 1

                # Store all bank transactions for this tenant
                for transaction in tenant_transactions:
                    contact = transaction.get("Contact", {})
                    bank_account = transaction.get("BankAccount", {})

                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "BankTransactionID": transaction.get("BankTransactionID"),
                        "Type": transaction.get("Type"),
                        "Status": transaction.get("Status"),
                        "ContactID": contact.get("ContactID"),
                        "ContactName": contact.get("Name"),
                        "BankAccountID": bank_account.get("AccountID"),
                        "BankAccountCode": bank_account.get("Code"),
                        "BankAccountName": bank_account.get("Name"),
                        "date": self.parse_xero_date(transaction.get("Date")),
                        "Reference": transaction.get("Reference"),
                        "IsReconciled": transaction.get("IsReconciled", False),
                        "CurrencyCode": transaction.get("CurrencyCode"),
                        "CurrencyRate": transaction.get("CurrencyRate"),
                        "LineAmountTypes": transaction.get("LineAmountTypes"),
                        "SubTotal": transaction.get("SubTotal"),
                        "TotalTax": transaction.get("TotalTax"),
                        "Total": transaction.get("Total"),
                        "Url": transaction.get("Url"),
                        "HasAttachments": transaction.get("HasAttachments", False),
                        "PrepaymentID": transaction.get("PrepaymentID"),
                        "OverpaymentID": transaction.get("OverpaymentID"),
                        "LineItems": transaction.get("LineItems", []),
                        "UpdatedDateUTC": self.parse_xero_date(
                            transaction.get("UpdatedDateUTC")
                        ),
                        "cleaned_data": transaction,  # Store complete raw transaction data
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_bank_transactions = self.mongodb.get_collection("xero_bank_transactions")
                    await xero_bank_transactions.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "BankTransactionID": doc["BankTransactionID"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('BankTransactionID')}")
                    self.elastic.index_document(index="xero_bank_transactions", document=doc, id=es_id)
                    all_stored_transactions.append(doc)
                    logger.info(
                        f"Indexed Xero bank transaction: {transaction.get('Reference')} ({transaction.get('BankTransactionID')})"
                    )

                logger.info(
                    f"Synced {len(tenant_transactions)} bank transactions for tenant {tenantId}"
                )

            return {
                "status": "success",
                "bank_transactions": all_stored_transactions,
                "count": len(all_stored_transactions),
                "tenants_synced": len(tenants_list),
            }
        except Exception as e:
            logger.error(f"Error fetching Xero bank transactions: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def sync_xero_bank_transfers(self, access_token: str, project_id: str):
        """Fetch Xero bank transfers for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(
                length=None
            )

            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored_transfers = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]

                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                # Fetch all bank transfers for this tenant
                # Note: Bank transfers typically don't require pagination as there are fewer of them
                bank_transfers_url = "https://api.xero.com/api.xro/2.0/BankTransfers"

                response = requests.get(bank_transfers_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()

                transfers = data.get("BankTransfers", [])

                # Store all bank transfers for this tenant
                for transfer in transfers:
                    from_bank_account = transfer.get("FromBankAccount", {})
                    to_bank_account = transfer.get("ToBankAccount", {})

                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "BankTransferID": transfer.get("BankTransferID"),
                        "date": self.parse_xero_date(transfer.get("Date")),
                        "FromBankAccountID": from_bank_account.get("AccountID"),
                        "FromBankAccountCode": from_bank_account.get("Code"),
                        "FromBankAccountName": from_bank_account.get("Name"),
                        "ToBankAccountID": to_bank_account.get("AccountID"),
                        "ToBankAccountCode": to_bank_account.get("Code"),
                        "ToBankAccountName": to_bank_account.get("Name"),
                        "Amount": transfer.get("Amount"),
                        "FromBankTransactionID": transfer.get("FromBankTransactionID"),
                        "ToBankTransactionID": transfer.get("ToBankTransactionID"),
                        "CurrencyRate": transfer.get("CurrencyRate"),
                        "FromIsReconciled": transfer.get("FromIsReconciled", False),
                        "ToIsReconciled": transfer.get("ToIsReconciled", False),
                        "Reference": transfer.get("Reference"),
                        "HasAttachments": transfer.get("HasAttachments", False),
                        "CreatedDateUTC": self.parse_xero_date(transfer.get("CreatedDateUTC")),
                        "cleaned_data": transfer,  # Store complete raw transfer data
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_bank_transfers = self.mongodb.get_collection("xero_bank_transfers")
                    await xero_bank_transfers.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "BankTransferID": doc["BankTransferID"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('BankTransferID')}")
                    self.elastic.index_document(index="xero_bank_transfers", document=doc, id=es_id)
                    all_stored_transfers.append(doc)
                    logger.info(
                        f"Indexed Xero bank transfer: {transfer.get('Amount')} from {from_bank_account.get('Name')} to {to_bank_account.get('Name')}"
                    )

                logger.info(f"Synced {len(transfers)} bank transfers for tenant {tenantId}")

            return {
                "status": "success",
                "bank_transfers": all_stored_transfers,
                "count": len(all_stored_transfers),
                "tenants_synced": len(tenants_list),
            }
        except Exception as e:
            logger.error(f"Error fetching Xero bank transfers: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def sync_xero_batch_payments(self, access_token: str, project_id: str):
        """Fetch Xero batch payments for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(
                length=None
            )

            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored_batch_payments = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]

                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                # Fetch all batch payments for this tenant
                batch_payments_url = "https://api.xero.com/api.xro/2.0/BatchPayments"

                response = requests.get(batch_payments_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()

                batch_payments = data.get("BatchPayments", [])

                # Store all batch payments for this tenant
                for batch_payment in batch_payments:
                    account = batch_payment.get("Account", {})

                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "BatchPaymentID": batch_payment.get("BatchPaymentID"),
                        "AccountID": account.get("AccountID"),
                        "AccountCode": account.get("Code"),
                        "AccountName": account.get("Name"),
                        "Reference": batch_payment.get("Reference"),
                        "Particulars": batch_payment.get("Particulars"),
                        "Code": batch_payment.get("Code"),
                        "Details": batch_payment.get("Details"),
                        "Narrative": batch_payment.get("Narrative"),
                        "date": self.parse_xero_date(batch_payment.get("Date")),
                        "Amount": batch_payment.get("Amount"),
                        "Type": batch_payment.get("Type"),
                        "Status": batch_payment.get("Status"),
                        "TotalAmount": batch_payment.get("TotalAmount"),
                        "IsReconciled": batch_payment.get("IsReconciled", False),
                        "Payments": batch_payment.get("Payments", []),
                        "UpdatedDateUTC": self.parse_xero_date(
                            batch_payment.get("UpdatedDateUTC")
                        ),
                        "cleaned_data": batch_payment,  # Store complete raw batch payment data
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_batch_payments = self.mongodb.get_collection("xero_batch_payments")
                    await xero_batch_payments.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "BatchPaymentID": doc["BatchPaymentID"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('BatchPaymentID')}")
                    self.elastic.index_document(index="xero_batch_payments", document=doc, id=es_id)
                    all_stored_batch_payments.append(doc)
                    logger.info(
                        f"Indexed Xero batch payment: {batch_payment.get('Reference')} - Total: {batch_payment.get('TotalAmount')}"
                    )

                logger.info(f"Synced {len(batch_payments)} batch payments for tenant {tenantId}")

            return {
                "status": "success",
                "batch_payments": all_stored_batch_payments,
                "count": len(all_stored_batch_payments),
                "tenants_synced": len(tenants_list),
            }
        except Exception as e:
            logger.error(f"Error fetching Xero batch payments: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_xero_budgets(self, access_token: str, project_id: str):
        """Fetch Xero budgets for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(
                length=None
            )

            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored_budgets = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]

                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                # Fetch all budgets for this tenant
                budgets_url = "https://api.xero.com/api.xro/2.0/Budgets"
                
                response = requests.get(budgets_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()

                budgets = data.get("Budgets", [])

                # Store all budgets for this tenant
                for budget in budgets:
                    # Process budget lines
                    budget_lines = []
                    for line in budget.get("BudgetLines", []):
                        budget_line = {
                            "AccountID": line.get("AccountID"),
                            "AccountCode": line.get("AccountCode"),
                            "Name": line.get("AccountName"),
                            "budget_balances": []
                        }
                        
                        # Process budget balances
                        for balance in line.get("BudgetBalances", []):
                            budget_balance = {
                                "period": self.parse_xero_date(balance.get("Period")),
                                "amount": balance.get("Amount"),
                                "unit_amount": balance.get("UnitAmount")
                            }
                            budget_line["budget_balances"].append(budget_balance)
                        
                        budget_lines.append(budget_line)

                    # Process tracking categories if they exist
                    tracking_categories = budget.get("Tracking", [])
                    processed_tracking_categories = []
                    
                    for tracking_cat in tracking_categories:
                        tracking_category = {
                            "TrackingCategoryID": tracking_cat.get("TrackingCategoryID"),
                            "Name": tracking_cat.get("Name"),
                            "options": []
                        }
                        
                        for option in tracking_cat.get("Options", []):
                            tracking_option = {
                                "TrackingOptionID": option.get("TrackingOptionID"),
                                "Name": option.get("Name")
                            }
                            tracking_category["options"].append(tracking_option)
                        
                        processed_tracking_categories.append(tracking_category)

                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "BudgetID": budget.get("BudgetID"),
                        "Type": budget.get("Type"),
                        "Description": budget.get("Description"),
                        "UpdatedDateUTC": self.parse_xero_date(budget.get("UpdatedDateUTC")),
                        "BudgetLines": budget_lines,
                        "Tracking": processed_tracking_categories,
                        "cleaned_data": budget,  # Store complete raw budget data
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_budgets = self.mongodb.get_collection("xero_budgets")
                    await xero_budgets.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "BudgetID": doc["BudgetID"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('BudgetID')}")
                    self.elastic.index_document(index="xero_budgets", document=doc, id=es_id)
                    all_stored_budgets.append(doc)
                    logger.info(
                        f"Indexed Xero budget: {budget.get('Description')} - Type: {budget.get('Type')}"
                    )

                logger.info(f"Synced {len(budgets)} budgets for tenant {tenantId}")

            return {
                "status": "success",
                "budgets": all_stored_budgets,
                "count": len(all_stored_budgets),
                "tenants_synced": len(tenants_list),
            }
        except Exception as e:
            logger.error(f"Error fetching Xero budgets: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_xero_contact_groups(self, access_token: str, project_id: str):
        """Fetch Xero contact groups for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_contact_groups = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }
                
                # Fetch all contact groups for this tenant
                contact_groups_url = "https://api.xero.com/api.xro/2.0/ContactGroups"
                
                response = requests.get(contact_groups_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()
                
                contact_groups = data.get("ContactGroups", [])
                
                # Store all contact groups for this tenant
                for contact_group in contact_groups:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "ContactGroupID": contact_group.get("ContactGroupID"),
                        "Name": contact_group.get("Name"),
                        "Status": contact_group.get("Status"),
                        "Contacts": contact_group.get("Contacts", []),
                        "cleaned_data": contact_group,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_contact_groups = self.mongodb.get_collection("xero_contact_groups")
                    await xero_contact_groups.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "ContactGroupID": doc["ContactGroupID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('ContactGroupID')}")
                    self.elastic.index_document(index="xero_contact_groups", document=doc, id=es_id)
                    all_stored_contact_groups.append(doc)
                    logger.info(f"Indexed Xero contact group: {contact_group.get('Name')}")
                
                logger.info(f"Synced {len(contact_groups)} contact groups for tenant {tenantId}")

            return {
                "status": "success",
                "contact_groups": all_stored_contact_groups,
                "count": len(all_stored_contact_groups),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero contact groups: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_xero_contacts(self, access_token: str, project_id: str):
        """Fetch Xero contacts for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_contacts = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }
                
                # Xero supports pagination for contacts - fetch all contacts
                page = 1
                tenant_contacts = []
                
                while True:
                    # Important: Use page parameter to get full contact details including ContactGroups
                    contacts_url = f"https://api.xero.com/api.xro/2.0/Contacts?page={page}"
                    
                    response = requests.get(contacts_url, headers=xero_headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    contacts = data.get("Contacts", [])
                    if not contacts:
                        break
                    
                    tenant_contacts.extend(contacts)
                    
                    # If we got less than 100 contacts, we've reached the end
                    if len(contacts) < 100:
                        break
                    
                    page += 1
                
                # Store all contacts for this tenant
                for contact in tenant_contacts:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "ContactID": contact.get("ContactID"),
                        "ContactNumber": contact.get("ContactNumber"),
                        "AccountNumber": contact.get("AccountNumber"),
                        "ContactStatus": contact.get("ContactStatus"),
                        "Name": contact.get("Name"),
                        "FirstName": contact.get("FirstName"),
                        "LastName": contact.get("LastName"),
                        "EmailAddress": contact.get("EmailAddress"),
                        "SkypeUserName": contact.get("SkypeUserName"),
                        "BankAccountDetails": contact.get("BankAccountDetails"),
                        "TaxNumber": contact.get("TaxNumber"),
                        "AccountsReceivableTaxType": contact.get("AccountsReceivableTaxType"),
                        "AccountsPayableTaxType": contact.get("AccountsPayableTaxType"),
                        "IsSupplier": contact.get("IsSupplier", False),
                        "IsCustomer": contact.get("IsCustomer", False),
                        "DefaultCurrency": contact.get("DefaultCurrency"),
                        "Website": contact.get("Website"),
                        "Discount": contact.get("Discount"),
                        "Addresses": contact.get("Addresses", []),
                        "Phones": contact.get("Phones", []),
                        "ContactGroups": contact.get("ContactGroups", []),
                        "ContactPersons": contact.get("ContactPersons", []),
                        "Balances": contact.get("Balances"),
                        "HasAttachments": contact.get("HasAttachments", False),
                        "UpdatedDateUTC": self.parse_xero_date(contact.get("UpdatedDateUTC")),
                        "cleaned_data": contact,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_contacts = self.mongodb.get_collection("xero_contacts")
                    await xero_contacts.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "ContactID": doc["ContactID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('ContactID')}")
                    self.elastic.index_document(index="xero_contacts", document=doc, id=es_id)
                    all_stored_contacts.append(doc)
                    logger.info(f"Indexed Xero contact: {contact.get('Name')} ({contact.get('ContactID')})")
                
                logger.info(f"Synced {len(tenant_contacts)} contacts for tenant {tenantId}")

            return {
                "status": "success",
                "contacts": all_stored_contacts,
                "count": len(all_stored_contacts),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero contacts: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_xero_credit_notes(self, access_token: str, project_id: str):
        """Fetch Xero credit notes for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_credit_notes = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }
                
                # Xero supports pagination for credit notes - fetch all
                page = 1
                tenant_credit_notes = []
                
                while True:
                    # Use pagination to get full line items
                    credit_notes_url = f"https://api.xero.com/api.xro/2.0/CreditNotes?page={page}"
                    
                    response = requests.get(credit_notes_url, headers=xero_headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    credit_notes = data.get("CreditNotes", [])
                    if not credit_notes:
                        break
                    
                    tenant_credit_notes.extend(credit_notes)
                    
                    # If we got less than 100 credit notes, we've reached the end
                    if len(credit_notes) < 100:
                        break
                    
                    page += 1
                
                # Store all credit notes for this tenant
                for credit_note in tenant_credit_notes:
                    contact = credit_note.get("Contact", {})
                    
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "CreditNoteID": credit_note.get("CreditNoteID"),
                        "CreditNoteNumber": credit_note.get("CreditNoteNumber"),
                        "Type": credit_note.get("Type"),
                        "Status": credit_note.get("Status"),
                        "ContactID": contact.get("ContactID"),
                        "ContactName": contact.get("Name"),
                        "date": self.parse_xero_date(credit_note.get("Date")),
                        "DueDate": self.parse_xero_date(credit_note.get("DueDate")),
                        "Reference": credit_note.get("Reference"),
                        "CurrencyCode": credit_note.get("CurrencyCode"),
                        "CurrencyRate": credit_note.get("CurrencyRate"),
                        "LineAmountTypes": credit_note.get("LineAmountTypes"),
                        "SubTotal": credit_note.get("SubTotal"),
                        "TotalTax": credit_note.get("TotalTax"),
                        "Total": credit_note.get("Total"),
                        "RemainingCredit": credit_note.get("RemainingCredit"),
                        "AppliedAmount": credit_note.get("AppliedAmount"),
                        "FullyPaidOnDate": self.parse_xero_date(credit_note.get("FullyPaidOnDate")),
                        "BrandingThemeID": credit_note.get("BrandingThemeID"),
                        "SentToContact": credit_note.get("SentToContact", False),
                        "HasAttachments": credit_note.get("HasAttachments", False),
                        "LineItems": credit_note.get("LineItems", []),
                        "Allocations": credit_note.get("Allocations", []),
                        "Payments": credit_note.get("Payments", []),
                        "UpdatedDateUTC": self.parse_xero_date(credit_note.get("UpdatedDateUTC")),
                        "cleaned_data": credit_note,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_credit_notes = self.mongodb.get_collection("xero_credit_notes")
                    await xero_credit_notes.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "CreditNoteID": doc["CreditNoteID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('CreditNoteID')}")
                    self.elastic.index_document(index="xero_credit_notes", document=doc, id=es_id)
                    all_stored_credit_notes.append(doc)
                    logger.info(f"Indexed Xero credit note: {credit_note.get('CreditNoteNumber')} ({credit_note.get('CreditNoteID')})")
                
                logger.info(f"Synced {len(tenant_credit_notes)} credit notes for tenant {tenantId}")

            return {
                "status": "success",
                "credit_notes": all_stored_credit_notes,
                "count": len(all_stored_credit_notes),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero credit notes: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def sync_xero_linked_transactions(self, access_token: str, project_id: str):
        """Fetch Xero linked transactions for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_linked_transactions = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }
                
                # Fetch linked transactions with pagination
                page = 1
                tenant_linked_transactions = []
                
                while True:
                    linked_transactions_url = f"https://api.xero.com/api.xro/2.0/LinkedTransactions?page={page}"
                    
                    response = requests.get(linked_transactions_url, headers=xero_headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    linked_transactions = data.get("LinkedTransactions", [])
                    if not linked_transactions:
                        break
                    
                    tenant_linked_transactions.extend(linked_transactions)
                    
                    # If we got less than 100 linked transactions, we've reached the end
                    if len(linked_transactions) < 100:
                        break
                    
                    page += 1
                
                # Store all linked transactions for this tenant
                for linked_transaction in tenant_linked_transactions:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "LinkedTransactionID": linked_transaction.get("LinkedTransactionID"),
                        "SourceTransactionID": linked_transaction.get("SourceTransactionID"),
                        "SourceLineItemID": linked_transaction.get("SourceLineItemID"),
                        "SourceTransactionTypeCode": linked_transaction.get("SourceTransactionTypeCode"),
                        "ContactID": linked_transaction.get("ContactID"),
                        "TargetTransactionID": linked_transaction.get("TargetTransactionID"),
                        "TargetLineItemID": linked_transaction.get("TargetLineItemID"),
                        "Status": linked_transaction.get("Status"),
                        "Type": linked_transaction.get("Type"),
                        "UpdatedDateUTC": self.parse_xero_date(linked_transaction.get("UpdatedDateUTC")),
                        "cleaned_data": linked_transaction,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_linked_transactions = self.mongodb.get_collection("xero_linked_transactions")
                    await xero_linked_transactions.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "LinkedTransactionID": doc["LinkedTransactionID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('LinkedTransactionID')}")
                    self.elastic.index_document(index="xero_linked_transactions", document=doc, id=es_id)
                    all_stored_linked_transactions.append(doc)
                    logger.info(f"Indexed Xero linked transaction: {linked_transaction.get('LinkedTransactionID')}")
                
                logger.info(f"Synced {len(tenant_linked_transactions)} linked transactions for tenant {tenantId}")

            return {
                "status": "success",
                "linked_transactions": all_stored_linked_transactions,
                "count": len(all_stored_linked_transactions),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero linked transactions: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_xero_journals(self, access_token: str, project_id: str):
        """Fetch Xero journals for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_journals = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }
                
                # Fetch journals with pagination (offset-based)
                offset = 0
                tenant_journals = []
                
                while True:
                    journals_url = f"https://api.xero.com/api.xro/2.0/Journals?offset={offset}"
                    
                    response = requests.get(journals_url, headers=xero_headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    journals = data.get("Journals", [])
                    if not journals:
                        break
                    
                    tenant_journals.extend(journals)
                    
                    # If we got less than 100 journals, we've reached the end
                    if len(journals) < 100:
                        break
                    
                    offset += 100
                
                # Store all journals for this tenant
                for journal in tenant_journals:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "JournalID": journal.get("JournalID"),
                        "JournalDate": self.parse_xero_date(journal.get("JournalDate")),
                        "JournalNumber": journal.get("JournalNumber"),
                        "CreatedDateUTC": self.parse_xero_date(journal.get("CreatedDateUTC")),
                        "Reference": journal.get("Reference"),
                        "SourceID": journal.get("SourceID"),
                        "SourceType": journal.get("SourceType"),
                        "JournalLines": journal.get("JournalLines", []),
                        "cleaned_data": journal,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_journals = self.mongodb.get_collection("xero_journals")
                    await xero_journals.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "JournalID": doc["JournalID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('JournalID')}")
                    self.elastic.index_document(index="xero_journals", document=doc, id=es_id)
                    all_stored_journals.append(doc)
                    logger.info(f"Indexed Xero journal: {journal.get('JournalNumber')} ({journal.get('JournalID')})")
                
                logger.info(f"Synced {len(tenant_journals)} journals for tenant {tenantId}")

            return {
                "status": "success",
                "journals": all_stored_journals,
                "count": len(all_stored_journals),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero journals: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def sync_xero_items(self, access_token: str, project_id: str):
        """Fetch Xero items for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_items = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }
                
                # Fetch all items for this tenant
                items_url = "https://api.xero.com/api.xro/2.0/Items"
                
                response = requests.get(items_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()
                
                items = data.get("Items", [])
                
                # Store all items for this tenant
                for item in items:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "ItemID": item.get("ItemID"),
                        "Code": item.get("Code"),
                        "Name": item.get("Name"),
                        "Description": item.get("Description"),
                        "PurchaseDescription": item.get("PurchaseDescription"),
                        "InventoryAssetAccountCode": item.get("InventoryAssetAccountCode"),
                        "IsSold": item.get("IsSold", False),
                        "IsPurchased": item.get("IsPurchased", False),
                        "IsTrackedAsInventory": item.get("IsTrackedAsInventory", False),
                        "TotalCostPool": item.get("TotalCostPool"),
                        "QuantityOnHand": item.get("QuantityOnHand"),
                        "PurchaseDetails": item.get("PurchaseDetails"),
                        "SalesDetails": item.get("SalesDetails"),
                        "UpdatedDateUTC": self.parse_xero_date(item.get("UpdatedDateUTC")),
                        "cleaned_data": item,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_items = self.mongodb.get_collection("xero_items")
                    await xero_items.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "ItemID": doc["ItemID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('ItemID')}")
                    self.elastic.index_document(index="xero_items", document=doc, id=es_id)
                    all_stored_items.append(doc)
                    logger.info(f"Indexed Xero item: {item.get('Name')} ({item.get('Code')})")
                
                logger.info(f"Synced {len(items)} items for tenant {tenantId}")

            return {
                "status": "success",
                "items": all_stored_items,
                "count": len(all_stored_items),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero items: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_xero_manual_journals(self, access_token: str, project_id: str):
        """Fetch Xero manual journals for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_manual_journals = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }
                
                # Fetch manual journals with pagination
                page = 1
                tenant_manual_journals = []
                
                while True:
                    manual_journals_url = f"https://api.xero.com/api.xro/2.0/ManualJournals?page={page}"
                    
                    response = requests.get(manual_journals_url, headers=xero_headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    manual_journals = data.get("ManualJournals", [])
                    if not manual_journals:
                        break
                    
                    tenant_manual_journals.extend(manual_journals)
                    
                    # If we got less than 100 manual journals, we've reached the end
                    if len(manual_journals) < 100:
                        break
                    
                    page += 1
                
                # Store all manual journals for this tenant
                for manual_journal in tenant_manual_journals:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "ManualJournalID": manual_journal.get("ManualJournalID"),
                        "Narration": manual_journal.get("Narration"),
                        "date": self.parse_xero_date(manual_journal.get("Date")),
                        "Status": manual_journal.get("Status"),
                        "LineAmountTypes": manual_journal.get("LineAmountTypes"),
                        "ShowOnCashBasisReports": manual_journal.get("ShowOnCashBasisReports", False),
                        "HasAttachments": manual_journal.get("HasAttachments", False),
                        "JournalLines": manual_journal.get("JournalLines", []),
                        "UpdatedDateUTC": self.parse_xero_date(manual_journal.get("UpdatedDateUTC")),
                        "cleaned_data": manual_journal,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_manual_journals = self.mongodb.get_collection("xero_manual_journals")
                    await xero_manual_journals.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "ManualJournalID": doc["ManualJournalID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('ManualJournalID')}")
                    self.elastic.index_document(index="xero_manual_journals", document=doc, id=es_id)
                    all_stored_manual_journals.append(doc)
                    logger.info(f"Indexed Xero manual journal: {manual_journal.get('Narration')} ({manual_journal.get('ManualJournalID')})")
                
                logger.info(f"Synced {len(tenant_manual_journals)} manual journals for tenant {tenantId}")

            return {
                "status": "success",
                "manual_journals": all_stored_manual_journals,
                "count": len(all_stored_manual_journals),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero manual journals: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def sync_xero_organisation(self, access_token: str, project_id: str):
        """Fetch Xero organisation details for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_organisations = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }
                
                # Fetch organisation details (returns array with single organisation)
                organisation_url = "https://api.xero.com/api.xro/2.0/Organisation"
                
                response = requests.get(organisation_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()
                
                organisations = data.get("Organisations", [])
                
                # Should only be one organisation per tenant
                for organisation in organisations:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "OrganisationID": organisation.get("OrganisationID"),
                        "Name": organisation.get("Name"),
                        "LegalName": organisation.get("LegalName"),
                        "PaysTax": organisation.get("PaysTax", False),
                        "Version": organisation.get("Version"),
                        "OrganisationType": organisation.get("OrganisationType"),
                        "BaseCurrency": organisation.get("BaseCurrency"),
                        "CountryCode": organisation.get("CountryCode"),
                        "IsDemoCompany": organisation.get("IsDemoCompany", False),
                        "OrganisationStatus": organisation.get("OrganisationStatus"),
                        "RegistrationNumber": organisation.get("RegistrationNumber"),
                        "EmployerIdentificationNumber": organisation.get("EmployerIdentificationNumber"),
                        "TaxNumber": organisation.get("TaxNumber"),
                        "FinancialYearEndDay": organisation.get("FinancialYearEndDay"),
                        "FinancialYearEndMonth": organisation.get("FinancialYearEndMonth"),
                        "SalesTaxBasis": organisation.get("SalesTaxBasis"),
                        "SalesTaxPeriod": organisation.get("SalesTaxPeriod"),
                        "DefaultSalesTax": organisation.get("DefaultSalesTax"),
                        "DefaultPurchasesTax": organisation.get("DefaultPurchasesTax"),
                        "PeriodLockDate": self.parse_xero_date(organisation.get("PeriodLockDate")),
                        "EndOfYearLockDate": self.parse_xero_date(organisation.get("EndOfYearLockDate")),
                        "CreatedDateUTC": self.parse_xero_date(organisation.get("CreatedDateUTC")),
                        "Timezone": organisation.get("Timezone"),
                        "OrganisationEntityType": organisation.get("OrganisationEntityType"),
                        "ShortCode": organisation.get("ShortCode"),
                        "Edition": organisation.get("Edition"),
                        "LineOfBusiness": organisation.get("LineOfBusiness"),
                        "Addresses": organisation.get("Addresses", []),
                        "Phones": organisation.get("Phones", []),
                        "ExternalLinks": organisation.get("ExternalLinks", []),
                        "PaymentTerms": organisation.get("PaymentTerms"),
                        "cleaned_data": organisation,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_organisation = self.mongodb.get_collection("xero_organisations")
                    await xero_organisation.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "OrganisationID": doc["OrganisationID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('OrganisationID')}")
                    self.elastic.index_document(index="xero_organisation", document=doc, id=es_id)
                    all_stored_organisations.append(doc)
                    logger.info(f"Indexed Xero organisation: {organisation.get('Name')} ({organisation.get('OrganisationID')})")
                
                logger.info(f"Synced organisation details for tenant {tenantId}")

            return {
                "status": "success",
                "organisations": all_stored_organisations,
                "count": len(all_stored_organisations),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero organisation: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_xero_overpayments(self, access_token: str, project_id: str):
        """Fetch Xero overpayments for all tenants and index them / store them."""
        try:
            # Fetch all tenants for this project
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_overpayments = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }
                
                # Fetch overpayments with pagination
                page = 1
                tenant_overpayments = []
                
                while True:
                    overpayments_url = f"https://api.xero.com/api.xro/2.0/Overpayments?page={page}"
                    
                    response = requests.get(overpayments_url, headers=xero_headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    overpayments = data.get("Overpayments", [])
                    if not overpayments:
                        break
                    
                    tenant_overpayments.extend(overpayments)
                    
                    # If we got less than 100 overpayments, we've reached the end
                    if len(overpayments) < 100:
                        break
                    
                    page += 1
                
                # Store all overpayments for this tenant
                for overpayment in tenant_overpayments:
                    contact = overpayment.get("Contact", {})
                    
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "OverpaymentID": overpayment.get("OverpaymentID"),
                        "Type": overpayment.get("Type"),
                        "Status": overpayment.get("Status"),
                        "ContactID": contact.get("ContactID"),
                        "ContactName": contact.get("Name"),
                        "date": self.parse_xero_date(overpayment.get("Date")),
                        "Reference": overpayment.get("Reference"),
                        "CurrencyCode": overpayment.get("CurrencyCode"),
                        "CurrencyRate": overpayment.get("CurrencyRate"),
                        "LineAmountTypes": overpayment.get("LineAmountTypes"),
                        "SubTotal": overpayment.get("SubTotal"),
                        "TotalTax": overpayment.get("TotalTax"),
                        "Total": overpayment.get("Total"),
                        "RemainingCredit": overpayment.get("RemainingCredit"),
                        "AppliedAmount": overpayment.get("AppliedAmount"),
                        "HasAttachments": overpayment.get("HasAttachments", False),
                        "LineItems": overpayment.get("LineItems", []),
                        "Allocations": overpayment.get("Allocations", []),
                        "Payments": overpayment.get("Payments", []),
                        "UpdatedDateUTC": self.parse_xero_date(overpayment.get("UpdatedDateUTC")),
                        "cleaned_data": overpayment,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    xero_over_payments = self.mongodb.get_collection("xero_over_payments")
                    await xero_over_payments.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "OverpaymentID": doc["OverpaymentID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('OverpaymentID')}")
                    self.elastic.index_document(index="xero_over_payments", document=doc, id=es_id)
                    all_stored_overpayments.append(doc)
                    logger.info(f"Indexed Xero overpayment: {overpayment.get('Reference')} ({overpayment.get('OverpaymentID')})")
                
                logger.info(f"Synced {len(tenant_overpayments)} overpayments for tenant {tenantId}")

            return {
                "status": "success",
                "overpayments": all_stored_overpayments,
                "count": len(all_stored_overpayments),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero overpayments: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_xero_payments(self, access_token: str, project_id: str):
        """Fetch Xero Payments for all tenants and index them / store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored_payments = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]

                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                payments_url = "https://api.xero.com/api.xro/2.0/Payments"
                response = requests.get(payments_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()

                payments = data.get("Payments", [])

                for payment in payments:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "PaymentID": payment.get("PaymentID"),
                        "InvoiceID": payment.get("Invoice", {}).get("InvoiceID"),
                        "AccountID": payment.get("Account", {}).get("AccountID"),
                        "Amount": payment.get("Amount"),
                        "date": self.parse_xero_date(payment.get("Date")),
                        "Status": payment.get("Status"),
                        "Type": "PAYMENT",
                        "cleaned_data": payment,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    xero_payments = self.mongodb.get_collection("xero_payments")
                    await xero_payments.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "PaymentID": doc["PaymentID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('PaymentID')}")
                    self.elastic.index_document(index="xero_payments", document=doc, id=es_id)
                    all_stored_payments.append(doc)
                    logger.info(f"Indexed Xero payment: {payment.get('PaymentID')}")

                logger.info(f"Synced {len(payments)} payments for tenant {tenantId}")

            return {
                "status": "success",
                "payments": all_stored_payments,
                "count": len(all_stored_payments),
                "tenants_synced": len(tenants_list)
            }

        except Exception as e:
            logger.error(f"Error fetching Xero payments: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_xero_prepayments(self, access_token: str, project_id: str):
        """Fetch Xero Prepayments for all tenants and index them / store them."""
        try:
            xero_tenants =  self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored_prepayments = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]

                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                prepayments_url = "https://api.xero.com/api.xro/2.0/Prepayments"
                response = requests.get(prepayments_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()

                prepayments = data.get("Prepayments", [])

                for prepayment in prepayments:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "PrepaymentID": prepayment.get("PrepaymentID"),
                        "ContactID": prepayment.get("Contact", {}).get("ContactID"),
                        "Amount": prepayment.get("Total"),
                        "date": self.parse_xero_date(prepayment.get("Date")),
                        "Status": prepayment.get("Status"),
                        "Type": "PREPAYMENT",
                        "cleaned_data": prepayment,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    xero_prepayments = self.mongodb.get_collection("xero_prepayments")
                    await xero_prepayments.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "PrepaymentID": doc["PrepaymentID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('PrepaymentID')}")
                    self.elastic.index_document(index="xero_prepayments", document=doc, id=es_id)
                    all_stored_prepayments.append(doc)
                    logger.info(f"Indexed Xero prepayment: {prepayment.get('PrepaymentID')}")

                logger.info(f"Synced {len(prepayments)} prepayments for tenant {tenantId}")

            return {
                "status": "success",
                "prepayments": all_stored_prepayments,
                "count": len(all_stored_prepayments),
                "tenants_synced": len(tenants_list)
            }

        except Exception as e:
            logger.error(f"Error fetching Xero prepayments: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_xero_purchase_orders(self, access_token: str, project_id: str):
        """Fetch Xero PurchaseOrders for all tenants and index/store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored_pos = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]

                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                purchase_orders_url = "https://api.xero.com/api.xro/2.0/PurchaseOrders"
                response = requests.get(purchase_orders_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()
                purchase_orders = data.get("PurchaseOrders", [])

                for po in purchase_orders:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "PurchaseOrderID": po.get("PurchaseOrderID"),
                        "PurchaseOrderNumber": po.get("PurchaseOrderNumber"),
                        "Status": po.get("Status"),
                        "ContactID": po.get("Contact", {}).get("ContactID"),
                        "Date": self.parse_xero_date(po.get("Date")),
                        "DeliveryDate": self.parse_xero_date(po.get("DeliveryDate")),
                        "ExpectedArrivalDate": self.parse_xero_date(po.get("ExpectedArrivalDate")),
                        "cleaned_data": po,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    xero_purchase_orders = self.mongodb.get_collection("xero_purchase_orders")
                    await xero_purchase_orders.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "PurchaseOrderID": doc["PurchaseOrderID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('PurchaseOrderID')}")
                    self.elastic.index_document(index="xero_purchase_orders", document=doc, id=es_id)
                    all_stored_pos.append(doc)
                    logger.info(f"Indexed Xero purchase order: {po.get('PurchaseOrderNumber')}")

                logger.info(f"Synced {len(purchase_orders)} purchase orders for tenant {tenantId}")

            return {
                "status": "success",
                "purchase_orders": all_stored_pos,
                "count": len(all_stored_pos),
                "tenants_synced": len(tenants_list)
            }

        except Exception as e:
            logger.error(f"Error fetching Xero purchase orders: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_xero_quotes(self, access_token: str, project_id: str):
        """Fetch Xero Quotes for all tenants and index/store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored_quotes = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]

                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                quotes_url = "https://api.xero.com/api.xro/2.0/Quotes"
                response = requests.get(quotes_url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()
                quotes = data.get("Quotes", [])

                for quote in quotes:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "QuoteID": quote.get("QuoteID"),
                        "QuoteNumber": quote.get("QuoteNumber"),
                        "Status": quote.get("Status"),
                        "Date": self.parse_xero_date(quote.get("Date")),
                        "ExpiryDate": self.parse_xero_date(quote.get("ExpiryDate")),
                        "ContactID": quote.get("Contact", {}).get("ContactID"),
                        "Data": quote,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    xero_quotes = self.mongodb.get_collection("xero_quotes")
                    await xero_quotes.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "QuoteID": doc["QuoteID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('QuoteID')}")
                    self.elastic.index_document(index="xero_quotes", document=doc, id=es_id)
                    all_stored_quotes.append(doc)
                    logger.info(f"Indexed Xero quote: {quote.get('QuoteNumber')}")

                logger.info(f"Synced {len(quotes)} quotes for tenant {tenantId}")

            return {
                "status": "success",
                "quotes": all_stored_quotes,
                "count": len(all_stored_quotes),
                "tenants_synced": len(tenants_list)
            }

        except Exception as e:
            logger.error(f"Error fetching Xero quotes: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_xero_repeating_invoices(self, access_token: str, project_id: str):
        """Fetch Xero RepeatingInvoices for all tenants and index/store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                url = "https://api.xero.com/api.xro/2.0/RepeatingInvoices"
                response = requests.get(url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()
                repeating_invoices = data.get("RepeatingInvoices", [])

                for ri in repeating_invoices:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "RepeatingInvoiceID": ri.get("RepeatingInvoiceID"),
                        "Name": ri.get("Name"),
                        "Status": ri.get("Status"),
                        "StartDate": self.parse_xero_date(ri.get("Schedule", {}).get("StartDate")),
                        "NextScheduledDate": self.parse_xero_date(ri.get("Schedule", {}).get("NextScheduledDate")),
                        "EndDate": self.parse_xero_date(ri.get("Schedule", {}).get("EndDate")),
                        "cleaned_data": ri,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    xero_repeating_invoices = self.mongodb.get_collection("xero_repeating_invoices")
                    await xero_repeating_invoices.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "RepeatingInvoiceID": doc["RepeatingInvoiceID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('RepeatingInvoiceID')}")
                    self.elastic.index_document(index="xero_repeating_invoices", document=doc, id=es_id)
                    all_stored.append(doc)
                    logger.info(f"Indexed Xero repeating invoice: {ri.get('Name')}")

                logger.info(f"Synced {len(repeating_invoices)} repeating invoices for tenant {tenantId}")

            return {
                "status": "success",
                "repeating_invoices": all_stored,
                "count": len(all_stored),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero repeating invoices: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_xero_tax_rates(self, access_token: str, project_id: str):
        """Fetch Xero TaxRates for all tenants and index/store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "xero-tenant-id": tenantId,
                }

                url = "https://api.xero.com/api.xro/2.0/TaxRates"
                response = requests.get(url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()
                tax_rates = data.get("TaxRates", [])

                for tr in tax_rates:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "TaxType": tr.get("TaxType"),
                        "Name": tr.get("Name"),
                        "Status": tr.get("Status"),
                        "TaxComponents": tr.get("TaxComponents", []),
                        "cleaned_data": tr,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    xero_tax_rates = self.mongodb.get_collection("xero_tax_rates")
                    await xero_tax_rates.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "TaxType": doc["TaxType"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('TaxType')}")
                    self.elastic.index_document(index="xero_tax_rates", document=doc, id=es_id)
                    all_stored.append(doc)
                    logger.info(f"Indexed Xero tax rate: {tr.get('Name')}")

                logger.info(f"Synced {len(tax_rates)} tax rates for tenant {tenantId}")

            return {
                "status": "success",
                "tax_rates": all_stored,
                "count": len(all_stored),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero tax rates: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_xero_users(self, access_token: str, project_id: str):
        """Fetch Xero Users for all tenants and index/store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "Xero-Tenant-Id": tenantId,
                }

                url = "https://api.xero.com/api.xro/2.0/Users"  # per docs :contentReference[oaicite:1]{index=1}
                response = requests.get(url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()
                users = data.get("Users", [])

                for u in users:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "UserID": u.get("UserID"),
                        "EmailAddress": u.get("EmailAddress"),
                        "FirstName": u.get("FirstName"),
                        "LastName": u.get("LastName"),
                        "Status": u.get("Status"),
                        "cleaned_data": u,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    xero_users = self.mongodb.get_collection("xero_users")
                    await xero_users.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "UserID": doc["UserID"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('UserID')}")
                    self.elastic.index_document(index="xero_users", document=doc, id=es_id)
                    all_stored.append(doc)
                    logger.info(f"Indexed Xero user: {u.get('EmailAddress')}")

                logger.info(f"Synced {len(users)} users for tenant {tenantId}")

            return {
                "status": "success",
                "users": all_stored,
                "count": len(all_stored),
                "tenants_synced": len(tenants_list)
            }

        except Exception as e:
            logger.error(f"Error fetching Xero users: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_xero_asset_types(self, access_token: str, project_id: str):
        """Fetch Xero AssetTypes for all tenants and index/store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "Xero-Tenant-Id": tenantId,
                }

                url = "https://api.xero.com/assets.xro/1.0/AssetTypes"  # per docs :contentReference[oaicite:2]{index=2}
                response = requests.get(url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()

                for at in data:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "assetTypeId": at.get("assetTypeId"),
                        "assetTypeName": at.get("assetTypeName"),
                        "fixedAssetAccountId": at.get("fixedAssetAccountId"),
                        "depreciationExpenseAccountId": at.get("depreciationExpenseAccountId"),
                        "cleaned_data": at,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    xero_asset_types = self.mongodb.get_collection("xero_asset_types")
                    await xero_asset_types.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "assetTypeId": doc["assetTypeId"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('assetTypeId')}")
                    self.elastic.index_document(index="xero_asset_types", document=doc, id=es_id)
                    all_stored.append(doc)
                    logger.info(f"Indexed Xero asset type: {at.get('assetTypeName')}")

                logger.info(f"Synced {len(data)} asset types for tenant {tenantId}")

            return {
                "status": "success",
                "asset_types": all_stored,
                "count": len(all_stored),
                "tenants_synced": len(tenants_list)
            }

        except Exception as e:
            logger.error(f"Error fetching Xero asset types: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_xero_assets(self, access_token: str, project_id: str):
        """Fetch Xero Assets for all tenants and index/store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "Xero-Tenant-Id": tenantId,
                }
                
                asset_status_codes = ["DRAFT", "REGISTERED", "DISPOSED"]

                for status in asset_status_codes:
                    url = f"https://api.xero.com/assets.xro/1.0/Assets?status={status}" 
                    response = requests.get(url, headers=xero_headers)
                    response.raise_for_status()
                    data = response.json()
                    assets = data.get("items", [])

                    for a in assets:
                        doc = {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "assetId": a.get("assetId"),
                            "assetName": a.get("assetName"),
                            "assetTypeId": a.get("assetTypeId"),
                            "purchaseDate": self.parse_xero_date(a.get("purchaseDate")),
                            "purchasePrice": a.get("purchasePrice"),
                            "assetStatus": a.get("assetStatus"),
                            "cleaned_data": a,
                            "last_synced": datetime.utcnow().isoformat(),
                        }

                        xero_assets = self.mongodb.get_collection("xero_assets")
                        await xero_assets.update_one(
                            {
                                "project_id": project_id,
                                "tenantId": tenantId,
                                "assetId": doc["assetId"]
                            },
                            {"$set": doc},
                            upsert=True,
                        )

                        es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('assetId')}")
                        self.elastic.index_document(index="xero_assets", document=doc, id=es_id)
                        all_stored.append(doc)
                        logger.info(f"Indexed Xero asset: {a.get('assetId')}")

                    logger.info(f"Synced {len(assets)} assets for tenant {tenantId} with status {status}")

            return {
                "status": "success",
                "assets": all_stored,
                "count": len(all_stored),
                "tenants_synced": len(tenants_list)
            }

        except Exception as e:
            logger.error(f"Error fetching Xero assets: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_xero_feed_connections(self, access_token: str, project_id: str):
        """Fetch Xero FeedConnections for all tenants and index/store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "Xero-Tenant-Id": tenantId,
                }

                url = "https://api.xero.com/bankfeeds.xro/1.0/FeedConnections"  # per docs :contentReference[oaicite:4]{index=4}
                response = requests.get(url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()
                feed_connections = data.get("FeedConnections", [])

                for fc in feed_connections:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "feedConnectionId": fc.get("id"),
                        "accountNumber": fc.get("accountNumber"),
                        "accountName": fc.get("accountName"),
                        "status": fc.get("status"),
                        "cleaned_data": fc,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    xero_feed_connections = self.mongodb.get_collection("xero_feed_connections")
                    await xero_feed_connections.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "feedConnectionId": doc["feedConnectionId"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('feedConnectionId')}")
                    self.elastic.index_document(index="xero_feed_connections", document=doc, id=es_id)
                    all_stored.append(doc)
                    logger.info(f"Indexed Xero feed connection: {fc.get('FeedConnectionID')}")

                logger.info(f"Synced {len(feed_connections)} feed connections for tenant {tenantId}")

            return {
                "status": "success",
                "feed_connections": all_stored,
                "count": len(all_stored),
                "tenants_synced": len(tenants_list)
            }

        except Exception as e:
            logger.error(f"Error fetching Xero feed connections: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_xero_statements(self, access_token: str, project_id: str):
        """Fetch Xero Statements for all tenants and index/store them."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find({"project_id": project_id}).to_list(length=None)
            if not tenants_list:
                return {"status": "error", "message": "No tenants found for this project."}

            all_stored = []

            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                xero_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "Xero-Tenant-Id": tenantId,
                }

                url = "https://api.xero.com/bankfeeds.xro/1.0/Statements"  # per docs :contentReference[oaicite:5]{index=5}
                response = requests.get(url, headers=xero_headers)
                response.raise_for_status()
                data = response.json()
                statements = data.get("Statements", [])

                for s in statements:
                    doc = {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "statementId": s.get("id"),
                        "feedConnectionId": s.get("feedConnectionId"),
                        "startBalance": s.get("startBalance"),
                        "endBalance": s.get("endBalance"),
                        "startDate": self.parse_xero_date(s.get("startDate")),
                        "endDate": self.parse_xero_date(s.get("endDate")),
                        "cleaned_data": s,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    xero_statements = self.mongodb.get_collection("xero_statements")
                    await xero_statements.update_one(
                        {
                            "project_id": project_id,
                            "tenantId": tenantId,
                            "statementId": doc["statementId"]
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('statementId')}")
                    self.elastic.index_document(index="xero_statements", document=doc, id=es_id)
                    all_stored.append(doc)
                    logger.info(f"Indexed Xero statement: {s.get('StatementID')}")

                logger.info(f"Synced {len(statements)} statements for tenant {tenantId}")

            return {
                "status": "success",
                "statements": all_stored,
                "count": len(all_stored),
                "tenants_synced": len(tenants_list)
            }

        except Exception as e:
            logger.error(f"Error fetching Xero statements: {e}")
            return {"status": "error", "message": str(e)}


    async def sync_xero_payroll_employees(self, access_token: str, project_id: str):
        """Fetch Xero payroll employees for all tenants, auto-detecting region."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_employees = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                # Read saved organisation from MongoDB to determine country code
                xero_organisation = self.mongodb.get_collection("xero_organisations")
                org_doc = await xero_organisation.find_one(
                    {"project_id": project_id, "tenantId": tenantId}
                )
                if org_doc and org_doc.get("country_code"):
                    country_code = org_doc.get("country_code")
                else:
                    # fallback: check tenant stored data if available
                    country_code = tenant.get("cleaned_data", {}).get("CountryCode")
                    if not country_code:
                        logger.info(f"No organisation country code found for tenant {tenantId}, skipping payroll sync.")
                        continue
                
                if country_code == "AU":
                    employees = await self._sync_payroll_employees_au(access_token, tenantId, project_id)
                elif country_code == "GB":
                    employees = await self._sync_payroll_employees_uk(access_token, tenantId, project_id)
                elif country_code == "NZ":
                    employees = await self._sync_payroll_employees_nz(access_token, tenantId, project_id)
                else:
                    logger.info(f"Payroll not supported for country: {country_code}")
                    continue
                
                all_stored_employees.extend(employees)
                logger.info(f"Synced {len(employees)} payroll employees for tenant {tenantId} ({country_code})")

            return {
                "status": "success",
                "employees": all_stored_employees,
                "count": len(all_stored_employees),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero payroll employees: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def _sync_payroll_employees_au(self, access_token: str, tenantId: str, project_id: str):
        """Sync Australian payroll employees."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        response = requests.get(
            "https://api.xero.com/payroll.xro/1.0/Employees",
            headers=xero_headers
        )
        response.raise_for_status()
        data = response.json()
        
        employees = []
        for employee in data.get("Employees", []):
            doc = {
                "project_id": project_id,
                "tenantId": tenantId,
                "Region": "AU",
                "EmployeeID": employee.get("EmployeeID"),
                "FirstName": employee.get("FirstName"),
                "LastName": employee.get("LastName"),
                "Email": employee.get("Email"),
                "DateOfBirth": self.parse_xero_date(employee.get("DateOfBirth")),
                "StartDate": self.parse_xero_date(employee.get("StartDate")),
                "TerminationDate": self.parse_xero_date(employee.get("TerminationDate")),
                "Status": employee.get("Status"),
                "Classification": employee.get("Classification"),
                "TaxDeclaration": employee.get("TaxDeclaration"),
                "SuperMemberships": employee.get("SuperMemberships", []),
                "HomeAddress": employee.get("HomeAddress"),
                "UpdatedDateUTC": self.parse_xero_date(employee.get("UpdatedDateUTC")),
                "cleaned_data": employee,
                "last_synced": datetime.utcnow().isoformat(),
            }
            
            xero_payroll_employees = self.mongodb.get_collection("xero_payroll_employees")
            await xero_payroll_employees.update_one(
                {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "EmployeeID": doc["EmployeeID"]
                },
                {"$set": doc},
                upsert=True,
            )
            es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('EmployeeID')}")
            self.elastic.index_document(index="xero_payroll_employees", document=doc, id=es_id)
            employees.append(doc)
        
        return employees


    async def _sync_payroll_employees_uk(self, access_token: str, tenantId: str, project_id: str):
        """Sync UK payroll employees."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        response = requests.get(
            "https://api.xero.com/payroll.xro/2.0/Employees",
            headers=xero_headers
        )
        response.raise_for_status()
        data = response.json()
        
        employees = []
        for employee in data.get("Employees", []):
            doc = {
                "project_id": project_id,
                "tenantId": tenantId,
                "Region": "UK",
                "EmployeeID": employee.get("employeeID"),
                "FirstName": employee.get("firstName"),
                "LastName": employee.get("lastName"),
                "Email": employee.get("email"),
                "DateOfBirth": self.parse_xero_date(employee.get("dateOfBirth")),
                "StartDate": self.parse_xero_date(employee.get("startDate")),
                "Status": employee.get("status"),
                "NINumber": employee.get("niNumber"),
                "Gender": employee.get("gender"),
                "Address": employee.get("address"),
                "UpdatedDateUTC": self.parse_xero_date(employee.get("updatedDateUTC")),
                "cleaned_data": employee,
                "last_synced": datetime.utcnow().isoformat(),
            }
            
            xero_payroll_employees = self.mongodb.get_collection("xero_payroll_employees")
            await xero_payroll_employees.update_one(
                {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "EmployeeID": doc["EmployeeID"]
                },
                {"$set": doc},
                upsert=True,
            )
            es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('EmployeeID')}")
            self.elastic.index_document(index="xero_payroll_employees", document=doc, id=es_id)
            employees.append(doc)
        
        return employees


    async def _sync_payroll_employees_nz(self, access_token: str, tenantId: str, project_id: str):
        """Sync New Zealand payroll employees."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        response = requests.get(
            "https://api.xero.com/payroll.xro/2.0/Employees",
            headers=xero_headers
        )
        response.raise_for_status()
        data = response.json()
        
        employees = []
        for employee in data.get("Employees", []):
            doc = {
                "project_id": project_id,
                "tenantId": tenantId,
                "Region": "NZ",
                "EmployeeID": employee.get("employeeID"),
                "FirstName": employee.get("firstName"),
                "LastName": employee.get("lastName"),
                "Email": employee.get("email"),
                "DateOfBirth": self.parse_xero_date(employee.get("dateOfBirth")),
                "StartDate": self.parse_xero_date(employee.get("startDate")),
                "IRDNumber": employee.get("irdNumber"),
                "Address": employee.get("address"),
                "UpdatedDateUTC": self.parse_xero_date(employee.get("updatedDateUTC")),
                "cleaned_data": employee,
                "last_synced": datetime.utcnow().isoformat(),
            }
            
            xero_payroll_employees = self.mongodb.get_collection("xero_payroll_employees")
            await xero_payroll_employees.update_one(
                {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "EmployeeID": doc["EmployeeID"]
                },
                {"$set": doc},
                upsert=True,
            )
            es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('EmployeeID')}")
            self.elastic.index_document(index="xero_payroll_employees", document=doc, id=es_id)
            employees.append(doc)
        
        return employees

    async def sync_xero_payroll_pay_runs(self, access_token: str, project_id: str):
        """Fetch Xero payroll pay runs for all tenants, auto-detecting region."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_pay_runs = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                # Read saved organisation from MongoDB to determine country code
                xero_organisation = self.mongodb.get_collection("xero_organisations")
                org_doc = await xero_organisation.find_one(
                    {"project_id": project_id, "tenantId": tenantId}
                )
                if org_doc and org_doc.get("country_code"):
                    country_code = org_doc.get("country_code")
                else:
                    # fallback: check tenant stored data if available
                    country_code = tenant.get("cleaned_data", {}).get("CountryCode")
                    if not country_code:
                        logger.info(f"No organisation country code found for tenant {tenantId}, skipping payroll sync.")
                        continue
                
                if country_code == "AU":
                    pay_runs = await self._sync_payroll_pay_runs_au(access_token, tenantId, project_id)
                elif country_code == "GB":
                    pay_runs = await self._sync_payroll_pay_runs_uk(access_token, tenantId, project_id)
                elif country_code == "NZ":
                    pay_runs = await self._sync_payroll_pay_runs_nz(access_token, tenantId, project_id)
                else:
                    logger.info(f"Payroll not supported for country: {country_code}")
                    continue
                
                all_stored_pay_runs.extend(pay_runs)
                logger.info(f"Synced {len(pay_runs)} payroll pay runs for tenant {tenantId} ({country_code})")

            return {
                "status": "success",
                "pay_runs": all_stored_pay_runs,
                "count": len(all_stored_pay_runs),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero payroll pay runs: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def _sync_payroll_pay_runs_au(self, access_token: str, tenantId: str, project_id: str):
        """Sync Australian payroll pay runs."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        response = requests.get(
            "https://api.xero.com/payroll.xro/1.0/PayRuns",
            headers=xero_headers
        )
        response.raise_for_status()
        data = response.json()
        
        pay_runs = []
        for pay_run in data.get("PayRuns", []):
            doc = {
                "project_id": project_id,
                "tenantId": tenantId,
                "Region": "AU",
                "PayRunID": pay_run.get("PayRunID"),
                "PayRunPeriodStartDate": self.parse_xero_date(pay_run.get("PayRunPeriodStartDate")),
                "PayRunPeriodEndDate": self.parse_xero_date(pay_run.get("PayRunPeriodEndDate")),
                "PayRunStatus": pay_run.get("PayRunStatus"),
                "PaymentDate": self.parse_xero_date(pay_run.get("PaymentDate")),
                "PayrollCalendarID": pay_run.get("PayrollCalendarID"),
                "Posted": pay_run.get("Posted", False),
                "Wages": pay_run.get("Wages"),
                "Deductions": pay_run.get("Deductions"),
                "Tax": pay_run.get("Tax"),
                "Super": pay_run.get("Super"),
                "Reimbursement": pay_run.get("Reimbursement"),
                "NetPay": pay_run.get("NetPay"),
                "Payslips": pay_run.get("Payslips", []),
                "UpdatedDateUTC": self.parse_xero_date(pay_run.get("UpdatedDateUTC")),
                "cleaned_data": pay_run,
                "last_synced": datetime.utcnow().isoformat(),
            }
            
            xero_payroll_pay_runs = self.mongodb.get_collection("xero_payroll_pay_runs")
            await xero_payroll_pay_runs.update_one(
                {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "PayRunID": doc["PayRunID"]
                },
                {"$set": doc},
                upsert=True,
            )
            es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('PayRunID')}")
            self.elastic.index_document(index="xero_payroll_pay_runs", document=doc, id=es_id)
            pay_runs.append(doc)
        
        return pay_runs


    async def _sync_payroll_pay_runs_uk(self, access_token: str, tenantId: str, project_id: str):
        """Sync UK payroll pay runs."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        response = requests.get(
            "https://api.xero.com/payroll.xro/2.0/PayRuns",
            headers=xero_headers
        )
        response.raise_for_status()
        data = response.json()
        
        pay_runs = []
        for pay_run in data.get("PayRuns", []):
            doc = {
                "project_id": project_id,
                "tenantId": tenantId,
                "Region": "UK",
                "PayRunID": pay_run.get("payRunID"),
                "PayRunPeriodStartDate": self.parse_xero_date(pay_run.get("periodStartDate")),
                "PayRunPeriodEndDate": self.parse_xero_date(pay_run.get("periodEndDate")),
                "PayRunStatus": pay_run.get("payRunStatus"),
                "PaymentDate": self.parse_xero_date(pay_run.get("paymentDate")),
                "PayrollCalendarID": pay_run.get("payrollCalendarID"),
                "Payslips": pay_run.get("payslips", []),
                "UpdatedDateUTC": self.parse_xero_date(pay_run.get("updatedDateUTC")),
                "cleaned_data": pay_run,
                "last_synced": datetime.utcnow().isoformat(),
            }
            
            xero_payroll_pay_runs = self.mongodb.get_collection("xero_payroll_pay_runs")
            await xero_payroll_pay_runs.update_one(
                {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "PayRunID": doc["PayRunID"]
                },
                {"$set": doc},
                upsert=True,
            )
            es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('PayRunID')}")
            self.elastic.index_document(index="xero_payroll_pay_runs", document=doc, id=es_id)
            pay_runs.append(doc)
        
        return pay_runs


    async def _sync_payroll_pay_runs_nz(self, access_token: str, tenantId: str, project_id: str):
        """Sync New Zealand payroll pay runs."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        response = requests.get(
            "https://api.xero.com/payroll.xro/2.0/PayRuns",
            headers=xero_headers
        )
        response.raise_for_status()
        data = response.json()
        
        pay_runs = []
        for pay_run in data.get("PayRuns", []):
            doc = {
                "project_id": project_id,
                "tenantId": tenantId,
                "Region": "NZ",
                "PayRunID": pay_run.get("payRunID"),
                "PayRunPeriodStartDate": self.parse_xero_date(pay_run.get("periodStartDate")),
                "PayRunPeriodEndDate": self.parse_xero_date(pay_run.get("periodEndDate")),
                "PayRunStatus": pay_run.get("payRunStatus"),
                "PaymentDate": self.parse_xero_date(pay_run.get("paymentDate")),
                "PayrollCalendarID": pay_run.get("payrollCalendarID"),
                "Payslips": pay_run.get("payslips", []),
                "UpdatedDateUTC": self.parse_xero_date(pay_run.get("updatedDateUTC")),
                "cleaned_data": pay_run,
                "last_synced": datetime.utcnow().isoformat(),
            }
            
            xero_payroll_pay_runs = self.mongodb.get_collection("xero_payroll_pay_runs")
            await xero_payroll_pay_runs.update_one(
                {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "PayRunID": doc["PayRunID"]
                },
                {"$set": doc},
                upsert=True,
            )
            es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('PayRunID')}")
            self.elastic.index_document(index="xero_payroll_pay_runs", document=doc, id=es_id)
            pay_runs.append(doc)
        
        return pay_runs

    async def sync_xero_payroll_payslips(self, access_token: str, project_id: str):
        """Fetch Xero payroll payslips for all tenants, auto-detecting region."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_payslips = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                # Read saved organisation from MongoDB to determine country code
                xero_organisation = self.mongodb.get_collection("xero_organisations")
                org_doc = await xero_organisation.find_one(
                    {"project_id": project_id, "tenantId": tenantId}
                )
                if org_doc and org_doc.get("country_code"):
                    country_code = org_doc.get("country_code")
                else:
                    # fallback: check tenant stored data if available
                    country_code = tenant.get("cleaned_data", {}).get("CountryCode")
                    if not country_code:
                        logger.info(f"No organisation country code found for tenant {tenantId}, skipping payroll sync.")
                        continue
                
                if country_code == "AU":
                    payslips = await self._sync_payroll_payslips_au(access_token, tenantId, project_id)
                elif country_code == "GB":
                    payslips = await self._sync_payroll_payslips_uk(access_token, tenantId, project_id)
                elif country_code == "NZ":
                    payslips = await self._sync_payroll_payslips_nz(access_token, tenantId, project_id)
                else:
                    logger.info(f"Payroll not supported for country: {country_code}")
                    continue
                
                all_stored_payslips.extend(payslips)
                logger.info(f"Synced {len(payslips)} payroll payslips for tenant {tenantId} ({country_code})")

            return {
                "status": "success",
                "payslips": all_stored_payslips,
                "count": len(all_stored_payslips),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero payroll payslips: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def _sync_payroll_payslips_au(self, access_token: str, tenantId: str, project_id: str):
        """Sync Australian payroll payslips."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        # First get all pay runs to extract payslip IDs
        pay_runs_response = requests.get(
            "https://api.xero.com/payroll.xro/1.0/PayRuns",
            headers=xero_headers
        )
        pay_runs_response.raise_for_status()
        pay_runs_data = pay_runs_response.json()
        
        payslips = []
        for pay_run in pay_runs_data.get("PayRuns", []):
            pay_run_id = pay_run.get("PayRunID")
            
            # Get payslips for this pay run
            payslip_response = requests.get(
                f"https://api.xero.com/payroll.xro/1.0/PayRuns/{pay_run_id}",
                headers=xero_headers
            )
            payslip_response.raise_for_status()
            payslip_data = payslip_response.json()
            
            for payslip in payslip_data.get("PayRuns", [{}])[0].get("Payslips", []):
                doc = {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "Region": "AU",
                    "PayslipID": payslip.get("PayslipID"),
                    "EmployeeID": payslip.get("EmployeeID"),
                    "PayRunID": pay_run_id,
                    "FirstName": payslip.get("FirstName"),
                    "LastName": payslip.get("LastName"),
                    "Wages": payslip.get("Wages"),
                    "Deductions": payslip.get("Deductions"),
                    "Tax": payslip.get("Tax"),
                    "Super": payslip.get("Super"),
                    "Reimbursements": payslip.get("Reimbursements"),
                    "NetPay": payslip.get("NetPay"),
                    "EarningsLines": payslip.get("EarningsLines", []),
                    "LeaveEarningsLines": payslip.get("LeaveEarningsLines", []),
                    "TimesheetEarningsLines": payslip.get("TimesheetEarningsLines", []),
                    "DeductionLines": payslip.get("DeductionLines", []),
                    "ReimbursementLines": payslip.get("ReimbursementLines", []),
                    "LeaveAccrualLines": payslip.get("LeaveAccrualLines", []),
                    "SuperannuationLines": payslip.get("SuperannuationLines", []),
                    "TaxLines": payslip.get("TaxLines", []),
                    "UpdatedDateUTC": self.parse_xero_date(payslip.get("UpdatedDateUTC")),
                    "cleaned_data": payslip,
                    "last_synced": datetime.utcnow().isoformat(),
                }
                
                xero_payroll_payslips = self.mongodb.get_collection("xero_payroll_payslips")
                await xero_payroll_payslips.update_one(
                    {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "PayslipID": doc["PayslipID"]
                    },
                    {"$set": doc},
                    upsert=True,
                )
                es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('PayslipID')}")
                self.elastic.index_document(index="xero_payroll_payslips", document=doc, id=es_id)
                payslips.append(doc)
        
        return payslips


    async def _sync_payroll_payslips_uk(self, access_token: str, tenantId: str, project_id: str):
        """Sync UK payroll payslips."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        # UK uses page-based pagination for payslips
        page = 1
        payslips = []
        
        while True:
            response = requests.get(
                f"https://api.xero.com/payroll.xro/2.0/Payslips?page={page}",
                headers=xero_headers
            )
            response.raise_for_status()
            data = response.json()
            
            page_payslips = data.get("Payslips", [])
            if not page_payslips:
                break
            
            for payslip in page_payslips:
                doc = {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "Region": "UK",
                    "PayslipID": payslip.get("paySlipID"),
                    "EmployeeID": payslip.get("employeeID"),
                    "PayRunID": payslip.get("payRunID"),
                    "FirstName": payslip.get("firstName"),
                    "LastName": payslip.get("lastName"),
                    "Wages": payslip.get("totalEarnings"),
                    "Deductions": payslip.get("totalDeductions"),
                    "Tax": payslip.get("totalTax"),
                    "NetPay": payslip.get("netPay"),
                    "EarningsLines": payslip.get("earningsLines", []),
                    "DeductionLines": payslip.get("deductionLines", []),
                    "ReimbursementLines": payslip.get("reimbursementLines", []),
                    "LeaveAccrualLines": payslip.get("leaveAccrualLines", []),
                    "TaxLines": payslip.get("taxLines", []),
                    "UpdatedDateUTC": self.parse_xero_date(payslip.get("updatedDateUTC")),
                    "cleaned_data": payslip,
                    "last_synced": datetime.utcnow().isoformat(),
                }
                
                xero_payroll_payslips = self.mongodb.get_collection("xero_payroll_payslips")
                await xero_payroll_payslips.update_one(
                    {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "PayslipID": doc["PayslipID"]
                    },
                    {"$set": doc},
                    upsert=True,
                )
                es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('PayslipID')}")
                self.elastic.index_document(index="xero_payroll_payslips", document=doc, id=es_id)
                payslips.append(doc)
            
            if len(page_payslips) < 100:
                break
            
            page += 1
        
        return payslips


    async def _sync_payroll_payslips_nz(self, access_token: str, tenantId: str, project_id: str):
        """Sync New Zealand payroll payslips."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        # NZ uses page-based pagination for payslips
        page = 1
        payslips = []
        
        while True:
            response = requests.get(
                f"https://api.xero.com/payroll.xro/2.0/Payslips?page={page}",
                headers=xero_headers
            )
            response.raise_for_status()
            data = response.json()
            
            page_payslips = data.get("Payslips", [])
            if not page_payslips:
                break
            
            for payslip in page_payslips:
                doc = {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "Region": "NZ",
                    "PayslipID": payslip.get("paySlipID"),
                    "EmployeeID": payslip.get("employeeID"),
                    "PayRunID": payslip.get("payRunID"),
                    "FirstName": payslip.get("firstName"),
                    "LastName": payslip.get("lastName"),
                    "Wages": payslip.get("totalEarnings"),
                    "Deductions": payslip.get("totalDeductions"),
                    "Tax": payslip.get("totalTax"),
                    "NetPay": payslip.get("netPay"),
                    "EarningsLines": payslip.get("earningsLines", []),
                    "DeductionLines": payslip.get("deductionLines", []),
                    "ReimbursementLines": payslip.get("reimbursementLines", []),
                    "LeaveAccrualLines": payslip.get("leaveAccrualLines", []),
                    "TaxLines": payslip.get("taxLines", []),
                    "UpdatedDateUTC": self.parse_xero_date(payslip.get("updatedDateUTC")),
                    "cleaned_data": payslip,
                    "last_synced": datetime.utcnow().isoformat(),
                }
                
                xero_payroll_payslips = self.mongodb.get_collection("xero_payroll_payslips")
                await xero_payroll_payslips.update_one(
                    {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "PayslipID": doc["PayslipID"]
                    },
                    {"$set": doc},
                    upsert=True,
                )
                es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('PayslipID')}")
                self.elastic.index_document(index="xero_payroll_payslips", document=doc, id=es_id)
                payslips.append(doc)
            
            if len(page_payslips) < 100:
                break
            
            page += 1
        
        return payslips

    async def sync_xero_payroll_timesheets(self, access_token: str, project_id: str):
        """Fetch Xero payroll timesheets for all tenants, auto-detecting region."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_timesheets = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                # Read saved organisation from MongoDB to determine country code
                xero_organisation = self.mongodb.get_collection("xero_organisations")
                org_doc = await xero_organisation.find_one(
                    {"project_id": project_id, "tenantId": tenantId}
                )
                if org_doc and org_doc.get("country_code"):
                    country_code = org_doc.get("country_code")
                else:
                    # fallback: check tenant stored data if available
                    country_code = tenant.get("cleaned_data", {}).get("CountryCode")
                    if not country_code:
                        logger.info(f"No organisation country code found for tenant {tenantId}, skipping payroll sync.")
                        continue
                
                if country_code == "AU":
                    timesheets = await self._sync_payroll_timesheets_au(access_token, tenantId, project_id)
                elif country_code == "GB":
                    # UK doesn't have timesheets endpoint
                    logger.info(f"Timesheets not available for UK payroll")
                    continue
                elif country_code == "NZ":
                    timesheets = await self._sync_payroll_timesheets_nz(access_token, tenantId, project_id)
                else:
                    logger.info(f"Payroll not supported for country: {country_code}")
                    continue
                
                all_stored_timesheets.extend(timesheets)
                logger.info(f"Synced {len(timesheets)} payroll timesheets for tenant {tenantId} ({country_code})")

            return {
                "status": "success",
                "timesheets": all_stored_timesheets,
                "count": len(all_stored_timesheets),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero payroll timesheets: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def _sync_payroll_timesheets_au(self, access_token: str, tenantId: str, project_id: str):
        """Sync Australian payroll timesheets."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        response = requests.get(
            "https://api.xero.com/payroll.xro/1.0/Timesheets",
            headers=xero_headers
        )
        response.raise_for_status()
        data = response.json()
        
        timesheets = []
        for timesheet in data.get("Timesheets", []):
            doc = {
                "project_id": project_id,
                "tenantId": tenantId,
                "Region": "AU",
                "TimesheetID": timesheet.get("TimesheetID"),
                "EmployeeID": timesheet.get("EmployeeID"),
                "StartDate": self.parse_xero_date(timesheet.get("StartDate")),
                "EndDate": self.parse_xero_date(timesheet.get("EndDate")),
                "Status": timesheet.get("Status"),
                "TotalHours": timesheet.get("Hours"),
                "TimesheetLines": timesheet.get("TimesheetLines", []),
                "UpdatedDateUTC": self.parse_xero_date(timesheet.get("UpdatedDateUTC")),
                "cleaned_data": timesheet,
                "last_synced": datetime.utcnow().isoformat(),
            }
            
            xero_payroll_timesheets = self.mongodb.get_collection("xero_payroll_timesheets")
            await xero_payroll_timesheets.update_one(
                {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "TimesheetID": doc["TimesheetID"]
                },
                {"$set": doc},
                upsert=True,
            )
            es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('TimesheetID')}")
            self.elastic.index_document(index="xero_payroll_timesheets", document=doc, id=es_id)
            timesheets.append(doc)
        
        return timesheets


    async def _sync_payroll_timesheets_nz(self, access_token: str, tenantId: str, project_id: str):
        """Sync New Zealand payroll timesheets."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        # NZ uses page-based pagination for timesheets
        page = 1
        timesheets = []
        
        while True:
            response = requests.get(
                f"https://api.xero.com/payroll.xro/2.0/Timesheets?page={page}",
                headers=xero_headers
            )
            response.raise_for_status()
            data = response.json()
            
            page_timesheets = data.get("Timesheets", [])
            if not page_timesheets:
                break
            
            for timesheet in page_timesheets:
                doc = {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "Region": "NZ",
                    "TimesheetID": timesheet.get("timesheetID"),
                    "EmployeeID": timesheet.get("employeeID"),
                    "StartDate": self.parse_xero_date(timesheet.get("startDate")),
                    "EndDate": self.parse_xero_date(timesheet.get("endDate")),
                    "Status": timesheet.get("status"),
                    "TotalHours": timesheet.get("totalHours"),
                    "TimesheetLines": timesheet.get("timesheetLines", []),
                    "UpdatedDateUTC": self.parse_xero_date(timesheet.get("updatedDateUTC")),
                    "cleaned_data": timesheet,
                    "last_synced": datetime.utcnow().isoformat(),
                }
                
                xero_payroll_timesheets = self.mongodb.get_collection("xero_payroll_timesheets")
                await xero_payroll_timesheets.update_one(
                    {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "TimesheetID": doc["TimesheetID"]
                    },
                    {"$set": doc},
                    upsert=True,
                )
                es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('TimesheetID')}")
                self.elastic.index_document(index="xero_payroll_timesheets", document=doc, id=es_id)
                timesheets.append(doc)
            
            if len(page_timesheets) < 100:
                break
            
            page += 1
        
        return timesheets

    async def sync_xero_payroll_leave_applications(self, access_token: str, project_id: str):
        """Fetch Xero payroll leave applications for all tenants, auto-detecting region."""
        try:
            xero_tenants = self.mongodb.get_collection("xero_tenants")
            tenants_list = await xero_tenants.find(
                {"project_id": project_id}
            ).to_list(length=None)
            
            if not tenants_list:
                return {
                    "status": "error",
                    "message": "No tenants found for this project."
                }
            
            all_stored_leave_applications = []
            
            for tenant in tenants_list:
                tenantId = tenant["tenantId"]
                
                # Read saved organisation from MongoDB to determine country code
                xero_organisation = self.mongodb.get_collection("xero_organisations")
                org_doc = await xero_organisation.find_one(
                    {"project_id": project_id, "tenantId": tenantId}
                )
                if org_doc and org_doc.get("country_code"):
                    country_code = org_doc.get("country_code")
                else:
                    # fallback: check tenant stored data if available
                    country_code = tenant.get("cleaned_data", {}).get("CountryCode")
                    if not country_code:
                        logger.info(f"No organisation country code found for tenant {tenantId}, skipping payroll sync.")
                        continue
                
                if country_code == "AU":
                    leave_applications = await self._sync_payroll_leave_applications_au(access_token, tenantId, project_id)
                elif country_code == "GB":
                    # UK doesn't have leave applications endpoint in same format
                    logger.info(f"Leave applications not available in same format for UK payroll")
                    continue
                elif country_code == "NZ":
                    leave_applications = await self._sync_payroll_leave_applications_nz(access_token, tenantId, project_id)
                else:
                    logger.info(f"Payroll not supported for country: {country_code}")
                    continue
                
                all_stored_leave_applications.extend(leave_applications)
                logger.info(f"Synced {len(leave_applications)} payroll leave applications for tenant {tenantId} ({country_code})")

            return {
                "status": "success",
                "leave_applications": all_stored_leave_applications,
                "count": len(all_stored_leave_applications),
                "tenants_synced": len(tenants_list)
            }
        except Exception as e:
            logger.error(f"Error fetching Xero payroll leave applications: {e}")
            return {
                "status": "error",
                "message": str(e),
            }


    async def _sync_payroll_leave_applications_au(self, access_token: str, tenantId: str, project_id: str):
        """Sync Australian payroll leave applications."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        response = requests.get(
            "https://api.xero.com/payroll.xro/1.0/LeaveApplications",
            headers=xero_headers
        )
        response.raise_for_status()
        data = response.json()
        
        leave_applications = []
        for leave_app in data.get("LeaveApplications", []):
            doc = {
                "project_id": project_id,
                "tenantId": tenantId,
                "Region": "AU",
                "LeaveApplicationID": leave_app.get("LeaveApplicationID"),
                "EmployeeID": leave_app.get("EmployeeID"),
                "LeaveTypeID": leave_app.get("LeaveTypeID"),
                "Title": leave_app.get("Title"),
                "StartDate": self.parse_xero_date(leave_app.get("StartDate")),
                "EndDate": self.parse_xero_date(leave_app.get("EndDate")),
                "Description": leave_app.get("Description"),
                "Status": leave_app.get("Status"),
                "LeavePeriods": leave_app.get("LeavePeriods", []),
                "UpdatedDateUTC": self.parse_xero_date(leave_app.get("UpdatedDateUTC")),
                "cleaned_data": leave_app,
                "last_synced": datetime.utcnow().isoformat(),
            }
            
            xero_payroll_leave_applications = self.mongodb.get_collection("xero_payroll_leave_applications")
            await xero_payroll_leave_applications.update_one(
                {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "LeaveApplicationID": doc["LeaveApplicationID"]
                },
                {"$set": doc},
                upsert=True,
            )
            es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('LeaveApplicationID')}")
            self.elastic.index_document(index="xero_payroll_leave_applications", document=doc, id=es_id)
            leave_applications.append(doc)
        
        return leave_applications


    async def _sync_payroll_leave_applications_nz(self, access_token: str, tenantId: str, project_id: str):
        """Sync New Zealand payroll leave applications."""
        xero_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "xero-tenant-id": tenantId,
        }
        
        # NZ uses page-based pagination for leave applications
        page = 1
        leave_applications = []
        
        while True:
            response = requests.get(
                f"https://api.xero.com/payroll.xro/2.0/LeaveApplications?page={page}",
                headers=xero_headers
            )
            response.raise_for_status()
            data = response.json()
            
            page_leave_apps = data.get("LeaveApplications", [])
            if not page_leave_apps:
                break
            
            for leave_app in page_leave_apps:
                doc = {
                    "project_id": project_id,
                    "tenantId": tenantId,
                    "Region": "NZ",
                    "LeaveApplicationID": leave_app.get("leaveApplicationID"),
                    "EmployeeID": leave_app.get("employeeID"),
                    "LeaveTypeID": leave_app.get("leaveTypeID"),
                    "Title": leave_app.get("title"),
                    "StartDate": self.parse_xero_date(leave_app.get("startDate")),
                    "EndDate": self.parse_xero_date(leave_app.get("endDate")),
                    "Description": leave_app.get("description"),
                    "Status": leave_app.get("status"),
                    "LeavePeriods": leave_app.get("leavePeriods", []),
                    "UpdatedDateUTC": self.parse_xero_date(leave_app.get("updatedDateUTC")),
                    "cleaned_data": leave_app,
                    "last_synced": datetime.utcnow().isoformat(),
                }
                
                xero_payroll_leave_applications = self.mongodb.get_collection("xero_payroll_leave_applications")
                await xero_payroll_leave_applications.update_one(
                    {
                        "project_id": project_id,
                        "tenantId": tenantId,
                        "LeaveApplicationID": doc["LeaveApplicationID"]
                    },
                    {"$set": doc},
                    upsert=True,
                )
                es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('LeaveApplicationID')}")
                self.elastic.index_document(index="xero_payroll_leave_applications", document=doc, id=es_id)
                leave_applications.append(doc)
            
            if len(page_leave_apps) < 100:
                break
            
            page += 1
        
        return leave_applications
    
    async def update_xero_secret_key(self, project_id: str, key: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"xero_refresh_key": key}},
        )
        return True if project.modified_count > 0 else False
    
    async def remove_xero_secret_key(self, project_id: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$unset": {"xero_refresh_key": 1}},
        )
        return True if project.modified_count > 0 else False
    
    def es_remove_xero_data(self, project_id: str) -> bool:
        """
        Remove all Xero-related data for a given project from Elasticsearch.
        """
        if not project_id:
            return False
        indices = []
        indices = self.elastic.list_indices(pattern="xero_*")

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
                logger.info(f"Deleted Xero data from index: {index} for project_id: {project_id}")
            except exceptions.NotFoundError:
                logger.error(f"Index not found: {index}, skipping.")
            except Exception as e:
                logger.error(f"Error deleting data from index {index}: {str(e)}")
                return False
        return True
    
    async def disconnect_xero(self, project_id: str):
        # remove xero data from elasticsearch and mongodb
        status = self.es_remove_xero_data(project_id)
        prefix = "xero_"
        collections = await self.mongodb.list_collections()

        collections = [c for c in collections if c.startswith(prefix)]
        # 3. Remove documents where project_id exists
        for col_name in collections:
            col = self.mongodb.get_collection(col_name)
            result = await col.delete_many({"project_id": project_id})
            logger.info(f"Deleted {result.deleted_count} documents from {col_name}")
        return status
    
    
ServiceRegistry.register_service("xero", XeroService())
