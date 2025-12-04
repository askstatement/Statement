import React, { useState, useEffect } from 'react';
import Script from "next/script";
import { PublicClientApplication } from "@azure/msal-browser";
import posthog from "posthog-js";

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';
const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID || '';
const MS_CLIENT_ID = process.env.MS_CLIENT_ID || '';
const NEXT_PUBLIC_BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || '';

export default function SocialButtons(props) {
  const [googleLoaded, setGoogleLoaded] = useState(false);
  const [msalInstance, setMsalInstance] = useState(null);

  // Initialize MSAL on client side
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const msalConfig = {
        auth: {
          clientId: MS_CLIENT_ID,
          authority: "https://login.microsoftonline.com/common",
          redirectUri: NEXT_PUBLIC_BASE_URL,
        },
        cache: {
          cacheLocation: "sessionStorage",
          storeAuthStateInCookie: false,
        },
      };

      const instance = new PublicClientApplication(msalConfig);

      // Important: Wait for MSAL initialization
      instance.initialize().then(() => {
        setMsalInstance(instance);
      });
    }
  }, []);

  // ------------------ GOOGLE LOGIN ------------------

  const handleGoogleScriptLoad = () => setGoogleLoaded(true);

  const handleGoogleLogin = async (credentialResponse) => {
    props?.setSigninLoading?.(true);
    props?.setMessage?.("");

    const path = window.location.pathname;
    const isSignup = path.startsWith("/signup");

    try {
      const res = await fetch(`${API_HOST}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id_token: credentialResponse.credential,
          is_signup: isSignup,
        }),
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        setPostHogUser(data.user.email);

        if (data.session_id) {
          document.cookie = `session_id=${data.session_id}; path=/; secure; samesite=lax`;
        }
        document.cookie = `access_token=${data.access_token}; path=/; secure; samesite=lax`;

        window.location.href = "/chat";
      } else {
        const error = await res.json();
        props?.setMessage?.(error.detail || "Google login failed");
      }
    } catch (error) {
      console.error("Google login error:", error);
      props?.setMessage?.("Error connecting to server");
    } finally {
      props?.setSigninLoading?.(false);
    }
  };

  useEffect(() => {
    if (googleLoaded && window.google) {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleLogin,
      });
    }
  }, [googleLoaded]);

  const handleGoogleButtonClick = () => {
    if (window.google?.accounts?.id) {
      const tempDiv = document.createElement("div");
      tempDiv.style.display = "none";
      document.body.appendChild(tempDiv);

      window.google.accounts.id.renderButton(tempDiv, {
        type: "standard",
        theme: "outline",
        size: "large",
      });

      setTimeout(() => {
        const googleBtn = tempDiv.querySelector('div[role="button"]');
        googleBtn?.click();
      }, 100);
    }
  };

  // ------------------ MICROSOFT LOGIN ------------------

  const handleLogin = async () => {
    if (!msalInstance) {
      props?.setMessage?.("Microsoft login is initializing, please wait...");
      return;
    }

    try {
      const loginResponse = await msalInstance.loginPopup({
        scopes: ["User.Read"],
        prompt: "select_account",
      });

      props?.setMessage?.(null);

      const idToken = loginResponse.idToken;
      const path = window.location.pathname;
      const isSignup = path.startsWith("/signup");

      let res = await fetch(`${API_HOST}/auth/microsoft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: idToken, is_signup: isSignup }),
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        setPostHogUser(data.user.email);

        if (data.session_id) {
          document.cookie = `session_id=${data.session_id}; path=/; secure; samesite=lax`;
        }
        document.cookie = `access_token=${data.access_token}; path=/; secure; samesite=lax`;

        window.location.href = "/chat";
      } else {
        const error = await res.json();
        props?.setMessage?.(error.detail || "Microsoft login failed");
      }
    } catch (err) {
      console.error("MS login error:", err);
      props?.setMessage?.("Microsoft login failed");
    }
  };


  const setPostHogUser = (email) => {
    posthog.identify(email, {
        email: email,
    });

    posthog.capture('signup_completed')
  }

  return (
    <div className='socials'>
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={handleGoogleScriptLoad}
      />
      <button
        className='social_button google'
        onClick={handleGoogleButtonClick}
        disabled={!googleLoaded}
        type="button"
      >
        <img src="/next_images/google.svg" alt="Google Logo" />
        <span>Continue with Google</span>
      </button>
      <button
        className='social_button microsoft'
        type="button"
        onClick={handleLogin}
        disabled={!msalInstance}
      >
        <img src="/next_images/microsoft.svg" alt="Microsoft Logo" />
        <span>Continue with Microsoft Account</span>
      </button>
      {/* <button className='social_button apple' type="button">
        <img src="/next_images/apple.svg" alt="Apple Logo" />
        <span>Continue with Apple</span>
      </button> */}
    </div>
  );
}
