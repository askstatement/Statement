'use client'
import { useRouter } from "next/navigation";

// components
import StripeConnect from "@/components/chat/connectionButton/stripeConnect";
import CommingSoon from "@/components/chat/connectionButton/commingSoon";

export default function ConnectPopup(props) {    
    const { stripeCode, dataSources, onClose } = props;

    const router = useRouter()

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
                <p className="popup_description">Unify your financial accounts for real-time visibility into cash flow, performance, and growth.</p>
                <div className="popup_scroll">
                    <div className="connection_account_details">
                        <h1 className="account_category">Accounts</h1>
                        <div className="connection_popup_account">
                            <div className="account_wrap">
                                <h1>
                                    <img src="/next_images/bank.svg" alt="Bank"/>
                                    Bank Accounts & Credit Cards
                                    <a href="#" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </h1>
                                <p>Track bank inflows and outflows for a clear cash flow view. Spot gaps early, manage balances daily, and link multiple cards. Available with US and EU banks (UK coming soon).</p>
                                <CommingSoon/>
                            </div>
                        </div>
                    </div>
                    <div className="connection_account_details">
                        <h1 className="account_category">Payment Platforms</h1>
                        <div className="connection_popup_account">
                            <div className="account_wrap">
                                <h1>
                                    <img src="/next_images/stripe.svg" alt="Stripe"/>
                                    Stripe
                                    <a href="https://stripe.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </h1>
                                <p>Monitor transactions and subscription revenues in real time. Gain instant insight into how your sales channels are performing across platforms.</p>
                                <StripeConnect stripeCode={stripeCode} dataSources={dataSources}/>
                            </div>
                            <div className="account_wrap">
                                <h1>
                                    <img src="/next_images/paypal.svg" alt="PayPal"/>
                                    PayPal
                                    <a href="https://paypal.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </h1>
                                <p>Keep track of PayPal transactions and recurring revenues as they happen. Instantly measure performance across payment streams.</p>
                                <CommingSoon/>
                            </div>
                        </div>
                    </div>
                    <div className="connection_account_details">
                        <h1 className="account_category">Accounting Platforms</h1>
                        <div className="connection_popup_account">
                            <div className="account_wrap">
                                <h1>
                                    <img src="/next_images/quickbooks.svg" alt="QuickBooks"/>
                                    QuickBooks
                                    <a href="https://quickBooks.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </h1>
                                <p>Integrate QuickBooks for a full accounting overview. Save time with automated reconciliations and reduce manual reporting errors.</p>
                                <CommingSoon/>
                            </div>
                            <div className="account_wrap">
                                <h1>
                                    <img src="/next_images/xero.svg" alt="Xero"/>
                                    Xero
                                    <a href="https://xero.com/" target="_blank" className="ext-link">
                                        <img className="ext-link" src="/next_images/external-link.svg" alt="External link"/>
                                    </a>
                                </h1>
                                <p>Connect Xero to access a complete view of your financial health. Automate reconciliations and minimize manual reporting errors.</p>
                                <CommingSoon/>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}