import os

ES_LABELLING_INDEX = os.getenv("ES_LABELLING_INDEX", "labelled_data")
ES_CATEGORY_INDEX = os.getenv("ES_CATEGORY_INDEX", "categories")
ES_INDEX = os.getenv("ES_INDEX", "bank_statement_lines")
ES_BANK_STATEMENT_BALANCES = os.getenv("ES_INDEX", "bank_statement_balances")
ES_ANNOTATIONS_INDEX = os.getenv("ES_ANNOTATIONS_INDEX", "bank_statement_lines_labelled_data")
ES_INVOICES_INDEX = os.getenv("ES_INVOICES_INDEX", "stripe_invoices")
ES_CUSTOMERS_INDEX = os.getenv("ES_CUSTOMERS_INDEX", "stripe_customers")
ES_PRODUCTS_INDEX = os.getenv("ES_PRODUCTS_INDEX", "stripe_products")
ES_SUBSCRIPTIONS_INDEX = os.getenv("ES_SUBSCRIPTIONS_INDEX", "stripe_subscriptions")
ES_BALANCETRANSACTIONS_INDEX = os.getenv("ES_BALANCETRANSACTIONS_INDEX", "stripe_balancetransactions")
ES_EVENTS_INDEX = os.getenv("ES_EVENTS_INDEX", "stripe_events")
ES_CHARGES_INDEX = os.getenv("ES_CHARGES_INDEX", "stripe_charges")
ES_REFUNDS_INDEX = os.getenv("ES_REFUNDS_INDEX", "stripe_refunds")
ES_PAYOUTS_INDEX = os.getenv("ES_PAYOUTS_INDEX", "stripe_payouts")
ES_BALANCE_INDEX = os.getenv("ES_BALANCE_INDEX", "stripe_balance")
ES_FILES_INDEX = os.getenv("ES_FILES_INDEX", "stripe_files")
ES_MANDATES_INDEX = os.getenv("ES_MANDATES_INDEX", "stripe_mandates")
ES_PAYMENT_INTENTS_INDEX = os.getenv("ES_PAYMENT_INTENTS_INDEX", "stripe_payment_intents")
ES_PLANS_INDEX = os.getenv("ES_PLANS_INDEX", "stripe_plans")
ES_COUPONS_INDEX = os.getenv("ES_COUPONS_INDEX", "stripe_coupons")
ES_DISPUTES_INDEX = os.getenv("ES_DISPUTES_INDEX", "stripe_disputes")
ES_PAYMENT_METHODS_INDEX = os.getenv("ES_PAYMENT_METHODS_INDEX", "stripe_payment_methods")
ES_SETUP_INTENTS_INDEX = os.getenv("ES_SETUP_INTENTS_INDEX", "stripe_setup_intents")
ES_TAX_RATES_INDEX = os.getenv("ES_TAX_RATES_INDEX", "stripe_tax_rates")
ES_APPLICATION_FEES_INDEX = os.getenv("ES_APPLICATION_FEES_INDEX", "stripe_application_fees")
ES_TRANSFERS_INDEX = os.getenv("ES_TRANSFERS_INDEX", "stripe_transfers")
ES_PAYPAL_INVOICES_INDEX = os.getenv("ES_PAYPAL_INVOICES_INDEX", "paypal_invoices")
ES_PAYPAL_SUBSCRIPTIONS_INDEX = os.getenv("ES_PAYPAL_SUBSCRIPTIONS_INDEX", "paypal_subscriptions")
ES_PAYPAL_BALANCES_INDEX = os.getenv("ES_PAYPAL_BALANCES_INDEX", "paypal_balances")
ES_PAYPAL_USERINFO_INDEX = os.getenv("ES_PAYPAL_USERINFO_INDEX", "paypal_userinfo")
ES_PAYPAL_PAYMENT_TOKENS_INDEX = os.getenv("ES_PAYPAL_PAYMENT_TOKENS_INDEX", "paypal_payment_tokens")
ES_PAYPAL_PRODUCTS_INDEX = os.getenv("ES_PAYPAL_PRODUCTS_INDEX", "paypal_products")
ES_PAYPAL_PLANS_INDEX = os.getenv("ES_PAYPAL_PLANS_INDEX", "paypal_plans")
ES_PAYPAL_TRANSACTIONS_INDEX = os.getenv("ES_PAYPAL_TRANSACTIONS_INDEX", "paypal_transactions")
ES_PAYPAL_DISPUTES_INDEX = os.getenv("ES_PAYPAL_DISPUTES_INDEX", "paypal_disputes")
ES_XERO_TENANTS_INDEX = os.getenv("ES_XERO_TENANTS_INDEX", "xero_tenants")
ES_XERO_INVOICES_INDEX = os.getenv("ES_XERO_INVOICES_INDEX", "xero_invoices")
ES_XERO_ACCOUNTS_INDEX = os.getenv("ES_XERO_ACCOUNTS_INDEX", "xero_accounts")
ES_XERO_BANK_TRANSACTIONS_INDEX = os.getenv("ES_XERO_BANK_TRANSACTIONS_INDEX", "xero_bank_transactions")
ES_XERO_BANK_TRANSFERS_INDEX = os.getenv("ES_XERO_BANK_TRANSFERS_INDEX", "xero_bank_transfers")
ES_XERO_BATCH_PAYMENTS_INDEX = os.getenv("ES_XERO_BATCH_PAYMENTS_INDEX", "xero_batch_payments")
ES_XERO_BUDGETS_INDEX = os.getenv("ES_XERO_BUDGETS_INDEX", "xero_budgets")
ES_XERO_CONTACT_GROUPS_INDEX = os.getenv("ES_XERO_CONTACT_GROUPS_INDEX", "xero_contact_groups")
ES_XERO_CONTACTS_INDEX = os.getenv("ES_XERO_CONTACTS_INDEX", "xero_contacts")
ES_XERO_CREDIT_NOTES_INDEX = os.getenv("ES_XERO_CREDIT_NOTES_INDEX", "xero_credit_notes")
ES_XERO_LINKED_TRANSACTIONS_INDEX = os.getenv("ES_XERO_LINKED_TRANSACTIONS_INDEX", "xero_linked_transactions")
ES_XERO_JOURNALS_INDEX = os.getenv("ES_XERO_JOURNALS_INDEX", "xero_journals")
ES_XERO_ITEMS_INDEX = os.getenv("ES_XERO_ITEMS_INDEX", "xero_items")
ES_XERO_MANUAL_JOURNALS_INDEX = os.getenv("ES_XERO_MANUAL_JOURNALS_INDEX", "xero_manual_journals")
ES_XERO_ORGANISATION_INDEX = os.getenv("ES_XERO_ORGANISATION_INDEX", "xero_organisation")
ES_XERO_OVERPAYMENTS_INDEX = os.getenv("ES_XERO_OVERPAYMENTS_INDEX", "xero_over_payments")
ES_XERO_PAYMENTS_INDEX = os.getenv("ES_XERO_PAYMENTS_INDEX", "xero_payments")
ES_XERO_PREPAYMENTS_INDEX = os.getenv("ES_XERO_PREPAYMENTS_INDEX", "xero_prepayments")
ES_XERO_PURCHASE_ORDERS_INDEX = os.getenv("ES_XERO_PURCHASE_ORDERS_INDEX", "xero_purchase_orders")
ES_XERO_QUOTES_INDEX = os.getenv("ES_XERO_QUOTES_INDEX", "xero_quotes")
ES_XERO_REPEATING_INVOICES_INDEX = os.getenv("ES_XERO_REPEATING_INVOICES_INDEX", "xero_repeating_invoices")
ES_XERO_TAX_RATES_INDEX = os.getenv("ES_XERO_TAX_RATES_INDEX", "xero_tax_rates")
ES_XERO_USERS_INDEX = os.getenv("ES_XERO_USERS_INDEX", "xero_users")
ES_XERO_ASSET_TYPES_INDEX = os.getenv("ES_XERO_ASSET_TYPES_INDEX", "xero_asset_types")
ES_XERO_ASSETS_INDEX = os.getenv("ES_XERO_ASSETS_INDEX", "xero_assets")
ES_XERO_FEED_CONNECTIONS_INDEX = os.getenv("ES_XERO_FEED_CONNECTIONS_INDEX", "xero_feed_connections")
ES_XERO_STATEMENTS_INDEX = os.getenv("ES_XERO_STATEMENTS_INDEX", "xero_statements")
ES_XERO_PAYROLL_EMPLOYEES_INDEX = os.getenv("ES_XERO_PAYROLL_EMPLOYEES_INDEX", "xero_payroll_employees")
ES_XERO_PAYROLL_PAY_RUNS_INDEX = os.getenv("ES_XERO_PAYROLL_PAY_RUNS_INDEX", "xero_payroll_pay_runs")
ES_XERO_PAYROLL_PAYSLIPS_INDEX = os.getenv("ES_XERO_PAYROLL_PAYSLIPS_INDEX", "xero_payroll_payslips")
ES_XERO_PAYROLL_TIMESHEETS_INDEX = os.getenv("ES_XERO_PAYROLL_TIMESHEETS_INDEX", "xero_payroll_timesheets")
ES_XERO_PAYROLL_LEAVE_APPLICATIONS_INDEX = os.getenv("ES_XERO_PAYROLL_LEAVE_APPLICATIONS_INDEX", "xero_payroll_leave_applications")

