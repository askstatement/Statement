'use client';
import "@/style/globals.scss";
import '@/style/container/auth.scss';
import { Suspense } from 'react';
import { ToastContainer, Bounce } from 'react-toastify';

export default function AuthLayout({ children }) {
  return (
    <div className="auth_layout">
      <Suspense fallback={<></>}>
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
      </Suspense>
    </div>
  );
}
