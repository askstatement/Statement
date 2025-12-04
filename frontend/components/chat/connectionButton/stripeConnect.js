"use client"
import { useState, useEffect } from "react";
import posthog from "posthog-js";

// context
import { useProjectContext } from "@/context/ProjectContext";

// utils
import { getAccessTokenFromCookie } from "@/utils/cookie";

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function StripeConnect(props) {

    const { stripeCode, dataSources = [] } = props;

    const isStripeConnected = dataSources.includes('stripe');

    const [isLoading, setIsLoading] = useState(false);
    const [isPause, setIsPause] = useState(false);
    const [isError, setIsError] = useState(false);
    const [loadingButtonText, setLoadingButtonText] = useState(
        isStripeConnected ? "Disconnect" : "Connecting to stripe.."
    );

    const [connectBtnText, setConnectBtnText] = useState(
        isStripeConnected ? "Disconnect" : props.buttonText ? props.buttonText: "Connect"
    );

    const { project } = useProjectContext();

    useEffect(() => {
        if (stripeCode && project?.project?._id) handleStripeCode();
    }, [stripeCode, project?.project?._id]);

    const handleStripeCode = async () => {
        setIsLoading(true);
        
        try {
            setIsError(true);
            if (!project?.project?._id) throw new Error("Project ID is missing.");
            setLoadingButtonText("Syncing data...");
            const res = await fetch(`${API_HOST}/stripe/oauth/callback`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    code: stripeCode,
                    project_id: project?.project?._id || "",
                }),
            });

            if (res.ok) {
                posthog.capture('stripe_connected');
                posthog.capture('data_connected',{ source: 'stripe'});
                const resData = await res.json();
                const { access_token } = resData;
                if (!access_token) {
                    setIsError(true);
                    setLoadingButtonText(`Error: failed to get access token!`)
                    setTimeout(() => {
                        removeStripeParamsAndReload();
                    }, 3500);
                    return
                }
                setLoadingButtonText("Connected to stripe, starting data sync..");               
                // connect ws and show progress
                connectStripeDataSyncWs(access_token);
            } else {
                setLoadingButtonText("Failed to sync stripe data.");
                console.error("Failed to sync Stripe data.");
                setTimeout(() => {
                    removeStripeParamsAndReload();
                }, 3500);
            }
        } catch (err) {
            setLoadingButtonText("Error connecting to stripe.");
            console.error("Error sending key:", err);
            setIsLoading(false);
            throw err;
        }
    };

    const removeStripeParamsAndReload = () => {
        const url = window.location.origin + window.location.pathname;
        window.location.href = `${url}?tab=chat&connect=true`;
    }

    const disconnectStripe = async () => {
        if (!project?.project?._id) return;
        setIsLoading(true);
        setLoadingButtonText("Disconnecting...");
        try {
            const res = await fetch(`${API_HOST}/stripe/disconnect`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    project_id: project?.project?._id || "",
                }),
            });

            if (res.ok) {
                posthog.capture('stripe_disconnected');
                posthog.capture('data_disconnected',{ source: 'stripe'});
                const url = window.location.origin + window.location.pathname;
                window.location.href = `${url}?tab=chat&connect=true`;
            } else {
                console.error("Failed to disconnect Stripe.");
            }
        } catch (err) {
            console.error("Error disconnecting:", err);
            throw err;
        }
        setIsLoading(false);
    }

    const connectUsingSDK = () => {
        if (isStripeConnected) return disconnectStripe();
        setIsLoading(true);
        const clientId = process.env.STRIPE_CLIENT_ID;
        const redirectUri = `${window.location.origin}/chat?tab=chat&stripe_status=connected`;
        const state = project?.project?._id || "";

        const stripeAuthUrl = `https://connect.stripe.com/oauth/authorize?response_type=code&client_id=${clientId}&scope=read_write&redirect_uri=${encodeURIComponent(redirectUri)}&state=${state}`;

        // Redirect to Stripe's OAuth page
        window.location.href = stripeAuthUrl;
    }

    const connectStripeDataSyncWs = (access_token) => {
        setIsLoading(true);
        const proto = window.location.protocol;
        const isLiveEnv = proto === "https:";
        const WP_HOST = process.env.WS_HOST || "localhost:8765/ws";
        let ws_url = isLiveEnv
            ? `wss://${WP_HOST}/stripe/sync-stripe-data`
            : `ws://${WP_HOST}/stripe/sync-stripe-data`;
        const jwtToken = getAccessTokenFromCookie();
        if (!jwtToken) return reject(new Error("WebSocket initialization failed: No token"));
        if (!project?.project?._id) throw new Error("Project ID is missing.");
        if (!access_token) throw new Error("Stripe access_token is missing.");

        ws_url += `?token=${jwtToken}&access_token=${access_token}&project_id=${project?.project?._id}`;

        const ws = new WebSocket(ws_url);

        ws.onopen = () => console.log("Stripe webSocket connected");;

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.status === "in-progress") {
                setLoadingButtonText(`Step ${message.progress}: processing ${message.step.split("_").join(" ")}`)
            } else if (message.status === "done") {
                setLoadingButtonText(`Data sync completed successfully..`)
                // update page url to avoid repeated api call
                setTimeout(() => {
                    removeStripeParamsAndReload();
                }, 3500);
                setIsLoading(false);
            } else if (message.status === "error") {
                setIsError(true);
                setLoadingButtonText(`Error: ${message.message}`)
                ws.close();
                // update page url to avoid repeated api call
                setTimeout(() => {
                    removeStripeParamsAndReload();
                }, 3500);
                setIsLoading(false);
            }
        };

        ws.onclose = () =>  {
            console.log("Stripe webSocket closed");
            removeStripeParamsAndReload();
            setIsLoading(false);
        }
    }

    return (
        <div className="account_connect_button">
            <button 
                className={`${(isStripeConnected || isError) && !isLoading ? 'disconnect' : ''}`}
                disabled={isLoading}
                onClick={connectUsingSDK}
            >
                {isStripeConnected && !isLoading ? 'Disconnect' : isLoading ? loadingButtonText : connectBtnText}
            </button>
            {/* {isStripeConnected && (
                <div className="available_account">
                    <h1>Available Accounts & Credit Cards</h1>
                    <div className="available_accoutn_wrap">
                        <div className="connnected_account">
                            <span className={isPause ? "status paused" : "status"}>{isPause? "Paused":"Connected"}</span>
                            <h2>Axis  Bank</h2>
                        </div>
                        {isPause? 
                            <div className="button_wrap">
                                <button onClick={() => setIsPause(false)}>Reconnect</button>
                                <button className="_delete">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
                                        <path d="M21 5.97656C17.67 5.64656 14.32 5.47656 10.98 5.47656C9 5.47656 7.02 5.57656 5.04 5.77656L3 5.97656" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                        <path d="M8.5 4.97L8.72 3.66C8.88 2.71 9 2 10.69 2H13.31C15 2 15.13 2.75 15.28 3.67L15.5 4.97" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                        <path d="M18.8484 9.14062L18.1984 19.2106C18.0884 20.7806 17.9984 22.0006 15.2084 22.0006H8.78844C5.99844 22.0006 5.90844 20.7806 5.79844 19.2106L5.14844 9.14062" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                        <path d="M10.3281 16.5H13.6581" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                        <path d="M9.5 12.5H14.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                    </svg>
                                </button>
                            </div>
                            :
                            <button onClick={() => setIsPause(true)}>Pause</button>
                        }
                    </div>
                </div>
            )} */}
        </div>
    )
}