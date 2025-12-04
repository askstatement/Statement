'use client'
import { useState } from "react";

// components
import ConnectPopup from "./connectPopup";

export default function AddConnection(props) {
    const { onClose, dataSources, stripeCode, xeroCode, qbCode, qbRealmId } = props;
    
    // 'connect' or 'paypal'
    const [activePopup, setActivePopup] = useState('connect');
    
    // Shared PayPal sync state
    const [paypalSyncState, setPaypalSyncState] = useState({
        isLoading: false,
        isError: false,
        loadingText: ''
    });

    const handleOpenPaypalPopup = () => {
        setActivePopup('paypal');
    };

    const handleCloseAll = () => {
        // Reset states
        setPaypalSyncState({
            isLoading: false,
            isError: false,
            loadingText: ''
        });
        setActivePopup('connect');
        onClose();
    };

    return (
        <>
            {activePopup === 'connect' && (
                <ConnectPopup
                    dataSources={dataSources}
                    stripeCode={stripeCode}
                    xeroCode={xeroCode}
                    qbCode={qbCode}
                    qbRealmId={qbRealmId}
                    onClose={handleCloseAll}
                    onOpenPaypalPopup={handleOpenPaypalPopup}
                    paypalSyncState={paypalSyncState}
                    setPaypalSyncState={setPaypalSyncState}
                />
            )}
        </>
    );
}