
export default function WelcomePopup ({openConnection}) {
    return (
        <div className="welcome_container">
            <h4>Getting Started with Statement</h4>
            <h1>Welcome to Statement </h1>
            <p>You are one step away. Connect Stripe or your accounting software and unlock your first insight in minutes, no dashboards, no spreadsheets, just clarity.</p>
            <div className="welcome_connect">
                <h2>Connect your sources</h2>
                <div className="account_connect_button">
                    <div className="source_details">
                        <div>
                            <img src="/next_images/stripe.svg"/>
                        </div>
                        <div>
                            <img src="/next_images/paypal.svg"/>
                        </div>
                        <div>
                            <img src="/next_images/quickbooks.svg"/>
                        </div>
                        <div>
                            <img src="/next_images/xero.svg"/>
                        </div>
                        <p>+2 more</p>
                    </div>
                    <button onClick={openConnection}>Connect</button>
                </div>
            </div>
        </div>
    )
}