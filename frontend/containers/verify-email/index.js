"use client"
import { useEffect } from "react";
import { useRouter, useSearchParams } from 'next/navigation';
import { getSessionIdFromCookie } from "@/utils/cookie";

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function VerifyEmail() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const verifyEmailToken = async () => {
      const email = searchParams.get('email');
      const token = searchParams.get('token');

      try {
        const response = await fetch(`${API_HOST}/auth/verify-email?email=${email}&token=${token}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        const sessionId = getSessionIdFromCookie();

        if (response.ok) {
          if (sessionId) {
            router.push("/chat?everify=success");
          } else {
            router.push("/login?everify=success");
          }
        } else {
          if (sessionId) {
            router.push("/chat?everify=failed");
          } else {
            router.push("/login?everify=failed");
          }
        }
      } catch (error) {
        router.push('/login?everify=failed');
      }
    };

    verifyEmailToken();
  }, []);

  return (
    <div className="auth_container"></div>
  );
}