'use client';
import "@/style/globals.scss";
import '@/style/container/chat.scss';
import '@/style/layout/chatlayout.scss';
import { useState, useEffect, Suspense } from 'react';
import { ToastContainer, Bounce } from 'react-toastify';
import posthog from "posthog-js";

// utils
import "@/utils/interceptFetch";
import { removeCookie } from "@/utils/cookie";
import { getSessionIdFromCookie } from "@/utils/cookie";

// context
import { SessionContext } from "@/context/SessionContext";
import { ProjectProvider } from "@/context/ProjectContext";
import Navbar from "@/components/chat/navbar";

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function ChatLayout({ children }) {

  const [session, setSession] = useState(null);

  const clearSessionAndReload = () => {
    posthog.reset();
    removeCookie("access_token")
    window.location.reload();
  }

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const sessionId = getSessionIdFromCookie();
        const res = await fetch(`${API_HOST}/auth/session?sid=${sessionId}`, {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        });
        if (!res.ok) throw clearSessionAndReload()
        const data = await res.json();
        if (!data?.user) clearSessionAndReload();
        setSession(data);
      } catch (err) {
        console.error('Session fetch error:', err);
        setSession(null);
      }
    };

    fetchSession();
  }, []);

  return (
    <div className="chat_layout">
      <Suspense fallback={<></>}>
        <ProjectProvider>
          <SessionContext.Provider value={session}>
            <Navbar />
            <main className="page_content">
                {children}
                <ToastContainer
                  position="top-right"
                  autoClose={5000}
                  hideProgressBar={false}
                  newestOnTop={false}
                  closeOnClick={false}
                  rtl={false}
                  pauseOnFocusLoss
                  draggable
                  pauseOnHover
                  theme="light"
                  transition={Bounce}
                />
            </main>
          </SessionContext.Provider>
        </ProjectProvider>
      </Suspense>
    </div>
  );
}
