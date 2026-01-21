'use client'
import { useRouter } from "next/navigation";

// components
import StripeConnect from "@/components/chat/connectionButton/stripeConnect";
import CommingSoon from "@/components/chat/connectionButton/commingSoon";
import { useEffect, useState } from "react";

const RUNTIME_ENV = process.env.RUNTIME_ENV || 'production';
import QuickBooksConnect from "../connectionButton/quickbooksConnect";
import XeroConnect from "../connectionButton/xeroConnect";
import PaypalConnect from "../connectionButton/paypalConnect";

export default function ConnectPopup(props) {    
    const {
      stripeCode,
      dataSources,
      qbCode,
      qbRealmId,
      onOpenPaypalPopup,
      onClose,
      xeroCode,
    } = props;
    
    const [searchApp, setSearchApp] = useState("")

    const router = useRouter()

    useEffect(() => {
        const accountsWrap = document.querySelectorAll(".connection_account_details")
        let hasMatch = false;

        accountsWrap.forEach(wrap => {
            wrap.style.display = "none"
            const accounts = wrap.querySelectorAll(".account_wrap")
            
            accounts.forEach(acc => {
                acc.style.display = "none"
                const title = acc.querySelector("h1").textContent.toLowerCase()
                
                if(title.includes(searchApp.toLowerCase())) {                                  
                    wrap.style.display = "flex"
                    acc.style.display = "block"
                    hasMatch = true;                  
                }
            })

            const noResultEl = document.querySelector(".no_search_result");
            if (noResultEl) {
                noResultEl.style.display = hasMatch ? "none" : "block";
            }
        })
    },[searchApp])

    return (
        <div className="connection_wrap">
            <div className="connection_popup" id="popup_wrap">
                <h1 className="popup_title">
                    Connect Your Data Sources
                    <button 
                        className="close_button" 
                        onClick={() => {
                            const paramsToRemove = ["code", "state", "scope", "stripe_status", "connect"];
                            const pageUrl = new URL(window.location.href);
                            paramsToRemove.forEach((param) => {pageUrl.searchParams.delete(param)});
                            router.replace(pageUrl.pathname + pageUrl.search, undefined, { shallow: true });
                            onClose();
                        }}>
                            <img src="/next_images/close.svg" alt="Close"/>
                    </button>
                </h1>
                <p className="popup_description">Link your bank accounts, Stripe, Statements, and other financial tools to unlock real-time cash flow insights all in one place.</p>
                <div className="account_search">
                    <input placeholder="Search apps..." value={searchApp} onChange={(e) => setSearchApp(e.target.value)}/> 
                    <img src="/next_images/search.svg"/>   
                </div>
                <div className="no_search_result">
                    No apps found matching {searchApp}
                </div>
                <div className="popup_scroll">
                    {/* <div className="connection_account_details">
                        <h1 className="account_category">Accounts</h1>
                        <div className="connection_popup_account">
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/bank.svg" alt="Bank"/>
                                    <div>
                                        <h1>Bank Accounts & Credit Cards</h1>
                                        <p>Track bank inflows and outflows for a clear cash flow view. Spot gaps early, manage balances daily, and link multiple cards. Available with US and EU banks (UK coming soon).</p>
                                    </div>
                                    <a href="#" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </div>
                                {RUNTIME_ENV === 'production' ? <CommingSoon/> : <PlaidConnect dataSources={dataSources}/>}
                            </div>
                        </div>
                    </div> */}
                    <div className="connection_account_details">
                        <h1 className="account_category">Payment Platforms</h1>
                        <div className="connection_popup_account">
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/stripe.svg" alt="Stripe"/>
                                    <div>
                                        <h1>Stripe</h1>
                                        <p>Real-time transaction tracking.</p>
                                    </div>
                                    <a href="https://stripe.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </div>
                                <StripeConnect stripeCode={stripeCode} dataSources={dataSources}/>
                            </div>
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/paypal.svg" alt="PayPal"/>
                                    <div>
                                        <h1>PayPal</h1>
                                        <p>Track PayPal revenue in real time.</p>
                                    </div>
                                    <a href="https://paypal.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </div>
                                <PaypalConnect 
                                    dataSources={dataSources} 
                                    onOpenPaypalPopup={onOpenPaypalPopup}
                                />
                            </div>
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/chargebee.svg" alt="Chargebee" onError={(e) => e.target.style.display = 'none'} />
                                    <div>
                                        <h1>Chargebee</h1>
                                        <p>Sync subscription revenue data.</p>
                                    </div>
                                    <a href="https://www.chargebee.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link" />
                                    </a>
                                </div>
                                <CommingSoon/>
                            </div>
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/freebooks.svg" alt="Stripe"/>
                                    <div>
                                        <h1>FreshBooks</h1>
                                        <p>Manage small business accounting</p>
                                    </div>
                                    <a href="https://www.freshbooks.com" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </div>
                                <CommingSoon/>
                            </div>
                        </div>
                    </div>
                    <div className="connection_account_details">
                        <h1 className="account_category">Accounting Platforms</h1>
                        <div className="connection_popup_account">
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/quickbooks.svg" alt="QuickBooks"/>
                                    <div>
                                        <h1>QuickBooks</h1>
                                        <p>Sync QuickBooks for automated accounting.</p>
                                    </div>
                                    <a href="https://quickBooks.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </div>
                                <QuickBooksConnect qbCode={qbCode} qbRealmId={qbRealmId} dataSources={dataSources} />
                            </div>
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/xero.svg" alt="Xero"/>
                                    <div>
                                        <h1>Xero</h1>
                                        <p>Connect Xero for automated accounting.</p>
                                    </div>
                                    <a href="https://xero.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </div>
                                <XeroConnect xeroCode={xeroCode} dataSources={dataSources}/>
                            </div>
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/zohobooks.jpeg" alt="Zoho Books"/>
                                    <div>
                                        <h1>Zoho Books</h1>
                                        <p>Connect Zoho Books for smart accounting.</p>
                                    </div>
                                    <a href="https://zoho.com/books/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                    </div>
                                <CommingSoon/>
                            </div>
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/square.svg" alt="Stripe"/>
                                    <div>
                                        <h1>Square</h1>
                                        <p>Gain deeper financial insights.</p>
                                    </div>
                                    <a href="https://squareup.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </div>
                                <CommingSoon/>
                            </div>
                        </div>
                    </div>
                    <div className="connection_account_details">
                        <h1 className="account_category">Expense & Spend Management</h1>
                        <div className="connection_popup_account">
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/plaid.svg" alt="Stripe"/>
                                    <div>
                                        <h1>Plaid</h1>
                                        <p>Secure bank connections.</p>
                                    </div>
                                    <a href="https://plaid.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </div>
                                <CommingSoon/>
                            </div>
                            <div className="account_wrap">
                                <div className="_title">
                                    <img src="/next_images/expensify.svg" alt="Stripe"/>
                                    <div>
                                        <h1>Expensify</h1>
                                        <p>Simplify expense tracking.</p>
                                    </div>
                                    <a href="https://www.expensify.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </div>
                                <CommingSoon/>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}