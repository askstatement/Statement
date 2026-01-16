'use client'
import { useState } from "react";

// components
import ConnectPopup from "./connectPopup";

export default function AddConnection(props) {
    const { onClose, dataSources, stripeCode } = props;

    // 'connect', 'paypal', or 'chargebee'
    const [activePopup, setActivePopup] = useState('connect');

    // Helper to set popup and reload page
    const handleOnBack = (popup, syncStarted = false) => {
        setActivePopup(popup);
        if (syncStarted) {
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        }
    };

    return (
        <>
            {activePopup === 'connect' && (
                <ConnectPopup
                    dataSources={dataSources}
                    stripeCode={stripeCode}
                    onClose={onClose}
                    onOpenPaypalPopup={() => setActivePopup('paypal')}
                    onOpenChargebeePopup={() => setActivePopup('chargebee')}
                />
            )}
        </>
    );
}