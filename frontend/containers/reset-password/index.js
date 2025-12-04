"use client"
import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import '@/style/container/auth.scss';

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function ResetPassword() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [email, setEmail] = useState("");
    const [token, setToken] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [message, setMessage] = useState("");
    const [notification, setNotification] = useState("");
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // Get token and email from URL
        const urlToken = searchParams.get('token');
        const urlEmail = searchParams.get('email');
        
        if (urlToken) setToken(urlToken);
        if (urlEmail) setEmail(urlEmail ?? "");
    }, [searchParams]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage("");
        
        if (newPassword !== confirmPassword) {
            setMessage("Passwords do not match");
            return;
        }
        
        if (newPassword.length < 6) {
            setMessage("Password must be at least 6 characters");
            return;
        }

        setLoading(true);
        try {
            const res = await fetch(`${API_HOST}/auth/reset-password`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ 
                    email, 
                    token, 
                    new_password: newPassword,
                    confirm_password: confirmPassword 
                }),
            });

            const data = await res.json();
            
            if (res.status === 200) {
                setNotification("Password reset successfully! Redirecting...");
                setTimeout(() => router.push('/login'), 2000);
            } else {
                setMessage(data.detail || "Password reset failed");
            }
        } catch (error) {
            setMessage("Error connecting to server");
        }
        setLoading(false);
    };

    return (
        <div className="auth_container">
            <div className='auth_wrap'>
                <div className='logo'>
                    <img src="/next_images/logo.svg" alt="StatementAI Logo"/>
                </div>
                <h1>Reset Password</h1>
                <div className='content-wrapper'>
                    {notification && <div className='_notification'>{notification}</div>}
                    <form onSubmit={handleSubmit} style={{ maxWidth: 400, margin: "auto" }} autoComplete="off">
                        <div className="field_wrap">
                            <input 
                                required 
                                type="password" 
                                placeholder="New Password" 
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                autoComplete="new-password"
                            />
                        </div>
                        <div className="field_wrap">
                            <input 
                                required 
                                type="password" 
                                placeholder="Confirm New Password" 
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                autoComplete="new-password"
                            />
                        </div>
                        <button type='submit' className='login_button' disabled={loading}>
                            {loading ? "Resetting Password..." : "Reset Password"}
                        </button>
                    </form>
                    <div className='_error'>{message}</div>
                    <p className='register'>
                        Remember your password? <a href="/login">Sign in</a>
                    </p>
                </div>
            </div>
        </div>
    );
}