"use client";
import { useState } from "react";
import posthog from "posthog-js";

// context
import { useProjectContext } from "@/context/ProjectContext";

// utils
import { getAccessTokenFromCookie } from "@/utils/cookie";

const API_HOST = process.env.API_HOST || "http://localhost:8765/api";

export default function PaypalPopup(props) {
  const { onBack } = props;

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [message, setMessage] = useState(null);

  const { project } = useProjectContext();

  const handlePopupSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage(null);

    try {
      if (!project?.project?._id) {
        setMessage("Project ID is missing.");
        setIsSubmitting(false);
        return;
      }
      
      const res = await fetch(`${API_HOST}/paypal/oauth/callback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: clientId,
          client_secret: clientSecret,
          project_id: project.project._id,
        }),
      });

      if (res.ok) {
        posthog.capture("paypal_connected");
        posthog.capture("data_connected", { source: "paypal" });
        const resData = await res.json();
        const { access_token } = resData;
        if (!access_token) {
          setMessage("Error: failed to get access token!");
          setIsSubmitting(false);
          return;
        }

        // Close popup and start WebSocket sync (which will update the button in AddConnection)
        sessionStorage.setItem("paypal_sync_initiated", "true");
        console.log("Paypal connected and sync initiated.");
        onBack(true); // Go back to AddConnection to show progress
      } else {
        setMessage("Failed to connect. Please check your credentials.");
        setIsSubmitting(false);
      }
    } catch (err) {
      console.error("Error submitting PayPal credentials:", err);
      setMessage(`Error: ${err.message || err}`);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="connection_wrap">
      <div className="paypal-popup-overlay">
        <div className="paypal-header-icons">
          <div className="paypal-top-button" onClick={() => onBack(false)}>
            <img src="/next_images/back.svg" alt="Back" />
          </div>
        </div>
        <div className="paypal-popup-wrapper">
          <div className="paypal-popup-header">
            <div className="popup-header-logo">
              <img src="/next_images/paypal.svg" alt="PayPal" />
            </div>
            <div className="popup-header-contents">
              <h2 className="popup-header-title">PayPal Integration</h2>
              <p className="popup-header-subtitle">
                Connect your PayPal account to sync transaction data.
              </p>
              <a
                href="https://askstatement.com/paypal-integration-guide"
                target="_blank"
                rel="noopener noreferrer"
              >
                How to generate keys and connect to Statement AI
              </a>
            </div>
          </div>
          <div className="paypal-popup-modal">
            <form className="paypal-popup-form">
              <div className="paypal-input-container client-id">
                <div className="input-label">Client ID</div>
                <input
                  type="text"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder="Enter PayPal Client ID"
                  required
                  disabled={isSubmitting}
                  className="paypal-input"
                />
              </div>

              <div className="paypal-input-container client-secret">
                <div className="input-label">Client Secret Key</div>
                <input
                  type="password"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  placeholder="Enter PayPal Client Secret"
                  required
                  disabled={isSubmitting}
                  className="paypal-input password"
                />
              </div>

              <div
                className="paypal-connect-button"
                onClick={handlePopupSubmit}
              >
                <div disabled={isSubmitting} className="paypal-blue-connect">
                  {isSubmitting ? "Connecting..." : "Connect PayPal"}
                </div>
              </div>

              {message && <div className="message-container">{message}</div>}

              <div className="paypal-disclosure-text">
                Your data is encrypted and secure. We only access transaction
                data.
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
