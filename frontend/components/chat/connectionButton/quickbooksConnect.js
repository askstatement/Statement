"use client";
import { useState, useEffect, useMemo } from "react";

// context
import { useProjectContext } from "@/context/ProjectContext";
import { useWebSocket } from "@/context/WebSocketContext";

// utils
import { getAccessTokenFromCookie } from "@/utils/cookie";

// utils
const API_HOST = process.env.API_HOST || "http://localhost:8765/api";

const QB_CLIENT_ID = process.env.QUICKBOOKS_CLIENT_ID;

export default function QuickBooksConnect(props) {
  const { qbCode, qbRealmId, dataSources = [] } = props;

  const isQBConnected = dataSources.includes("quickbooks");

  const { project } = useProjectContext();
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const { syncProgress } = useWebSocket();
  const progress = syncProgress?.quickbooks;

  useEffect(() => {
    if (qbCode && project?.project?._id) handleQBCode();
  }, [qbCode, project?.project?._id]);

  const handleQBCode = async () => {
    try {
      if (!project?.project?._id) throw new Error("Project ID is missing.");

      if (!qbCode || !qbRealmId) {
        setTimeout(() => {
          removeQBParamsAndReload();
        }, 3500);
        return;
      }

      const res = await fetch(`${API_HOST}/quickbooks/oauth/callback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: qbCode,
          realm_id: qbRealmId,
          project_id: project?.project?._id || "",
        }),
      });

      if (res.ok) {
        const resData = await res.json();
        const { access_token } = resData;
        if (!access_token) {
          setTimeout(() => {
            removeQBParamsAndReload();
          }, 3500);
          return;
        }

        console.log("QuickBooks connected and sync initiated.");
      } else {
        console.error("Failed to sync QuickBooks data.");
        setTimeout(() => {
          removeQBParamsAndReload();
        }, 3500);
      }
    } catch (err) {
      console.error("Error:", err);
      throw err;
    }
  };

  const removeQBParamsAndReload = () => {
    const url = window.location.origin + window.location.pathname;
    window.location.href = `${url}?tab=chat&connect=true`;
  };

  const disconnectQB = async () => {
    if (!project?.project?._id) return;
    setIsDisconnecting(true);
    try {
      const res = await fetch(`${API_HOST}/quickbooks/disconnect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: project?.project?._id || "",
        }),
      });

      if (res.ok) {
        const url = window.location.origin + window.location.pathname;
        window.location.href = `${url}?tab=chat&connect=true`;
      } else {
        console.error("Failed to disconnect QuickBooks.");
      }
    } catch (err) {
      console.error("Error disconnecting:", err);
      throw err;
    } finally {
      setIsDisconnecting(false);
    }
  };

  const connectUsingSDK = async () => {
    if (isQBConnected && !isDisconnecting) return disconnectQB();
    try {
      const redirectUri = `${window.location.origin}/chat?tab=chat&connect=true&qbStatus=connected`;
      const scopes = [
        "com.intuit.quickbooks.accounting",
        "com.intuit.quickbooks.payment",
        "openid",
        "profile",
      ].join(" ");

      const qbAuthUrl = `https://appcenter.intuit.com/connect/oauth2?client_id=${QB_CLIENT_ID}&response_type=code&scope=${encodeURIComponent(scopes)}&redirect_uri=${encodeURIComponent(redirectUri)}&state=qbConnected`;

      window.location.href = qbAuthUrl;
    } catch (error) {
      console.error("Error generating PKCE:", error);
    }
  };  

  // Check if sync is active
  const isLoading = progress?.status === "in-progress";
  const isError = progress?.status === "error";
  const isDone = progress?.status === "done";

  // We are in the authorizing phase if the code is in the URL but we haven't received any sync progress message yet.
  const isAuthorizing = useMemo(
    () => !!qbCode && !progress,
    [qbCode, progress],
  );  

  // Determine button text and state
  let buttonText = props.buttonText || "Connect";
  let buttonDisabled = false;

  if (isDisconnecting) {
    buttonText = "Disconnecting...";
    buttonDisabled = true;
  } else if (isLoading) {
    buttonText = `Step ${progress.progress}: processing ${progress.step.split("_").join(" ")}`;
    buttonDisabled = true;
  } else if (isAuthorizing) {
    buttonText = "Establishing connection...";
    buttonDisabled = true;
  } else if (isError) {
    buttonText = `Error: ${progress.message}`;
    buttonDisabled = false;
  } else if (isDone) {
    buttonText = "Sync Complete!";
    buttonDisabled = true;
  } else if (isQBConnected) {
    buttonText = "Disconnect";
    buttonDisabled = false;
  }

  useEffect(() => {
    if (progress?.status === "done" || progress?.status === "error") {
      setTimeout(() => {
        removeQBParamsAndReload();
      }, 3500);
    }
  }, [progress]);

  return (
    <div className="account_connect_button">
      <button
        className={`${isQBConnected && !isLoading && !isDisconnecting ? "disconnect" : ""} ${isLoading || isAuthorizing || isDisconnecting ? "in-progress" : ""}`}
        disabled={buttonDisabled}
        onClick={connectUsingSDK}
      >
        {buttonText}
      </button>
    </div>
  );
}
