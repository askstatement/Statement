'use client'
import { useState } from "react";

// components
import ConnectPopup from "./connectPopup";
import PaypalPopup from "./paypalPopup";

export default function AddConnection(props) {
  const { onClose, dataSources, stripeCode, xeroCode, qbCode, qbRealmId } =
    props;

  // 'connect', 'paypal', or 'chargebee'
  const [activePopup, setActivePopup] = useState("connect");

  // Shared PayPal sync state
  const [paypalSyncState, setPaypalSyncState] = useState({
    isLoading: false,
    isError: false,
    loadingText: "",
  });

  const handleCloseAll = () => {
    // Reset states
    setPaypalSyncState({
      isLoading: false,
      isError: false,
      loadingText: "",
    });
    setActivePopup("connect");
    onClose();
  };

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
      {activePopup === "connect" && (
        <ConnectPopup
          dataSources={dataSources}
          stripeCode={stripeCode}
          xeroCode={xeroCode}
          qbCode={qbCode}
          qbRealmId={qbRealmId}
          onClose={handleCloseAll}
          onOpenPaypalPopup={() => setActivePopup("paypal")}
          onOpenChargebeePopup={() => setActivePopup("chargebee")}
          paypalSyncState={paypalSyncState}
          setPaypalSyncState={setPaypalSyncState}
        />
      )}
      {activePopup === "paypal" && (
        <PaypalPopup
          dataSources={dataSources}
          onClose={onClose}
          onBack={(syncStarted) => handleOnBack("connect", syncStarted)}
        />
      )}
    </>
  );
}