ES_SCHEMA = [
    {
        "index": ES_LABELLING_INDEX,
        "index_body": {
            "settings": {
                "analysis": {
                    "char_filter": {
                        "remove_digits": {
                            "type": "pattern_replace",
                            "pattern": "\\d+",
                            "replacement": ""
                        },
                        "remove_non_letters": {
                            "type": "pattern_replace",
                            "pattern": "[^A-Za-z]",
                            "replacement": ""
                        }
                    },
                    "analyzer": {
                        "custom_normalizer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "char_filter": ["remove_digits", "remove_non_letters"],
                            "filter": ["lowercase", "asciifolding"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "normalized_key": {
                        "type": "text",
                        "analyzer": "custom_normalizer"
                    },
                    "original_value": {"type": "keyword"},
                    "data": {"type": "object"}
                }
            }
        }
    }, {
        "index": ES_CATEGORY_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "Category": {"type": "keyword"},
                    "Subcategory": {"type": "keyword"},
                    "embedding": {"type": "dense_vector", "dims": 1536}
                }
            }
        }
    }, {
        "index": ES_BANK_STATEMENT_BALANCES,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {
                        "type": "keyword"
                    },
                    "account_id": {
                        "type": "keyword"
                    },
                    "bank_name": {
                        "type": "keyword"
                    },
                    "official_name": {
                        "type": "keyword"
                    },
                    "mask": {
                        "type": "keyword"
                    },
                    "type": {
                        "type": "keyword"
                    },
                    "subtype": {
                        "type": "keyword"
                    },
                    "current_balance": {
                        "type": "float"
                    },
                    "available_balance": {
                        "type": "float"
                    },
                    "iso_currency_code": {
                        "type": "keyword"
                    }
                }
            }
        }
    }, {
        "index": ES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "date": {
                        "type": "date",
                        "format": "dd-MM-yy||dd/MM/yy"
                    },
                    "item": {
                        "type": "text",
                        "fields": {
                        "raw": {
                                "type": "keyword"
                            }
                        }
                    },
                    "amount": {
                        "type": "float"
                    },
                    "category": {
                        "type": "keyword"
                    },
                    "sub_category": {
                        "type": "keyword"
                    },
                    "transaction_id": {
                        "type": "keyword"
                    },
                    "account_id": {
                        "type": "keyword"
                    },
                    "debit_credit": {
                        "type": "keyword",
                        "description": "Indicates if the transaction is a Debit, Credit, or Unknown. Allowed values: 'Debit', 'Credit', 'Unknown'."
                    },
                    "project_id": {
                        "type": "keyword"
                    }
                }
            }
        }
    }, {
        "index": ES_ANNOTATIONS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "description": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "updated_description": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "category": {
                        "type": "keyword"
                    },
                    "sub_category": {
                        "type": "keyword"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 1536
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "updated_at": {
                        "type": "date"
                    },
                    "data_id": {
                        "type": "keyword"
                    },
                    "verified": {
                        "type": "keyword"
                    },
                }
            }
        }
    }, {
        "index": ES_INVOICES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "invoice_id": {"type": "keyword"}, 
                    "invoice_number": {"type": "keyword"},
                    "customer_name": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"  # ISO format or Unix timestamp
                    }
                }
            }
        }
    }, {
        "index": ES_CUSTOMERS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "customer_id": {"type": "keyword"},
                    "email": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"  # ISO format or Unix timestamp
                    }
                }
            }
        }
    }, {
        "index": ES_PRODUCTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "product_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_SUBSCRIPTIONS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "subscription_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_BALANCETRANSACTIONS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "balance_transaction_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_EVENTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "event_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_CHARGES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "charge_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_REFUNDS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "refund_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_PAYOUTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "payout_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_BALANCE_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "balance_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_DISPUTES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "dispute_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_FILES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "file_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_MANDATES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "file_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_PAYMENT_INTENTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "payment_intent_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_PLANS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "plan_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_COUPONS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "coupon_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_PAYMENT_METHODS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "payment_method_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_SETUP_INTENTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "setup_intent_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_TAX_RATES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tax_rate_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_TRANSFERS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "transfer_id": {"type": "keyword"},
                    "cleaned_data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_PAYPAL_INVOICES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "invoice_id": {"type": "keyword"}, 
                    "invoice_number": {"type": "keyword"},
                    "customer_name": {"type": "keyword"},
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"  # ISO format or Unix timestamp
                    }
                }
            }
        }
    }, {
        "index": ES_PAYPAL_BALANCES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "balance_id": {"type": "keyword"},
                    "currency": {"type": "keyword"},
                    "primary": {"type": "boolean"},
                    "total_balance": {"type": "object"},
                    "available_balance": {"type": "object"},
                    "withheld_balance": {"type": "object"},
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_PAYPAL_USERINFO_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "name": {"type": "text"},
                    "emails": {"type": "object"},
                    "address": {
                        "type": "object",
                        "properties": {
                            "street_address": {"type": "text"},
                            "locality": {"type": "keyword"},
                            "region": {"type": "keyword"},
                            "postal_code": {"type": "keyword"},
                            "country": {"type": "keyword"}
                        }
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_PAYPAL_SUBSCRIPTIONS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "subscription_id": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "plan_id": {"type": "keyword"},
                    "subscriber_name": {"type": "keyword"},
                    "subscriber_email": {"type": "keyword"},
                    "start_time": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "update_time": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    } ,{
        "index": ES_PAYPAL_PAYMENT_TOKENS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "token_id": {"type": "keyword"},
                    "payment_source": {"type": "object"},
                    "customer": {"type": "object"}, 
                    "status": {"type": "keyword"},
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }   
    }, {
        "index": ES_PAYPAL_PRODUCTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "product_id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "description": {"type": "text"},
                    "type": {"type": "keyword"},
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }   
    }, {
        "index": ES_PAYPAL_PLANS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "plan_id": {"type": "keyword"},
                    "product_id": {"type": "keyword"},
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "status": {"type": "keyword"},
                    "usage_type": {"type": "keyword"},
                    "billing_cycles": {"type": "object"},
                    "payment_preferences": {"type": "object"},
                    "create_time": {"type": "date"},
                    "update_time": {"type": "date"},
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_PAYPAL_TRANSACTIONS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "transaction_id": {"type": "keyword"},
                    "transaction_info": {
                        "properties": {
                            "paypal_account_id": {"type": "keyword"},
                            "transaction_id": {"type": "keyword"},
                            "transaction_event_code": {"type": "keyword"},
                            "transaction_initiation_date": {"type": "date"},
                            "transaction_updated_date": {"type": "date"},
                            "transaction_amount": {
                                "properties": {
                                    "currency_code": {"type": "keyword"},
                                    "value": {"type": "float"}
                                }
                            },
                            "transaction_status": {"type": "keyword"},
                            "transaction_subject": {"type": "text"},
                            "payer_email": {"type": "keyword"},
                            "payer_name": {"type": "text"}
                        }
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_PAYPAL_DISPUTES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "dispute_id": {"type": "keyword"},
                    "reason": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "dispute_state": {"type": "keyword"},
                    "dispute_life_cycle_stage": {"type": "keyword"},
                    "dispute_channel": {"type": "keyword"},
                    "dispute_amount": {
                        "properties": {
                            "currency_code": {"type": "keyword"},
                            "value": {"type": "float"}
                        }
                    },
                    "create_time": {"type": "date"},
                    "update_time": {"type": "date"},
                    "disputed_transaction_id": {"type": "keyword"},
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_TENANTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "tenant_name": {"type": "text"},
                    "tenant_type": {"type": "keyword"},
                    "created_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_INVOICES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "invoice_id": {"type": "keyword"},
                    "invoice_number": {"type": "keyword"},
                    "type": {"type": "keyword"},  # ACCREC or ACCPAY
                    "status": {"type": "keyword"},  # DRAFT, SUBMITTED, AUTHORISED, PAID, etc.
                    "contact_id": {"type": "keyword"},
                    "contact_name": {"type": "text"},
                    "date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "due_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "reference": {"type": "text"},
                    "currency_code": {"type": "keyword"},
                    "currency_rate": {"type": "float"},
                    "line_amount_types": {"type": "keyword"},  # Exclusive, Inclusive, NoTax
                    "sub_total": {"type": "float"},
                    "total_tax": {"type": "float"},
                    "total": {"type": "float"},
                    "amount_due": {"type": "float"},
                    "amount_paid": {"type": "float"},
                    "amount_credited": {"type": "float"},
                    "fully_paid_on_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "has_attachments": {"type": "boolean"},
                    "is_discounted": {"type": "boolean"},
                    "line_items": {"type": "object"},
                    "payments": {"type": "object"},
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_ACCOUNTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "account_id": {"type": "keyword"},
                    "code": {"type": "keyword"},
                    "name": {"type": "text"},
                    "type": {"type": "keyword"},  # BANK, CURRENT, REVENUE, EXPENSE, etc.
                    "tax_type": {"type": "keyword"},
                    "description": {"type": "text"},
                    "status": {"type": "keyword"},  # ACTIVE, ARCHIVED, DELETED
                    "class": {"type": "keyword"},  # ASSET, EQUITY, EXPENSE, LIABILITY, REVENUE
                    "enable_payments_to_account": {"type": "boolean"},
                    "show_in_expense_claims": {"type": "boolean"},
                    "bank_account_number": {"type": "keyword"},
                    "bank_account_type": {"type": "keyword"},  # BANK, CREDITCARD, PAYPAL
                    "currency_code": {"type": "keyword"},
                    "reporting_code": {"type": "keyword"},
                    "reporting_code_name": {"type": "text"},
                    "has_attachments": {"type": "boolean"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_BANK_TRANSACTIONS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "bank_transaction_id": {"type": "keyword"},
                    "type": {"type": "keyword"},  # SPEND, RECEIVE, SPEND-OVERPAYMENT, RECEIVE-OVERPAYMENT, etc.
                    "status": {"type": "keyword"},  # AUTHORISED, DELETED
                    "contact_id": {"type": "keyword"},
                    "contact_name": {"type": "text"},
                    "bank_account_id": {"type": "keyword"},
                    "bank_account_code": {"type": "keyword"},
                    "bank_account_name": {"type": "text"},
                    "date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "reference": {"type": "text"},
                    "is_reconciled": {"type": "boolean"},
                    "currency_code": {"type": "keyword"},
                    "currency_rate": {"type": "float"},
                    "line_amount_types": {"type": "keyword"},
                    "sub_total": {"type": "float"},
                    "total_tax": {"type": "float"},
                    "total": {"type": "float"},
                    "url": {"type": "keyword"},
                    "has_attachments": {"type": "boolean"},
                    "prepayment_id": {"type": "keyword"},
                    "overpayment_id": {"type": "keyword"},
                    "line_items": {"type": "object"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_BANK_TRANSFERS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "bank_transfer_id": {"type": "keyword"},
                    "date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "from_bank_account_id": {"type": "keyword"},
                    "from_bank_account_code": {"type": "keyword"},
                    "from_bank_account_name": {"type": "text"},
                    "to_bank_account_id": {"type": "keyword"},
                    "to_bank_account_code": {"type": "keyword"},
                    "to_bank_account_name": {"type": "text"},
                    "amount": {"type": "float"},
                    "from_bank_transaction_id": {"type": "keyword"},
                    "to_bank_transaction_id": {"type": "keyword"},
                    "currency_rate": {"type": "float"},
                    "from_is_reconciled": {"type": "boolean"},
                    "to_is_reconciled": {"type": "boolean"},
                    "reference": {"type": "text"},
                    "has_attachments": {"type": "boolean"},
                    "created_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_BATCH_PAYMENTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "batch_payment_id": {"type": "keyword"},
                    "account_id": {"type": "keyword"},
                    "account_code": {"type": "keyword"},
                    "account_name": {"type": "text"},
                    "reference": {"type": "text"},
                    "particulars": {"type": "text"},  # NZ only
                    "code": {"type": "text"},  # NZ only
                    "details": {"type": "text"},  # NZ only
                    "narrative": {"type": "text"},  # NZ only
                    "date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "amount": {"type": "float"},
                    "type": {"type": "keyword"},  # PAYBATCH or RECBATCH
                    "status": {"type": "keyword"},  # AUTHORISED, DELETED
                    "total_amount": {"type": "float"},
                    "is_reconciled": {"type": "boolean"},
                    "payments": {"type": "object"},  # Array of payment objects
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_BUDGETS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "budget_id": {"type": "keyword"},
                    "budget_type": {"type": "keyword"},  # OVERALL, TRACKING
                    "description": {"type": "text"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "budget_lines": {
                        "type": "nested",
                        "properties": {
                            "account_id": {"type": "keyword"},
                            "account_code": {"type": "keyword"},
                            "budget_balances": {
                                "type": "nested",
                                "properties": {
                                    "period": {"type": "date"},
                                    "amount": {"type": "float"},
                                    "unit_amount": {"type": "float"}
                                }
                            }
                        }
                    },
                    "tracking_categories": {
                        "type": "object",
                        "properties": {
                            "tracking_category_id": {"type": "keyword"},
                            "tracking_category_name": {"type": "text"},
                            "options": {
                                "type": "nested",
                                "properties": {
                                    "tracking_option_id": {"type": "keyword"},
                                    "tracking_option_name": {"type": "text"}
                                }
                            }
                        }
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_CONTACT_GROUPS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "contact_group_id": {"type": "keyword"},
                    "name": {"type": "text"},
                    "status": {"type": "keyword"},  # ACTIVE, DELETED
                    "contacts": {"type": "object"},  # Array of contacts in the group
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_CONTACTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "contact_id": {"type": "keyword"},
                    "contact_number": {"type": "keyword"},
                    "account_number": {"type": "keyword"},
                    "contact_status": {"type": "keyword"},  # ACTIVE, ARCHIVED, GDPRREQUEST
                    "name": {"type": "text"},
                    "first_name": {"type": "text"},
                    "last_name": {"type": "text"},
                    "email_address": {"type": "keyword"},
                    "skype_user_name": {"type": "keyword"},
                    "bank_account_details": {"type": "text"},
                    "tax_number": {"type": "keyword"},
                    "accounts_receivable_tax_type": {"type": "keyword"},
                    "accounts_payable_tax_type": {"type": "keyword"},
                    "is_supplier": {"type": "boolean"},
                    "is_customer": {"type": "boolean"},
                    "default_currency": {"type": "keyword"},
                    "website": {"type": "keyword"},
                    "discount": {"type": "float"},
                    "addresses": {"type": "object"},
                    "phones": {"type": "object"},
                    "contact_groups": {"type": "object"},
                    "contact_persons": {"type": "object"},
                    "balances": {"type": "object"},
                    "has_attachments": {"type": "boolean"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_CREDIT_NOTES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "credit_note_id": {"type": "keyword"},
                    "credit_note_number": {"type": "keyword"},
                    "type": {"type": "keyword"},  # ACCPAYCREDIT, ACCRECCREDIT
                    "status": {"type": "keyword"},  # DRAFT, SUBMITTED, AUTHORISED, PAID, VOIDED, DELETED
                    "contact_id": {"type": "keyword"},
                    "contact_name": {"type": "text"},
                    "date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "due_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "reference": {"type": "text"},
                    "currency_code": {"type": "keyword"},
                    "currency_rate": {"type": "float"},
                    "line_amount_types": {"type": "keyword"},
                    "sub_total": {"type": "float"},
                    "total_tax": {"type": "float"},
                    "total": {"type": "float"},
                    "remaining_credit": {"type": "float"},
                    "applied_amount": {"type": "float"},
                    "fully_paid_on_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "branding_theme_id": {"type": "keyword"},
                    "sent_to_contact": {"type": "boolean"},
                    "has_attachments": {"type": "boolean"},
                    "line_items": {"type": "object"},
                    "allocations": {"type": "object"},
                    "payments": {"type": "object"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_LINKED_TRANSACTIONS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "linked_transaction_id": {"type": "keyword"},
                    "source_transaction_id": {"type": "keyword"},
                    "source_line_item_id": {"type": "keyword"},
                    "source_transaction_type_code": {"type": "keyword"},
                    "contact_id": {"type": "keyword"},
                    "target_transaction_id": {"type": "keyword"},
                    "target_line_item_id": {"type": "keyword"},
                    "status": {"type": "keyword"},  # APPROVED, DRAFT, ONDRAFT, BILLED, VOIDED
                    "type": {"type": "keyword"},  # BILLABLEEXPENSE
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_JOURNALS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "journal_id": {"type": "keyword"},
                    "journal_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "journal_number": {"type": "keyword"},
                    "created_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "reference": {"type": "text"},
                    "source_id": {"type": "keyword"},
                    "source_type": {"type": "keyword"},  # ACCPAY, ACCREC, MANUALJOURNAL, etc.
                    "journal_lines": {"type": "object"},
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_ITEMS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "item_id": {"type": "keyword"},
                    "code": {"type": "keyword"},
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "purchase_description": {"type": "text"},
                    "inventory_asset_account_code": {"type": "keyword"},
                    "is_sold": {"type": "boolean"},
                    "is_purchased": {"type": "boolean"},
                    "is_tracked_as_inventory": {"type": "boolean"},
                    "total_cost_pool": {"type": "float"},
                    "quantity_on_hand": {"type": "float"},
                    "purchase_details": {"type": "object"},
                    "sales_details": {"type": "object"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_MANUAL_JOURNALS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "manual_journal_id": {"type": "keyword"},
                    "narration": {"type": "text"},
                    "date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "status": {"type": "keyword"},  # DRAFT, POSTED, DELETED, VOIDED
                    "line_amount_types": {"type": "keyword"},
                    "show_on_cash_basis_reports": {"type": "boolean"},
                    "has_attachments": {"type": "boolean"},
                    "journal_lines": {"type": "object"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_ORGANISATION_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "organisation_id": {"type": "keyword"},
                    "name": {"type": "text"},
                    "legal_name": {"type": "text"},
                    "pays_tax": {"type": "boolean"},
                    "version": {"type": "keyword"},
                    "organisation_type": {"type": "keyword"},
                    "base_currency": {"type": "keyword"},
                    "country_code": {"type": "keyword"},
                    "is_demo_company": {"type": "boolean"},
                    "organisation_status": {"type": "keyword"},
                    "registration_number": {"type": "keyword"},
                    "employer_identification_number": {"type": "keyword"},
                    "tax_number": {"type": "keyword"},
                    "financial_year_end_day": {"type": "integer"},
                    "financial_year_end_month": {"type": "integer"},
                    "sales_tax_basis": {"type": "keyword"},
                    "sales_tax_period": {"type": "keyword"},
                    "default_sales_tax": {"type": "keyword"},
                    "default_purchases_tax": {"type": "keyword"},
                    "period_lock_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "end_of_year_lock_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "created_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "timezone": {"type": "keyword"},
                    "organisation_entity_type": {"type": "keyword"},
                    "short_code": {"type": "keyword"},
                    "edition": {"type": "keyword"},
                    "line_of_business": {"type": "text"},
                    "addresses": {"type": "object"},
                    "phones": {"type": "object"},
                    "external_links": {"type": "object"},
                    "payment_terms": {"type": "object"},
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_OVERPAYMENTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "overpayment_id": {"type": "keyword"},
                    "type": {"type": "keyword"},  # RECEIVE-OVERPAYMENT, SPEND-OVERPAYMENT
                    "status": {"type": "keyword"},  # AUTHORISED, PAID, VOIDED
                    "contact_id": {"type": "keyword"},
                    "contact_name": {"type": "text"},
                    "date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "reference": {"type": "text"},
                    "currency_code": {"type": "keyword"},
                    "currency_rate": {"type": "float"},
                    "line_amount_types": {"type": "keyword"},
                    "sub_total": {"type": "float"},
                    "total_tax": {"type": "float"},
                    "total": {"type": "float"},
                    "remaining_credit": {"type": "float"},
                    "applied_amount": {"type": "float"},
                    "has_attachments": {"type": "boolean"},
                    "line_items": {"type": "object"},
                    "allocations": {"type": "object"},
                    "payments": {"type": "object"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_PAYMENTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "payment_id": {"type": "keyword"},
                    "invoice_id": {"type": "keyword"},
                    "account_id": {"type": "keyword"},
                    "amount": {"type": "float"},
                    "date": {"type": "date"},
                    "status": {"type": "keyword"},
                    "type": {"type": "keyword"},  # PAYMENT
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    },
    {
        "index": ES_XERO_PREPAYMENTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "prepayment_id": {"type": "keyword"},
                    "contact_id": {"type": "keyword"},
                    "amount": {"type": "float"},
                    "date": {"type": "date"},
                    "status": {"type": "keyword"},
                    "type": {"type": "keyword"},  # PREPAYMENT
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_REPEATING_INVOICES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "repeating_invoice_id": {"type": "keyword"},
                    "name": {"type": "text"},
                    "status": {"type": "keyword"},
                    "start_date": {"type": "date","format": "strict_date_optional_time||epoch_millis"},
                    "next_invoice_date": {"type": "date","format": "strict_date_optional_time||epoch_millis"},
                    "end_date": {"type": "date","format": "strict_date_optional_time||epoch_millis"},
                    "data": {"type": "object"},
                    "last_synced": {"type": "date","format": "strict_date_optional_time||epoch_millis"}
                }
            }
        }
    }, {
        "index": ES_XERO_TAX_RATES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "tax_type": {"type": "keyword"},
                    "name": {"type": "text"},
                    "status": {"type": "keyword"},
                    "tax_components": {"type": "object"},
                    "data": {"type": "object"},
                    "last_synced": {"type": "date","format": "strict_date_optional_time||epoch_millis"}
                }
            }
        }
    }, {
        "index": ES_XERO_USERS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "email_address": {"type": "keyword"},
                    "first_name": {"type": "text"},
                    "last_name": {"type": "text"},
                    "status": {"type": "keyword"},
                    "data": {"type": "object"},
                    "last_synced": {"type": "date", "format": "strict_date_optional_time||epoch_millis"}
                }
            }
        }
    }, {
        "index": ES_XERO_ASSET_TYPES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "asset_type_id": {"type": "keyword"},
                    "asset_type_name": {"type": "keyword"},
                    "fixed_asset_account_id": {"type": "keyword"},
                    "depreciation_expense_account_id": {"type": "keyword"},
                    "data": {"type": "object"},
                    "last_synced": {"type": "date", "format": "strict_date_optional_time||epoch_millis"}
                }
            }
        }
    }, {
        "index": ES_XERO_ASSETS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "asset_id": {"type": "keyword"},
                    "asset_name": {"type": "keyword"},
                    "asset_type_id": {"type": "keyword"},
                    "purchase_date": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                    "purchase_cost": {"type": "float"},
                    "status": {"type": "keyword"},
                    "data": {"type": "object"},
                    "last_synced": {"type": "date", "format": "strict_date_optional_time||epoch_millis"}
                }
            }
        }
    }, {
        "index": ES_XERO_FEED_CONNECTIONS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "feed_connection_id": {"type": "keyword"},
                    "account_number": {"type": "keyword"},
                    "account_name": {"type": "text"},
                    "status": {"type": "keyword"},
                    "data": {"type": "object"},
                    "last_synced": {"type": "date", "format": "strict_date_optional_time||epoch_millis"}
                }
            }
        }
    }, {
        "index": ES_XERO_STATEMENTS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "statement_id": {"type": "keyword"},
                    "feed_connection_id": {"type": "keyword"},
                    "start_balance": {"type": "float"},
                    "end_balance": {"type": "float"},
                    "start_date": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                    "end_date": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                    "data": {"type": "object"},
                    "last_synced": {"type": "date", "format": "strict_date_optional_time||epoch_millis"}
                }
            }
        }
    }, {
        "index": ES_XERO_PAYROLL_EMPLOYEES_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "employee_id": {"type": "keyword"},
                    "first_name": {"type": "text"},
                    "last_name": {"type": "text"},
                    "email": {"type": "keyword"},
                    "date_of_birth": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "status": {"type": "keyword"},
                    "start_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "termination_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "classification": {"type": "keyword"},
                    "ni_number": {"type": "keyword"},
                    "ird_number": {"type": "keyword"},
                    "gender": {"type": "keyword"},
                    "tax_declaration": {"type": "object"},
                    "super_memberships": {"type": "object"},
                    "home_address": {"type": "object"},
                    "address": {"type": "object"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_PAYROLL_PAY_RUNS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "pay_run_id": {"type": "keyword"},
                    "pay_run_period_start_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "pay_run_period_end_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "pay_run_status": {"type": "keyword"},
                    "payment_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "payroll_calendar_id": {"type": "keyword"},
                    "posted": {"type": "boolean"},
                    "wages": {"type": "float"},
                    "deductions": {"type": "float"},
                    "tax": {"type": "float"},
                    "super": {"type": "float"},
                    "reimbursement": {"type": "float"},
                    "net_pay": {"type": "float"},
                    "payslips": {"type": "object"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_PAYROLL_PAYSLIPS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "payslip_id": {"type": "keyword"},
                    "employee_id": {"type": "keyword"},
                    "pay_run_id": {"type": "keyword"},
                    "first_name": {"type": "text"},
                    "last_name": {"type": "text"},
                    "wages": {"type": "float"},
                    "deductions": {"type": "float"},
                    "tax": {"type": "float"},
                    "super": {"type": "float"},
                    "reimbursements": {"type": "float"},
                    "net_pay": {"type": "float"},
                    "earnings_lines": {"type": "object"},
                    "leave_earnings_lines": {"type": "object"},
                    "timesheet_earnings_lines": {"type": "object"},
                    "deduction_lines": {"type": "object"},
                    "reimbursement_lines": {"type": "object"},
                    "leave_accrual_lines": {"type": "object"},
                    "superannuation_lines": {"type": "object"},
                    "tax_lines": {"type": "object"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_PAYROLL_TIMESHEETS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "timesheet_id": {"type": "keyword"},
                    "employee_id": {"type": "keyword"},
                    "start_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "end_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "status": {"type": "keyword"},
                    "total_hours": {"type": "float"},
                    "timesheet_lines": {"type": "object"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }, {
        "index": ES_XERO_PAYROLL_LEAVE_APPLICATIONS_INDEX,
        "index_body": {
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "leave_application_id": {"type": "keyword"},
                    "employee_id": {"type": "keyword"},
                    "leave_type_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "start_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "end_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "description": {"type": "text"},
                    "status": {"type": "keyword"},
                    "leave_periods": {"type": "object"},
                    "updated_date_utc": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "data": {"type": "object"},
                    "last_synced": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    }
                }
            }
        }
    }
]