"use client";
import { useState, useEffect } from "react";
import posthog from "posthog-js";

// context
import { useProjectContext } from "@/context/ProjectContext";
import { useWebSocket } from "@/context/WebSocketContext";

const API_HOST = process.env.API_HOST || "http://localhost:8765/api";

export default function PaypalConnect(props) {
  const { dataSources = [], onOpenPaypalPopup, buttonText } = props;

  const isPaypalConnected = dataSources.includes("paypal");

  const { project } = useProjectContext();
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [isAuthorizing, setIsAuthorizing] = useState(
    () =>
      typeof window !== "undefined" &&
      sessionStorage.getItem("paypal_sync_initiated") === "true",
  );
  const { syncProgress } = useWebSocket();
  const progress = syncProgress?.paypal;

  const handlePaypalAuth = async (e) => {
    e.preventDefault();

    if (isPaypalConnected && !isDisconnecting) {
      await disconnectPaypal();
    } else {
      // Open the PayPal popup
      onOpenPaypalPopup();
    }
  };

  const disconnectPaypal = async () => {
    if (!project?.project?._id) return;
    setIsDisconnecting(true);
    try {
      const res = await fetch(`${API_HOST}/paypal/disconnect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: project?.project?._id || "",
        }),
      });

      if (res.ok) {
        posthog.capture("paypal_disconnected");
        posthog.capture("data_disconnected", { source: "paypal" });
        const url = window.location.origin + window.location.pathname;
        window.location.href = `${url}?tab=chat&connect=true`;
      } else {
        console.error("Failed to disconnect Paypal.");
      }
    } catch (err) {
      console.error("Error disconnecting:", err);
    } finally {
      setIsDisconnecting(false);
    }
  };

  // Check if sync is active
  const isLoading = progress?.status === "in-progress";
  const isError = progress?.status === "error";
  const isDone = progress?.status === "done";

  // Determine button text and state
  let buttonTextValue = buttonText || "Connect";
  let buttonDisabled = false;

  if (isDisconnecting) {
    buttonTextValue = "Disconnecting...";
    buttonDisabled = true;
  } else if (isLoading) {
    buttonTextValue = `Step ${progress.progress}: processing ${progress.step.split("_").join(" ")}`;
    buttonDisabled = true;
  } else if (isAuthorizing) {
    buttonTextValue = "Establishing connection...";
    buttonDisabled = true;
  } else if (isError) {
    buttonTextValue = `Error: ${progress.message}`;
    buttonDisabled = false;
  } else if (isDone) {
    buttonTextValue = "Sync Complete!";
    buttonDisabled = true;
  } else if (isPaypalConnected) {
    buttonTextValue = "Disconnect";
    buttonDisabled = false;
  }

  useEffect(() => {
    if (progress) {
      // Once we get a progress update, we can clear the flag.
      if (sessionStorage.getItem("paypal_sync_initiated")) {
        sessionStorage.removeItem("paypal_sync_initiated");
        setIsAuthorizing(false);
      }
    }
    if (progress?.status === "done" || progress?.status === "error") {
      setTimeout(() => {
        const url = window.location.origin + window.location.pathname;
        window.location.href = `${url}?tab=chat&connect=true`;
      }, 3500);
    }
  }, [progress]);

  return (
    <div className="account_connect_button">
      <form onSubmit={handlePaypalAuth}>
        <button
          className={`${isPaypalConnected && !isLoading && !isDisconnecting ? "disconnect" : ""} ${isLoading || isAuthorizing || isDisconnecting ? "in-progress" : ""}`}
          type="submit"
          disabled={buttonDisabled}
        >
          {buttonTextValue}
        </button>
      </form>
    </div>
  );
}
