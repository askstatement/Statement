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
from intuitlib.client import AuthClient

logger = Logger(__name__)


class QuickbooksService(BaseService):
    name = "quickbooks"

    async def quickbooks_oauth_callback(self, code: str, realm_id: str):
        """Handles QuickBooks OAuth callback to exchange code for access token."""
        try:

            client_id = os.getenv("QUICKBOOKS_CLIENT_ID")
            client_secret = os.getenv("QUICKBOOKS_CLIENT_SECRET")
            redirect_uri = os.getenv("QUICKBOOKS_REDIRECT_URI")
            environment = os.getenv("QUICKBOOKS_ENVIRONMENT", "sandbox")

            auth_client = AuthClient(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                environment=environment,
                id_token={"realmId": realm_id},
            )

            # Exchange authorization code for tokens
            auth_client.get_bearer_token(code)

            access_token = auth_client.access_token
            refresh_token = auth_client.refresh_token

            print(f"Successfully obtained QuickBooks tokens for realm {realm_id}")

            return access_token, refresh_token

        except Exception as e:
            print(f"Error in QuickBooks OAuth callback: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    def _get_qb_headers(self, access_token):
        """Generate headers for QuickBooks API requests."""
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

    def _get_qb_base_url(self, realm_id, is_sandbox=True):
        """Get QuickBooks API base URL."""
        if is_sandbox:
            return f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}"
        return f"https://quickbooks.api.intuit.com/v3/company/{realm_id}"

    def _parse_qb_date(self, date_str):
        """Parse QuickBooks date format to ISO format."""
        if not date_str:
            return None
        try:
            # QuickBooks typically returns dates as YYYY-MM-DD
            return datetime.strptime(date_str, "%Y-%m-%d").isoformat()
        except:
            return date_str

    def normalize_line_items(self, line_items):
        """Normalize numeric fields in line items to ensure consistent data types"""
        normalized_items = []
        for item in line_items:
            normalized_item = item.copy()

            # Normalize Amount field
            if 'Amount' in normalized_item:
                normalized_item['Amount'] = float(normalized_item['Amount']) if normalized_item['Amount'] is not None else None

            # Only convert value to float if it's a numeric string
            if 'value' in normalized_item and normalized_item['value'] is not None:
                value_str = normalized_item['value']
                # Check if the value looks like a number (optional negative sign, digits, optional decimal)
                if value_str and (value_str.replace('-', '').replace('.', '').replace(',', '').isdigit()):
                    try:
                        normalized_item['value'] = float(value_str.replace(',', ''))
                    except (ValueError, TypeError):
                        # If conversion fails, keep the original value
                        normalized_item['value'] = value_str
                else:
                    # Keep non-numeric values as they are (dates, text, etc.)
                    normalized_item['value'] = value_str

            # Normalize SalesItemLineDetail fields
            if 'SalesItemLineDetail' in normalized_item:
                sales_detail = normalized_item['SalesItemLineDetail'].copy()

                if 'UnitPrice' in sales_detail:
                    sales_detail['UnitPrice'] = float(sales_detail['UnitPrice']) if sales_detail['UnitPrice'] is not None else None

                if 'Qty' in sales_detail:
                    sales_detail['Qty'] = float(sales_detail['Qty']) if sales_detail['Qty'] is not None else None

                normalized_item['SalesItemLineDetail'] = sales_detail

            normalized_items.append(normalized_item)

        return normalized_items

    async def sync_quickbooks_accounts(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks accounts and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_accounts = []
            start_position = 1
            max_results = 1000

            while True:
                # Query accounts with pagination
                query = f"SELECT * FROM Account STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                accounts = data.get("QueryResponse", {}).get("Account", [])

                if not accounts:
                    break

                for account in accounts:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": account.get("Id"),
                        "Name": account.get("Name"),
                        "FullyQualifiedName": account.get("FullyQualifiedName"),
                        "AccountType": account.get("AccountType"),
                        "AccountSubType": account.get("AccountSubType"),
                        "Classification": account.get("Classification"),
                        "AcctNum": account.get("AcctNum"),
                        "CurrentBalance": account.get("CurrentBalance"),
                        "CurrentBalanceWithSubAccounts": account.get(
                            "CurrentBalanceWithSubAccounts"
                        ),
                        "CurrencyRef": account.get("CurrencyRef"),
                        "Active": account.get("Active"),
                        "SubAccount": account.get("SubAccount"),
                        "ParentRef": account.get("ParentRef"),
                        "Description": account.get("Description"),
                        "SyncToken": account.get("SyncToken"),
                        "MetaData": account.get("MetaData"),
                        "data": account,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_account = self.mongodb.get_collection("quickbooks_account")
                    await quickbooks_account.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_account", document=doc, id=es_id)
                    stored_accounts.append(doc)
                    print(f"Indexed QuickBooks account: {account.get('Name')} ({account.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(accounts) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "accounts": stored_accounts,
                "count": len(stored_accounts)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks accounts: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_bills(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks Bills using paging and index/store them."""
        try:
            headers = self._get_qb_headers(access_token)
            base_url = self._get_qb_base_url(realm_id)

            start_position = 1
            max_results = 1000
            all_stored = []

            while True:
                query = f"SELECT * FROM Bill STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                bills = data.get("QueryResponse", {}).get("Bill", [])
                for b in bills:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": b.get("Id"),
                        "SyncToken": b.get("SyncToken"),
                        "APAccountRef": b.get("APAccountRef"),
                        "VendorRef": b.get("VendorRef"),
                        "TxnDate": self._parse_qb_date(b.get("TxnDate")),
                        "TotalAmt": b.get("TotalAmt"),
                        "CurrencyRef": b.get("CurrencyRef"),
                        "LinkedTxn": b.get("LinkedTxn"),
                        "SalesTermRef": b.get("SalesTermRef"),
                        "DueDate": self._parse_qb_date(b.get("DueDate")),
                        "Line": b.get("Line"),
                        "Balance": b.get("Balance"),
                        "MetaData": b.get("MetaData"),
                        "data": b,
                        "last_synced": datetime.utcnow().isoformat(),
                    }
                    # Upsert into MongoDB
                    quickbooks_bill = self.mongodb.get_collection("quickbooks_bill")
                    await quickbooks_bill.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )
                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_bill", document=doc, id=es_id)
                    all_stored.append(doc)

                # If we got less than max_results, we've reached the end
                if len(bills) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "bills": all_stored,
                "count": len(all_stored),
            }

        except Exception as e:
            print(f"Error fetching QuickBooks bills paged: {e}")
            return {"status": "error", "message": str(e)}

    # Sync Budgets
    async def sync_quickbooks_budgets(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks Budgets and index/store them (with paging if supported)."""
        try:
            headers = self._get_qb_headers(access_token)
            base_url = self._get_qb_base_url(realm_id)

            start_position = 1
            max_results = 1000
            all_stored = []

            while True:
                query = f"SELECT * FROM Budget STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)

                response.raise_for_status()
                data = response.json()

                budgets = data.get("QueryResponse", {}).get("Budget", [])

                for b in budgets:
                    b["BudgetDetail"] = self._normalize_line_items(b.get("BudgetDetail", []))
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": b.get("Id"),
                        "Name": b.get("Name"),
                        "StartDate": self._parse_qb_date(b.get("StartDate")),
                        "EndDate": self._parse_qb_date(b.get("EndDate")),
                        "BudgetEntryType": b.get("BudgetEntryType"),
                        "BudgetType": b.get("BudgetType"),
                        "BudgetDetail": b.get("BudgetDetail"),
                        "Active": b.get("Active"),
                        "SyncToken": b.get("SyncToken"),
                        "MetaData": b.get("MetaData"),
                        "data": b,
                        "last_synced": datetime.utcnow().isoformat(),
                    }
                    # Upsert into MongoDB
                    quickbooks_budget = self.mongodb.get_collection("quickbooks_budget")
                    await quickbooks_budget.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_budget", document=doc, id=es_id)
                    print(f"Indexed QuickBooks budget: {doc['Id']}")
                    all_stored.append(doc)

                # If we got less than max_results, we've reached the end
                if len(budgets) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "budgets": all_stored,
                "count": len(all_stored),
            }

        except Exception as e:
            print(f"Error fetching QuickBooks budgets: {e}")
            return {"status": "error", "message": str(e)}

    # Sync CashFlows
    async def sync_quickbooks_cashflows(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks Statement of Cash Flows report and index/store it."""
        try:
            headers = self._get_qb_headers(access_token)
            base_url = self._get_qb_base_url(realm_id)
            url = f"{base_url}/reports/CashFlow"
            params = {"minorversion": "65"}
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            report = data.get("Columns", {}).get("Column", [])
            header = data.get("Header", {})
            rows = data.get("Rows", {}).get("Row", [])

            doc = {
                "project_id": project_id,
                "realm_id": realm_id,
                "Header": header,
                "Rows": rows,
                "Columns": data.get("Columns", {}),
                "data": data,
                "last_synced": datetime.utcnow().isoformat(),
            }

            quickbooks_cashflow = self.mongodb.get_collection("quickbooks_cashflow")
            await quickbooks_cashflow.update_one(
                {
                    "project_id": project_id,
                    "realm_id": realm_id,
                    "Header.EndPeriod": header.get("EndPeriod"),
                },
                {"$set": doc},
                upsert=True,
            )

            # Index to Elasticsearch
            es_id = self.generate_hash(
                f"{doc.get('project_id')}-{doc.get('realm_id')}-{header.get('EndPeriod')}"
            )
            self.elastic.index_document(index="quickbooks_cashflow", document=doc, id=es_id)
            print(
                f"Synced QuickBooks CashFlow report for realm {realm_id} at date {header.get('EndPeriod')}"
            )

            return {
                "status": "success",
                "cashflow": doc
            }

        except Exception as e:
            print(f"Error fetching QuickBooks cashflows: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_quickbooks_company_info(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks company info and index it / store it."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            # Query company info
            query = "SELECT * FROM CompanyInfo"
            url = f"{base_url}/query"

            params = {"query": query, "minorversion": "65"}

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            company_infos = data.get("QueryResponse", {}).get("CompanyInfo", [])

            if not company_infos:
                return {
                    "status": "error",
                    "message": "No company info found"
                }

            company_info = company_infos[0]  # Should only be one

            if "NameValue" in company_info:
                del company_info["NameValue"]


            doc = {
                "project_id": project_id,
                "realm_id": realm_id,
                "Id": company_info.get("Id"),
                "CompanyName": company_info.get("CompanyName"),
                "LegalName": company_info.get("LegalName"),
                "CompanyAddr": company_info.get("CompanyAddr"),
                "CustomerCommunicationAddr": company_info.get(
                    "CustomerCommunicationAddr"
                ),
                "LegalAddr": company_info.get("LegalAddr"),
                "PrimaryPhone": company_info.get("PrimaryPhone"),
                "CompanyStartDate": self._parse_qb_date(
                    company_info.get("CompanyStartDate")
                ),
                "EmployerId": company_info.get("EmployerId"),
                "FiscalYearStartMonth": company_info.get("FiscalYearStartMonth"),
                "Country": company_info.get("Country"),
                "Email": company_info.get("Email"),
                "WebAddr": company_info.get("WebAddr"),
                "SupportedLanguages": company_info.get("SupportedLanguages"),
                "SyncToken": company_info.get("SyncToken"),
                "MetaData": company_info.get("MetaData"),
                "data": company_info,
                "last_synced": datetime.utcnow().isoformat(),
            }

            # Upsert into MongoDB
            quickbooks_company_info = self.mongodb.get_collection("quickbooks_company_info")
            await quickbooks_company_info.update_one(
                {
                    "project_id": project_id,
                    "realm_id": realm_id
                },
                {"$set": doc},
                upsert=True,
            )

            # Index to Elasticsearch
            es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('realm_id')}")
            self.elastic.index_document(index="quickbooks_company_info", document=doc, id=es_id)
            print(f"Indexed QuickBooks company info: {company_info.get('CompanyName')}")

            return {
                "status": "success",
                "company_info": doc
            }
        except Exception as e:
            print(f"Error fetching QuickBooks company info: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_customers(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks customers and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_customers = []
            start_position = 1
            max_results = 1000

            while True:
                # Query customers with pagination
                query = f"SELECT * FROM Customer STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                customers = data.get("QueryResponse", {}).get("Customer", [])

                if not customers:
                    break

                for customer in customers:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": customer.get("Id"),
                        "DisplayName": customer.get("DisplayName"),
                        "GivenName": customer.get("GivenName"),
                        "FamilyName": customer.get("FamilyName"),
                        "CompanyName": customer.get("CompanyName"),
                        "FullyQualifiedName": customer.get("FullyQualifiedName"),
                        "PrintOnCheckName": customer.get("PrintOnCheckName"),
                        "Active": customer.get("Active"),
                        "PrimaryPhone": customer.get("PrimaryPhone"),
                        "PrimaryEmailAddr": customer.get("PrimaryEmailAddr"),
                        "BillAddr": customer.get("BillAddr"),
                        "Taxable": customer.get("Taxable"),
                        "Job": customer.get("Job"),
                        "BillWithParent": customer.get("BillWithParent"),
                        "Balance": customer.get("Balance"),
                        "BalanceWithJobs": customer.get("BalanceWithJobs"),
                        "PreferredDeliveryMethod": customer.get(
                            "PreferredDeliveryMethod"
                        ),
                        "SyncToken": customer.get("SyncToken"),
                        "MetaData": customer.get("MetaData"),
                        "data": customer,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_customer = self.mongodb.get_collection("quickbooks_customer")
                    await quickbooks_customer.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_customer", document=doc, id=es_id)
                    stored_customers.append(doc)
                    print(f"Indexed QuickBooks customer: {customer.get('DisplayName')} ({customer.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(customers) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "customers": stored_customers,
                "count": len(stored_customers)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks customers: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_employees(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks employees and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_employees = []
            start_position = 1
            max_results = 1000

            while True:
                # Query employees with pagination
                query = f"SELECT * FROM Employee STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                employees = data.get("QueryResponse", {}).get("Employee", [])

                if not employees:
                    break

                for employee in employees:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": employee.get("Id"),
                        "DisplayName": employee.get("DisplayName"),
                        "GivenName": employee.get("GivenName"),
                        "FamilyName": employee.get("FamilyName"),
                        "PrintOnCheckName": employee.get("PrintOnCheckName"),
                        "Active": employee.get("Active"),
                        "PrimaryPhone": employee.get("PrimaryPhone"),
                        "PrimaryAddr": employee.get("PrimaryAddr"),
                        "SSN": employee.get("SSN"),
                        "BillableTime": employee.get("BillableTime"),
                        "SyncToken": employee.get("SyncToken"),
                        "MetaData": employee.get("MetaData"),
                        "data": employee,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_employee = self.mongodb.get_collection("quickbooks_employee")
                    await quickbooks_employee.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_employee", document=doc, id=es_id)
                    stored_employees.append(doc)
                    print(f"Indexed QuickBooks employee: {employee.get('DisplayName')} ({employee.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(employees) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "employees": stored_employees,
                "count": len(stored_employees)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks employees: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_estimates(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks estimates and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_estimates = []
            start_position = 1
            max_results = 1000

            while True:
                # Query estimates with pagination
                query = f"SELECT * FROM Estimate STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                estimates = data.get("QueryResponse", {}).get("Estimate", [])

                if not estimates:
                    break

                for estimate in estimates:
                    line_items = self._normalize_line_items(estimate.get("Line", []))
                    estimate["Line"] = line_items  # Update with normalized line items

                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": estimate.get("Id"),
                        "DocNumber": estimate.get("DocNumber"),
                        "TxnDate": estimate.get("TxnDate"),
                        "TxnStatus": estimate.get("TxnStatus"),
                        "TotalAmt": estimate.get("TotalAmt"),
                        "CurrencyRef": estimate.get("CurrencyRef"),
                        "CustomerRef": estimate.get("CustomerRef"),
                        "CustomerMemo": estimate.get("CustomerMemo"),
                        "BillAddr": estimate.get("BillAddr"),
                        "ShipAddr": estimate.get("ShipAddr"),
                        "BillEmail": estimate.get("BillEmail"),
                        "ProjectRef": estimate.get("ProjectRef"),
                        "PrintStatus": estimate.get("PrintStatus"),
                        "EmailStatus": estimate.get("EmailStatus"),
                        "Line": line_items,
                        "ApplyTaxAfterDiscount": estimate.get("ApplyTaxAfterDiscount"),
                        "CustomField": estimate.get("CustomField"),
                        "TxnTaxDetail": estimate.get("TxnTaxDetail"),
                        "SyncToken": estimate.get("SyncToken"),
                        "MetaData": estimate.get("MetaData"),
                        "data": estimate,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_estimate = self.mongodb.get_collection("quickbooks_estimate")
                    await quickbooks_estimate.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_estimate", document=doc, id=es_id)
                    stored_estimates.append(doc)
                    print(f"Indexed QuickBooks estimate: {estimate.get('DocNumber')} ({estimate.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(estimates) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "estimates": stored_estimates,
                "count": len(stored_estimates)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks estimates: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_invoices(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks invoices and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_invoices = []
            start_position = 1
            max_results = 1000

            while True:
                # Query invoices with pagination
                query = f"SELECT * FROM Invoice STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                invoices = data.get("QueryResponse", {}).get("Invoice", [])

                if not invoices:
                    break

                for invoice in invoices:
                    line_items = self._normalize_line_items(invoice.get("Line", []))
                    invoice["Line"] = line_items 

                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": invoice.get("Id"),
                        "DocNumber": invoice.get("DocNumber"),
                        "TxnDate": invoice.get("TxnDate"),
                        "DueDate": invoice.get("DueDate"),
                        "TotalAmt": invoice.get("TotalAmt"),
                        "Balance": invoice.get("Balance"),
                        "PrintStatus": invoice.get("PrintStatus"),
                        "EmailStatus": invoice.get("EmailStatus"),
                        "ApplyTaxAfterDiscount": invoice.get("ApplyTaxAfterDiscount"),
                        "Line": line_items,
                        "SalesTermRef": invoice.get("SalesTermRef"),
                        "CustomerMemo": invoice.get("CustomerMemo"),
                        "ProjectRef": invoice.get("ProjectRef"),
                        "Deposit": invoice.get("Deposit"),
                        "CustomerRef": invoice.get("CustomerRef"),
                        "TxnTaxDetail": invoice.get("TxnTaxDetail"),
                        "LinkedTxn": invoice.get("LinkedTxn"),
                        "BillEmail": invoice.get("BillEmail"),
                        "ShipAddr": invoice.get("ShipAddr"),
                        "BillAddr": invoice.get("BillAddr"),
                        "CustomField": invoice.get("CustomField"),
                        "SyncToken": invoice.get("SyncToken"),
                        "MetaData": invoice.get("MetaData"),
                        "data": invoice,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_invoice = self.mongodb.get_collection("quickbooks_invoice")
                    await quickbooks_invoice.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_invoice", document=doc, id=es_id)
                    stored_invoices.append(doc)
                    print(f"Indexed QuickBooks invoice: {invoice.get('DocNumber')} ({invoice.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(invoices) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "invoices": stored_invoices,
                "count": len(stored_invoices)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks invoices: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_items(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks items and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_items = []
            start_position = 1
            max_results = 1000

            while True:
                # Query items with pagination
                query = f"SELECT * FROM Item STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                items = data.get("QueryResponse", {}).get("Item", [])

                if not items:
                    break

                for item in items:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": item.get("Id"),
                        "Name": item.get("Name"),
                        "FullyQualifiedName": item.get("FullyQualifiedName"),
                        "Type": item.get("Type"),
                        "Active": item.get("Active"),
                        "SyncToken": item.get("SyncToken"),
                        "MetaData": item.get("MetaData"),
                        "data": item,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_item = self.mongodb.get_collection("quickbooks_item")
                    await quickbooks_item.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_item", document=doc, id=es_id)
                    stored_items.append(doc)
                    print(f"Indexed QuickBooks item: {item.get('Name')} ({item.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(items) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "items": stored_items,
                "count": len(stored_items)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks items: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    # --- Sync Payments ---
    async def sync_quickbooks_payments(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks payments and index them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_payments = []
            start_position = 1
            max_results = 1000

            while True:
                # Query payments with pagination
                query = f"SELECT * FROM Payment STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                payments = data.get("QueryResponse", {}).get("Payment", [])

                if not payments:
                    break

                for payment in payments:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": payment.get("Id"),
                        "TxnDate": payment.get("TxnDate"),
                        "TotalAmt": payment.get("TotalAmt"),
                        "UnappliedAmt": payment.get("UnappliedAmt"),
                        "DepositToAccountRef": payment.get("DepositToAccountRef"),
                        "ProjectRef": payment.get("ProjectRef"),
                        "ProcessPayment": payment.get("ProcessPayment"),
                        "Line": payment.get("Line"),
                        "CustomerRef": payment.get("CustomerRef"),
                        "SyncToken": payment.get("SyncToken"),
                        "MetaData": payment.get("MetaData"),
                        "data": payment,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_payment = self.mongodb.get_collection("quickbooks_payment")
                    await quickbooks_payment.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_payment", document=doc, id=es_id)
                    stored_payments.append(doc)
                    print(f"Indexed QuickBooks Payment: {payment.get('PaymentRefNum')} ({payment.get('Id')})")

                if len(payments) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "payments": stored_payments,
                "count": len(stored_payments)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks payments: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_quickbooks_preferences(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks company preferences and index them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            # Preferences is a singleton endpoint, no pagination needed
            url = f"{base_url}/preferences"

            response = requests.get(url, headers=headers, params={"minorversion": "65"})
            response.raise_for_status()
            data = response.json()

            prefs = data.get("Preferences", {})

            if prefs:
                doc = {
                    "project_id": project_id,
                    "realm_id": realm_id,
                    "Id": prefs.get("Id"),
                    "AccountingInfoPrefs": prefs.get("AccountingInfoPrefs"),
                    "ProductAndServicesPrefs": prefs.get("ProductAndServicesPrefs"),
                    "SalesFormsPrefs": prefs.get("SalesFormsPrefs"),
                    "VendorAndPurchasesPrefs": prefs.get("VendorAndPurchasesPrefs"),
                    "TaxPrefs": prefs.get("TaxPrefs"),
                    "OtherPrefs": prefs.get("OtherPrefs"),
                    "TimeTrackingPrefs": prefs.get("TimeTrackingPrefs"),
                    "CurrencyPrefs": prefs.get("CurrencyPrefs"),
                    "EmailMessagesPrefs": prefs.get("EmailMessagesPrefs"),
                    "ReportPrefs": prefs.get("ReportPrefs"),
                    "SyncToken": prefs.get("SyncToken"),
                    "MetaData": prefs.get("MetaData"),
                    "data": prefs,
                    "last_synced": datetime.utcnow().isoformat(),
                }

                # Upsert into MongoDB
                quickbooks_preferences = self.mongodb.get_collection("quickbooks_preferences")
                await quickbooks_preferences.update_one(
                    {"project_id": project_id, "realm_id": realm_id},
                    {"$set": doc},
                    upsert=True,
                )

                # Index to Elasticsearch
                es_id = self.generate_hash(f"{doc.get('project_id')}-{doc.get('realm_id')}")
                self.elastic.index_document(index="quickbooks_preferences", document=doc, id=es_id)
                print(f"Indexed QuickBooks Preferences for Realm: {realm_id}")

                return {"status": "success", "count": 1}

            return {"status": "success", "count": 0, "message": "No preferences found"}

        except Exception as e:
            print(f"Error fetching QuickBooks preferences: {e}")
            return {"status": "error", "message": str(e)}

    # --- Sync Profit And Loss ---
    async def sync_quickbooks_profit_and_loss(self, access_token: str, project_id: str, realm_id: str, start_date: str = None, end_date: str = None):
        """
        Fetch QuickBooks Profit and Loss Report.
        Note: P&L is a report, not a list of entities. It requires a date range.
        Defaults to 'This Fiscal Year' if no dates provided.
        """
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            url = f"{base_url}/reports/ProfitAndLoss"

            params = {
                "minorversion": "65",
                "date_macro": "This Fiscal Year"
            }

            if start_date and end_date:
                params = {
                    "minorversion": "65",
                    "start_date": start_date,
                    "end_date": end_date
                }

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            report_data = response.json()

            # Extract Header info to form a unique ID for this report snapshot
            header = report_data.get("Header", {})
            report_start = header.get("StartPeriod")
            report_end = header.get("EndPeriod")
            accounting_method = header.get("Option", [{}])[0].get("Value", "Accrual") # Simplification

            # Create a unique hash for this specific report configuration
            report_unique_string = f"{project_id}{realm_id}{report_start}{report_end}{accounting_method}"
            es_id = self.generate_hash(report_unique_string)

            doc = {
                "project_id": project_id,
                "realm_id": realm_id,
                "Header": header,
                "Rows": report_data.get("Rows", {}),
                "Columns": report_data.get("Columns", {}),
                "last_synced": datetime.utcnow().isoformat(),
            }

            # Upsert into MongoDB
            quickbooks_profit_and_loss = self.mongodb.get_collection("quickbooks_profit_and_loss")
            await quickbooks_profit_and_loss.update_one(
                {
                    "project_id": project_id,
                    "Header.StartPeriod": report_start,
                    "Header.EndPeriod": report_end,
                },
                {"$set": doc},
                upsert=True,
            )

            # Index to Elasticsearch
            self.elastic.index_document(index="quickbooks_profit_and_loss", document=doc, id=es_id)
            print(f"Indexed QuickBooks P&L Report: {report_start} to {report_end}")

            return {
                "status": "success",
                "report_id": es_id,
                "period": f"{report_start} to {report_end}"
            }

        except Exception as e:
            print(f"Error fetching QuickBooks P&L: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_quickbooks_purchase_orders(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks purchase orders and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_purchase_orders = []
            start_position = 1
            max_results = 1000

            while True:
                # Query purchase orders with pagination
                query = f"SELECT * FROM PurchaseOrder STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                purchase_orders = data.get("QueryResponse", {}).get("PurchaseOrder", [])

                if not purchase_orders:
                    break

                for po in purchase_orders:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": po.get("Id"),
                        "DocNumber": po.get("DocNumber"),
                        "TxnDate": self._parse_qb_date(po.get("TxnDate")),
                        "TotalAmt": po.get("TotalAmt"),
                        "POStatus": po.get("POStatus"),
                        "EmailStatus": po.get("EmailStatus"),
                        "POEmail": po.get("POEmail"),
                        "APAccountRef": po.get("APAccountRef"),
                        "CurrencyRef": po.get("CurrencyRef"),
                        "ShipAddr": po.get("ShipAddr"),
                        "VendorAddr": po.get("VendorAddr"),
                        "VendorRef": po.get("VendorRef"),
                        "Line": po.get("Line", []),
                        "CustomField": po.get("CustomField"),
                        "SyncToken": po.get("SyncToken"),
                        "MetaData": po.get("MetaData"),
                        "data": po,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_purchase_order = self.mongodb.get_collection("quickbooks_purchase_order")
                    await quickbooks_purchase_order.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_purchase_order", document=doc, id=es_id)
                    stored_purchase_orders.append(doc)
                    print(f"Indexed QuickBooks purchase order: {po.get('DocNumber')} ({po.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(purchase_orders) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "purchase_orders": stored_purchase_orders,
                "count": len(stored_purchase_orders)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks purchase orders: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_credit_memos(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks credit memos and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_credit_memos = []
            start_position = 1
            max_results = 1000

            while True:
                # Query credit memos with pagination
                query = f"SELECT * FROM CreditMemo STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                credit_memos = data.get("QueryResponse", {}).get("CreditMemo", [])

                if not credit_memos:
                    break

                for cm in credit_memos:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": cm.get("Id"),
                        "DocNumber": cm.get("DocNumber"),
                        "TxnDate": self._parse_qb_date(cm.get("TxnDate")),
                        "TotalAmt": cm.get("TotalAmt"),
                        "RemainingCredit": cm.get("RemainingCredit"),
                        "Balance": cm.get("Balance"),
                        "PrintStatus": cm.get("PrintStatus"),
                        "EmailStatus": cm.get("EmailStatus"),
                        "ApplyTaxAfterDiscount": cm.get("ApplyTaxAfterDiscount"),
                        "Line": cm.get("Line", []),
                        "CustomerMemo": cm.get("CustomerMemo"),
                        "ProjectRef": cm.get("ProjectRef"),
                        "CustomerRef": cm.get("CustomerRef"),
                        "TxnTaxDetail": cm.get("TxnTaxDetail"),
                        "CustomField": cm.get("CustomField"),
                        "ShipAddr": cm.get("ShipAddr"),
                        "BillAddr": cm.get("BillAddr"),
                        "BillEmail": cm.get("BillEmail"),
                        "SyncToken": cm.get("SyncToken"),
                        "MetaData": cm.get("MetaData"),
                        "data": cm,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_credit_memo = self.mongodb.get_collection("quickbooks_credit_memo")
                    await quickbooks_credit_memo.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_credit_memo", document=doc, id=es_id)
                    stored_credit_memos.append(doc)
                    print(f"Indexed QuickBooks credit memo: {cm.get('DocNumber')} ({cm.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(credit_memos) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "credit_memos": stored_credit_memos,
                "count": len(stored_credit_memos)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks credit memos: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_sales_receipts(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks sales receipts and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_sales_receipts = []
            start_position = 1
            max_results = 1000

            while True:
                # Query sales receipts with pagination
                query = f"SELECT * FROM SalesReceipt STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                sales_receipts = data.get("QueryResponse", {}).get("SalesReceipt", [])

                if not sales_receipts:
                    break

                for sr in sales_receipts:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": sr.get("Id"),
                        "DocNumber": sr.get("DocNumber"),
                        "TxnDate": self._parse_qb_date(sr.get("TxnDate")),
                        "TotalAmt": sr.get("TotalAmt"),
                        "Balance": sr.get("Balance"),
                        "PrintStatus": sr.get("PrintStatus"),
                        "EmailStatus": sr.get("EmailStatus"),
                        "PaymentRefNum": sr.get("PaymentRefNum"),
                        "PaymentMethodRef": sr.get("PaymentMethodRef"),
                        "DepositToAccountRef": sr.get("DepositToAccountRef"),
                        "Line": sr.get("Line", []),
                        "ApplyTaxAfterDiscount": sr.get("ApplyTaxAfterDiscount"),
                        "CustomerMemo": sr.get("CustomerMemo"),
                        "ProjectRef": sr.get("ProjectRef"),
                        "CustomerRef": sr.get("CustomerRef"),
                        "TxnTaxDetail": sr.get("TxnTaxDetail"),
                        "BillAddr": sr.get("BillAddr"),
                        "CustomField": sr.get("CustomField"),
                        "SyncToken": sr.get("SyncToken"),
                        "MetaData": sr.get("MetaData"),
                        "data": sr,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_sales_receipt = self.mongodb.get_collection("quickbooks_sales_receipt")
                    await quickbooks_sales_receipt.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_sales_receipt", document=doc, id=es_id)
                    stored_sales_receipts.append(doc)
                    print(f"Indexed QuickBooks sales receipt: {sr.get('DocNumber')} ({sr.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(sales_receipts) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "sales_receipts": stored_sales_receipts,
                "count": len(stored_sales_receipts)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks sales receipts: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_refund_receipts(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks refund receipts and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_refund_receipts = []
            start_position = 1
            max_results = 1000

            while True:
                # Query refund receipts with pagination
                query = f"SELECT * FROM RefundReceipt STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                refund_receipts = data.get("QueryResponse", {}).get("RefundReceipt", [])

                if not refund_receipts:
                    break

                for rr in refund_receipts:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": rr.get("Id"),
                        "DocNumber": rr.get("DocNumber"),
                        "TxnDate": self._parse_qb_date(rr.get("TxnDate")),
                        "TotalAmt": rr.get("TotalAmt"),
                        "Balance": rr.get("Balance"),
                        "PrintStatus": rr.get("PrintStatus"),
                        "PaymentMethodRef": rr.get("PaymentMethodRef"),
                        "DepositToAccountRef": rr.get("DepositToAccountRef"),
                        "Line": rr.get("Line", []),
                        "ApplyTaxAfterDiscount": rr.get("ApplyTaxAfterDiscount"),
                        "CustomerMemo": rr.get("CustomerMemo"),
                        "CustomerRef": rr.get("CustomerRef"),
                        "BillAddr": rr.get("BillAddr"),
                        "ShipAddr": rr.get("ShipAddr"),
                        "BillEmail": rr.get("BillEmail"),
                        "CustomField": rr.get("CustomField"),
                        "TxnTaxDetail": rr.get("TxnTaxDetail"),
                        "SyncToken": rr.get("SyncToken"),
                        "MetaData": rr.get("MetaData"),
                        "data": rr,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_refund_receipt = self.mongodb.get_collection("quickbooks_refund_receipt")
                    await quickbooks_refund_receipt.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_refund_receipt", document=doc, id=es_id)
                    stored_refund_receipts.append(doc)
                    print(f"Indexed QuickBooks refund receipt: {rr.get('DocNumber')} ({rr.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(refund_receipts) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "refund_receipts": stored_refund_receipts,
                "count": len(stored_refund_receipts)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks refund receipts: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_journal_entries(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks journal entries and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_journal_entries = []
            start_position = 1
            max_results = 1000

            while True:
                # Query journal entries with pagination
                query = f"SELECT * FROM JournalEntry STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                journal_entries = data.get("QueryResponse", {}).get("JournalEntry", [])

                if not journal_entries:
                    break

                for je in journal_entries:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": je.get("Id"),
                        "TxnDate": self._parse_qb_date(je.get("TxnDate")),
                        "Line": je.get("Line", []),
                        "Adjustment": je.get("Adjustment"),
                        "TxnTaxDetail": je.get("TxnTaxDetail"),
                        "SyncToken": je.get("SyncToken"),
                        "MetaData": je.get("MetaData"),
                        "data": je,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_journal_entry = self.mongodb.get_collection("quickbooks_journal_entry")
                    await quickbooks_journal_entry.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_journal_entry", document=doc, id=es_id)
                    stored_journal_entries.append(doc)
                    print(f"Indexed QuickBooks journal entry: {je.get('DocNumber')} ({je.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(journal_entries) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "journal_entries": stored_journal_entries,
                "count": len(stored_journal_entries)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks journal entries: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_vendors(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks vendors and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_vendors = []
            start_position = 1
            max_results = 1000

            while True:
                # Query vendors with pagination
                query = f"SELECT * FROM Vendor STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                vendors = data.get("QueryResponse", {}).get("Vendor", [])

                if not vendors:
                    break

                for vendor in vendors:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": vendor.get("Id"),
                        "DisplayName": vendor.get("DisplayName"),
                        "GivenName": vendor.get("GivenName"),
                        "FamilyName": vendor.get("FamilyName"),
                        "CompanyName": vendor.get("CompanyName"),
                        "PrintOnCheckName": vendor.get("PrintOnCheckName"),
                        "Active": vendor.get("Active"),
                        "PrimaryPhone": vendor.get("PrimaryPhone"),
                        "PrimaryEmailAddr": vendor.get("PrimaryEmailAddr"),
                        "WebAddr": vendor.get("WebAddr"),
                        "BillAddr": vendor.get("BillAddr"),
                        "AcctNum": vendor.get("AcctNum"),
                        "Vendor1099": vendor.get("Vendor1099"),
                        "Balance": vendor.get("Balance"),
                        "SyncToken": vendor.get("SyncToken"),
                        "MetaData": vendor.get("MetaData"),
                        "data": vendor,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_vendor = self.mongodb.get_collection("quickbooks_vendor")
                    await quickbooks_vendor.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_vendor", document=doc, id=es_id)
                    stored_vendors.append(doc)
                    print(f"Indexed QuickBooks vendor: {vendor.get('DisplayName')} ({vendor.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(vendors) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "vendors": stored_vendors,
                "count": len(stored_vendors)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks vendors: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_transfers(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks transfers and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_transfers = []
            start_position = 1
            max_results = 1000

            while True:
                # Query transfers with pagination
                query = f"SELECT * FROM Transfer STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                transfers = data.get("QueryResponse", {}).get("Transfer", [])

                if not transfers:
                    break

                for transfer in transfers:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": transfer.get("Id"),
                        "TxnDate": self._parse_qb_date(transfer.get("TxnDate")),
                        "Amount": transfer.get("Amount"),
                        "FromAccountRef": transfer.get("FromAccountRef"),
                        "ToAccountRef": transfer.get("ToAccountRef"),
                        "SyncToken": transfer.get("SyncToken"),
                        "MetaData": transfer.get("MetaData"),
                        "data": transfer,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_transfer = self.mongodb.get_collection("quickbooks_transfer")
                    await quickbooks_transfer.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_transfer", document=doc, id=es_id)
                    stored_transfers.append(doc)
                    print(f"Indexed QuickBooks transfer: {transfer.get('Id')} - {transfer.get('Amount')}")

                # If we got less than max_results, we've reached the end
                if len(transfers) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "transfers": stored_transfers,
                "count": len(stored_transfers)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks transfers: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_deposits(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks deposits and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_deposits = []
            start_position = 1
            max_results = 1000

            while True:
                # Query deposits with pagination
                query = f"SELECT * FROM Deposit STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                deposits = data.get("QueryResponse", {}).get("Deposit", [])

                if not deposits:
                    break

                for deposit in deposits:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": deposit.get("Id"),
                        "TxnDate": self._parse_qb_date(deposit.get("TxnDate")),
                        "TotalAmt": deposit.get("TotalAmt"),
                        "DepositToAccountRef": deposit.get("DepositToAccountRef"),
                        "Line": deposit.get("Line", []),
                        "SyncToken": deposit.get("SyncToken"),
                        "MetaData": deposit.get("MetaData"),
                        "data": deposit,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_deposit = self.mongodb.get_collection("quickbooks_deposit")
                    await quickbooks_deposit.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_deposit", document=doc, id=es_id)
                    stored_deposits.append(doc)
                    print(f"Indexed QuickBooks deposit: {deposit.get('DocNumber')} ({deposit.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(deposits) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "deposits": stored_deposits,
                "count": len(stored_deposits)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks deposits: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_vendor_credits(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks vendor credits and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_vendor_credits = []
            start_position = 1
            max_results = 1000

            while True:
                # Query vendor credits with pagination
                query = f"SELECT * FROM VendorCredit STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                vendor_credits = data.get("QueryResponse", {}).get("VendorCredit", [])

                if not vendor_credits:
                    break

                for vc in vendor_credits:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": vc.get("Id"),
                        "TxnDate": self._parse_qb_date(vc.get("TxnDate")),
                        "TotalAmt": vc.get("TotalAmt"),
                        "VendorRef": vc.get("VendorRef"),
                        "APAccountRef": vc.get("APAccountRef"),
                        "Line": vc.get("Line", []),
                        "SyncToken": vc.get("SyncToken"),
                        "MetaData": vc.get("MetaData"),
                        "data": vc,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_vendor_credit = self.mongodb.get_collection("quickbooks_vendor_credit")
                    await quickbooks_vendor_credit.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_vendor_credit", document=doc, id=es_id)
                    stored_vendor_credits.append(doc)
                    print(f"Indexed QuickBooks vendor credit: {vc.get('DocNumber')} ({vc.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(vendor_credits) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "vendor_credits": stored_vendor_credits,
                "count": len(stored_vendor_credits)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks vendor credits: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def sync_quickbooks_bill_payments(self, access_token: str, project_id: str, realm_id: str):
        """Fetch QuickBooks bill payments and index them / store them."""
        try:
            base_url = self._get_qb_base_url(realm_id)
            headers = self._get_qb_headers(access_token)

            stored_bill_payments = []
            start_position = 1
            max_results = 1000

            while True:
                # Query bill payments with pagination
                query = f"SELECT * FROM BillPayment STARTPOSITION {start_position} MAXRESULTS {max_results}"
                url = f"{base_url}/query"

                params = {"query": query, "minorversion": "65"}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                bill_payments = data.get("QueryResponse", {}).get("BillPayment", [])

                if not bill_payments:
                    break

                for bp in bill_payments:
                    doc = {
                        "project_id": project_id,
                        "realm_id": realm_id,
                        "Id": bp.get("Id"),
                        "TxnDate": self._parse_qb_date(bp.get("TxnDate")),
                        "TotalAmt": bp.get("TotalAmt"),
                        "PayType": bp.get("PayType"),
                        "PrivateNote": bp.get("PrivateNote"),
                        "VendorRef": bp.get("VendorRef"),
                        "Line": bp.get("Line", []),
                        "CheckPayment": bp.get("CheckPayment"),
                        "SyncToken": bp.get("SyncToken"),
                        "MetaData": bp.get("MetaData"),
                        "data": bp,
                        "last_synced": datetime.utcnow().isoformat(),
                    }

                    # Upsert into MongoDB
                    quickbooks_bill_payment = self.mongodb.get_collection("quickbooks_bill_payment")
                    await quickbooks_bill_payment.update_one(
                        {
                            "project_id": project_id,
                            "realm_id": realm_id,
                            "Id": doc["Id"],
                        },
                        {"$set": doc},
                        upsert=True,
                    )

                    # Index to Elasticsearch
                    es_id = self.generate_hash(
                        f"{doc.get('project_id')}-{doc.get('realm_id')}-{doc.get('Id')}"
                    )
                    self.elastic.index_document(index="quickbooks_bill_payment", document=doc, id=es_id)
                    stored_bill_payments.append(doc)
                    print(f"Indexed QuickBooks bill payment: {bp.get('DocNumber')} ({bp.get('Id')})")

                # If we got less than max_results, we've reached the end
                if len(bill_payments) < max_results:
                    break

                start_position += max_results

            return {
                "status": "success",
                "bill_payments": stored_bill_payments,
                "count": len(stored_bill_payments)
            }
        except Exception as e:
            print(f"Error fetching QuickBooks bill payments: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def update_quickbooks_secret_key(self, project_id: str, key: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"quickbooks_refresh_key": key}},
        )
        return True if project.modified_count > 0 else False

    async def remove_quickbooks_secret_key(self, project_id: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$unset": {"quickbooks_refresh_key": 1}},
        )
        return True if project.modified_count > 0 else False

    def es_remove_quickbooks_data(self, project_id: str) -> bool:
        """
        Remove all Quickbooks_-related data for a given project from Elasticsearch.
        """
        if not project_id:
            return False
        indices = []
        indices = self.elastic.list_indices(pattern="quickbooks_*")

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
                logger.info(f"Deleted Quickbooks data from index: {index} for project_id: {project_id}")
            except exceptions.NotFoundError:
                logger.error(f"Index not found: {index}, skipping.")
            except Exception as e:
                logger.error(f"Error deleting data from index {index}: {str(e)}")
                return False
        return True

    async def disconnect_quickbooks(self, project_id: str):
        # remove Quickbooks data from elasticsearch and mongodb
        status = self.es_remove_quickbooks_data(project_id)
        prefix = "quickbooks_"
        collections = await self.mongodb.list_collections()

        collections = [c for c in collections if c.startswith(prefix)]
        # 3. Remove documents where project_id exists
        for col_name in collections:
            col = self.mongodb.get_collection(col_name)
            result = await col.delete_many({"project_id": project_id})
            logger.info(f"Deleted {result.deleted_count} documents from {col_name}")
        return status


ServiceRegistry.register_service("quickbooks", QuickbooksService())
