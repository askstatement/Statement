"use client";
import { useState, useEffect, useMemo } from "react";
import posthog from "posthog-js";

// context
import { useProjectContext } from "@/context/ProjectContext";
import { useWebSocket } from "@/context/WebSocketContext";

// utils
import { getAccessTokenFromCookie } from "@/utils/cookie";

const API_HOST = process.env.API_HOST || "http://localhost:8765/api";

export default function XeroConnect(props) {
  const { xeroCode, dataSources = [] } = props;

  const isXeroConnected = dataSources.includes("xero");

  const { project } = useProjectContext();
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const { syncProgress } = useWebSocket();
  const progress = syncProgress?.xero;

  useEffect(() => {
    // If there's a xeroCode in the URL and we have a project, handle the auth callback.
    if (xeroCode && project?.project?._id) handleXeroCode();
  }, [xeroCode, project?.project?._id]);

  const handleXeroCode = async () => {
    const projectId = project?.project?._id;
    if (!projectId) {
      return;
    }

    try {
      if (!project?.project?._id) throw new Error("Project ID is missing.");
      // get xero_code_verifier from session storage
      const code_verifier = sessionStorage.getItem("xero_code_verifier");
      if (!code_verifier) {
        setTimeout(() => {
          removeXeroParamsAndReload();
        }, 3500);
        return;
      }
      const res = await fetch(`${API_HOST}/xero/oauth/callback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: xeroCode,
          code_verifier: code_verifier,
          project_id: project?.project?._id || "",
        }),
      });

      if (res.ok) {
        posthog.capture("xero_connected");
        posthog.capture("data_connected", { source: "xero" });
        const resData = await res.json();
        const { access_token } = resData;
        if (!access_token) {
          setTimeout(() => {
            removeXeroParamsAndReload();
          }, 3500);
          return;
        }

        console.log("Xero connected and sync initiated.");
      } else {
        console.error("Failed to sync Xero data.");
        setTimeout(() => {
          removeXeroParamsAndReload();
        }, 3500);
      }
    } catch (err) {
      console.error("Error sending key:", err);
      throw err;
    }
  };

  // Check if sync is active
  const isLoading = progress?.status === "in-progress";
  const isError = progress?.status === "error";
  const isDone = progress?.status === "done";

  // We are in the authorizing phase if the code is in the URL but we haven't received any sync progress message yet.
  const isAuthorizing = useMemo(
    () => !!xeroCode && !progress,
    [xeroCode, progress],
  );

  // Determine button text and state
  let buttonText = "Connect";
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
  } else if (isXeroConnected) {
    buttonText = "Disconnect";
    buttonDisabled = false;
  }

  useEffect(() => {
    if (progress?.status === "done" || progress?.status === "error") {
      setTimeout(() => {
        removeXeroParamsAndReload();
      }, 3500);
    }
  }, [progress]);

  const removeXeroParamsAndReload = () => {
    const url = window.location.origin + window.location.pathname;
    window.location.href = `${url}?tab=chat&connect=true`;
  };

  const disconnectXero = async () => {
    if (!project?.project?._id) return;
    setIsDisconnecting(true);
    try {
      const res = await fetch(`${API_HOST}/xero/disconnect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: project?.project?._id || "",
        }),
      });

      if (res.ok) {
        posthog.capture("xero_disconnected");
        posthog.capture("data_disconnected", { source: "xero" });
        const url = window.location.origin + window.location.pathname;
        window.location.href = `${url}?tab=chat&connect=true`;
      } else {
        console.error("Failed to disconnect Xero.");
      }
    } catch (err) {
      console.error("Error disconnecting:", err);
      throw err;
    } finally {
      setIsDisconnecting(false);
    }
  };

  const generatePKCE = async () => {
    // Generate random code_verifier (43-128 characters)
    const generateRandomString = (length) => {
      const possible =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
      const values = window.crypto.getRandomValues(new Uint8Array(length));
      return Array.from(values).reduce(
        (acc, x) => acc + possible[x % possible.length],
        "",
      );
    };

    const code_verifier = generateRandomString(64);

    const base64encode = (arrayBuffer) => {
      const bytes = new Uint8Array(arrayBuffer);
      let binary = "";
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      return btoa(binary)
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=/g, "");
    };

    const encoder = new TextEncoder();
    const data = encoder.encode(code_verifier);
    const digest = await window.crypto.subtle.digest("SHA-256", data);

    const code_challenge = base64encode(digest);

    return { code_verifier, code_challenge };
  };

  const connectUsingSDK = async () => {
    // If already connected and not syncing, disconnect
    if (isXeroConnected && !isLoading && !isDisconnecting) {
      return disconnectXero();
    }

    try {
      const { code_verifier, code_challenge } = await generatePKCE();
      sessionStorage.setItem("xero_code_verifier", code_verifier);

      const clientId = process.env.XERO_CLIENT_ID;
      const redirectUri = `${window.location.origin}/chat?tab=chat&connect=true&xeroStatus=connected`;
      const scopes = [
        "offline_access",
        "openid",
        "profile",
        "email",
        "accounting.transactions.read",
        "accounting.reports.read",
        "accounting.journals.read",
        "accounting.settings.read",
        "accounting.contacts.read",
        "accounting.attachments.read",
        "accounting.budgets.read",
        "payroll.employees.read",
        "payroll.payruns.read",
        "payroll.payslip.read",
        "payroll.timesheets.read",
        "payroll.settings.read",
        "assets.read",
        "projects.read",
      ].join(" ");

      const xeroAuthUrl = `https://login.xero.com/identity/connect/authorize?response_type=code&client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${encodeURIComponent(scopes)}&code_challenge=${code_challenge}&code_challenge_method=S256&state=xeroConnected`;

      window.location.href = xeroAuthUrl;
    } catch (error) {
      console.error("Error generating PKCE:", error);
    }
  };

  return (
    <div className="account_connect_button">
      <button
        className={`${isXeroConnected && !isLoading && !isDisconnecting ? "disconnect" : ""} ${isLoading || isAuthorizing || isDisconnecting ? "in-progress" : ""}`}
        disabled={buttonDisabled}
        onClick={connectUsingSDK}
      >
        {buttonText}
      </button>
    </div>
  );
}
