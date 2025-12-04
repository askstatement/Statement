"use client";
import { useState, useEffect, useRef } from 'react';
import { toast } from 'react-toastify';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import posthog from 'posthog-js';

import '@/style/container/auth.scss';

//components
import SocialButtons from '@/components/uiElements/socialButtons';

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function Login() {

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [signinLoading, setSigninLoading] = useState(false);
    const [forgotPassword, setForgotPassword] = useState(false);
    const [message, setMessage] = useState("");
    const [notification, setNotification] = useState("");
    const [forgotEmail, setFotgotEmail] = useState("");
    
    const searchParams = useSearchParams();
    const emailStatus = searchParams.get('everify');
    const hasShownToast = useRef(false);

    useEffect(() => {
        // Skip if no emailStatus or toast already shown
        if (!emailStatus || hasShownToast.current) return;
            
        const showVerificationPopup = async () => {

            try {
                if (emailStatus === "success") {
                    hasShownToast.current = true;
                    toast.success("Email verified successfully! Please log in.", {
                        position: "top-right",
                        autoClose: 5000,
                        hideProgressBar: false,
                        closeOnClick: false,
                        pauseOnHover: true,
                        draggable: true,
                        progress: undefined,
                        theme: "dark",
                    });
                } else if (emailStatus === "failed") {
                    hasShownToast.current = true;
                    toast.error("Email verification failed or the link has expired. Please try again.", {
                        position: "top-right",
                        autoClose: 5000,
                        hideProgressBar: false,
                        closeOnClick: false,
                        pauseOnHover: true,
                        draggable: true,
                        progress: undefined,
                        theme: "dark",
                    });
                }
            } catch (error) {
            router.push('/login?everify=failed')
            }
        };

        showVerificationPopup();
    }, [emailStatus]);

    const setPostHogUser = (email) => {        
        posthog.identify(email, {
            email: email,
        });
        posthog.capture('signin_completed')
    }

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage("");
        setSigninLoading(true)
        const minLoadingTime = 3000;
        const startTime = Date.now();
        try {
            const elapsed = Date.now() - startTime;
            if (elapsed < minLoadingTime) {
                await new Promise(resolve => setTimeout(resolve, minLoadingTime - elapsed));
            }

            if (!email || !password) {
                setMessage("Email and password are required");
                return;
            }
            const res = await fetch(`${API_HOST}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email, password }),
            });

            if (res.status === 200) {
                setEmail("");
                setPostHogUser(email);
                const resData = await res.json();
                // Assuming the response contains an access token
                if (resData.access_token) {
                    console.log('Access Token:', resData.access_token);
                    const expires = new Date();
                    expires.setDate(expires.getDate() + 7);
                    if (resData.session_id) {
                        document.cookie = `session_id=${resData.session_id}; path=/; secure; samesite=lax`;
                    }
                    document.cookie = `access_token=${resData.access_token}; path=/; secure; samesite=lax`;
                    // Redirect to /chat
                    window.location.href = '/chat';
                }
            } else {
                const data = await res.json();
                setMessage(data.detail || "Login failed");
            }
        } catch (error) {
            setMessage("Error connecting to server");
        } finally {
            setSigninLoading(false)
        }
    };

    const handleForgotPassword = async (e) => {
        e.preventDefault();
        setNotification("");
        
        try {
            const res = await fetch(`${API_HOST}/auth/forgot-password`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email: forgotEmail }),
            });

            const data = await res.json();
            setNotification(data.msg); // This will show the success message regardless of email existence
            
        } catch (error) {
            setMessage("Error connecting to server");
        } finally {
            setSigninLoading(false)
        }
    };

    return (
        <>
            {!forgotPassword ?
                <div className="auth_container">
                    <div className='auth_wrap'>
                        <div className='logo'>
                            <img src="/next_images/logo.svg" alt="StatementAI Logo" />
                        </div>
                        <h1>Sign in to Statement</h1>
                        <div className='content-wrapper'>
                            {notification && <div className='_notification'>{notification}</div>}
                            <form onSubmit={handleSubmit} style={{ maxWidth: 400, margin: "auto" }} autoComplete="off">
                                <div className="field_wrap">
                                    <input required placeholder="Email" autoComplete="off" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                                </div>
                                <div className="field_wrap">
                                    <input required type="password" placeholder="Password" name="real-password" autoComplete="new-password" onChange={(e) => setPassword(e.target.value)} />
                                </div>
                                <button type='submit' className='login_button'>
                                    {signinLoading ? <div className='_loading'><img src='/next_images/signin_loading.svg' />Signing in...</div>
                                        : 'Sign in'}
                                </button>
                            </form>
                            <div className='_error'>{message}</div>
                            <Link href="" className='forgot_password' onClick={() => setForgotPassword(true)}>Forgot password?</Link>
                            <p className='register'>Don't have an account? <a href="/signup">Sign up</a></p>
                            <div className='divider'>
                                <div className='_before'></div>
                                <span>or</span>
                                <div className='_after'></div>
                            </div>
                            <SocialButtons setSigninLoading={setSigninLoading} setMessage={setMessage} />
                            <div className='policy'>
                                <p><a href='/terms'>Terms of Service</a> and <a href='/privacy'>Privacy Policy</a></p>
                            </div>
                        </div>
                    </div>
                </div>
                :
                <div className="auth_container">
                    <div className='auth_wrap'>
                        <div className='logo'>
                            <img src="/next_images/logo.svg" alt="StatementAI Logo" />
                        </div>
                        <h1>Reset Password</h1>
                        <div className='content-wrapper'>
                            {notification && <div className='_notification'>{notification}</div>}
                            <form onSubmit={handleForgotPassword} style={{ maxWidth: 400, margin: "auto" }} autoComplete="off">
                                <div className="field_wrap">
                                    <input 
                                        required 
                                        placeholder="Email" 
                                        autoComplete="off" 
                                        type="email" 
                                        value={forgotEmail}
                                        onChange={(e) => setFotgotEmail(e.target.value)}
                                    />
                                </div>
                                <button type='submit' className='login_button'>
                                    Send Reset Link
                                </button>
                            </form>
                            <div className='_error'>{message}</div>
                            <Link href="" className='forgot_password' onClick={() => setForgotPassword(false)}>Back to Sign in</Link>
                            <p className='register'>Don't have an account? <a href="/signup">Sign up</a></p>
                            <div className='divider'>
                                <div className='_before'></div>
                                <span>or</span>
                                <div className='_after'></div>
                            </div>
                            <SocialButtons setSigninLoading={setSigninLoading} setMessage={setMessage} />
                            <div className='policy'>
                                <p><a href='/terms'>Terms of Service</a> and <a href='/privacy'>Privacy Policy</a></p>
                            </div>
                        </div>
                    </div>
                </div>
            }
        </>
    )
}
