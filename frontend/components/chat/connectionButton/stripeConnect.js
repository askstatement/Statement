"use client"
import { useState, useEffect, useMemo } from "react";

// context
import { useProjectContext } from "@/context/ProjectContext";
import { useWebSocket } from "@/context/WebSocketContext";

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function StripeConnect(props) {

    const { stripeCode, dataSources = [] } = props;

    const isStripeConnected = dataSources.includes('stripe');

    const { project } = useProjectContext();
    const [isDisconnecting, setIsDisconnecting] = useState(false);
    const { syncProgress } = useWebSocket();
    const progress = syncProgress?.stripe;

    useEffect(() => {
        if (stripeCode && project?.project?._id) handleStripeCode();
    }, [stripeCode, project?.project?._id]);

    const handleStripeCode = async () => {
        const projectId = project?.project?._id;
        try {
            if (!project?.project?._id) throw new Error("Project ID is missing.");
            const res = await fetch(`${API_HOST}/stripe/oauth/callback`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    code: stripeCode,
                    project_id: project?.project?._id || "",
                }),
            });

            if (res.ok) {
                const resData = await res.json();
                const { access_token } = resData;
                if (!access_token) {
                    setTimeout(() => {
                        removeStripeParamsAndReload();
                    }, 3500);
                    return
                }

                console.log("Stripe connected and sync initiated.");
            } else {
                console.error("Failed to sync Stripe data.");
                setTimeout(() => {
                    removeStripeParamsAndReload();
                }, 3500);
            }
        } catch (err) {
            console.error("Error sending key:", err);
            throw err;
        }
    };

    const removeStripeParamsAndReload = () => {
        const url = window.location.origin + window.location.pathname;
        window.location.href = `${url}?tab=chat&connect=true`;
    }

    const disconnectStripe = async () => {
        if (!project?.project?._id) return;
        setIsDisconnecting(true);
        try {
            const res = await fetch(`${API_HOST}/stripe/disconnect`, {
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
                console.error("Failed to disconnect Stripe.");
            }
        } catch (err) {
            console.error("Error disconnecting:", err);
            throw err;
        } finally {
            setIsDisconnecting(false);
        }
    }

    const connectUsingSDK = () => {
        if (isStripeConnected && !isDisconnecting) return disconnectStripe();
        const clientId = process.env.STRIPE_CLIENT_ID;
        const redirectUri = `${window.location.origin}/chat?tab=chat&stripe_status=connected`;
        const state = project?.project?._id || "";

        const stripeAuthUrl = `https://connect.stripe.com/oauth/authorize?response_type=code&client_id=${clientId}&scope=read_write&redirect_uri=${encodeURIComponent(redirectUri)}&state=${state}`;

        // Redirect to Stripe's OAuth page
        window.location.href = stripeAuthUrl;
    }

    // Check if sync is active
    const isLoading = progress?.status === 'in-progress';
    const isError = progress?.status === 'error';
    const isDone = progress?.status === 'done';

    // We are in the authorizing phase if the code is in the URL but we haven't received any sync progress message yet.
    const isAuthorizing = useMemo(() => !!stripeCode && !progress, [stripeCode, progress]);

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
    } else if (isStripeConnected) {
        buttonText = "Disconnect";
        buttonDisabled = false;
    }

    useEffect(() => {
        if (progress?.status === 'done' || progress?.status === 'error') {
            setTimeout(() => {
                removeStripeParamsAndReload();
            }, 3500);
        }
    }, [progress]);

    return (
        <div className="account_connect_button">
            <button
                className={`${(isStripeConnected && !isLoading && !isDisconnecting) ? 'disconnect' : ''} ${(isLoading || isAuthorizing || isDisconnecting) ? 'in-progress' : ''}`}
                disabled={buttonDisabled}
                onClick={connectUsingSDK}
            >
                {buttonText}
            </button>
        </div>
    )
}