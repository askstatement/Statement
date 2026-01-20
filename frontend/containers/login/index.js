"use client";
import { useState, useEffect, useRef } from 'react';
import { toast } from 'react-toastify';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import posthog from 'posthog-js';

import '@/style/container/auth.scss';

//components
import SocialButtons from '@/components/uiElements/socialButtons';

// utils
import { getCookie, removeCookie, setSessionCookies } from '@/utils/cookie';

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function Login() {

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [token, setToken] = useState("");
    const [signinLoading, setSigninLoading] = useState(false);
    const [forgotPassword, setForgotPassword] = useState(false);
    const [tokenError, setTokenError] = useState("");
    const [authSection, setAuthSection] = useState("login")
    const [message, setMessage] = useState("");
    const [notification, setNotification] = useState("");
    const [forgotEmail, setFotgotEmail] = useState("");
    
    const searchParams = useSearchParams();
    const emailStatus = searchParams.get('everify');
    const unsubscribe = searchParams.get('unsubscribe');
    
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
        const minLoadingTime = 1000;
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
                const resData = await res.json();      
                if(resData.two_factor_enabled) {
                    setAuthSection("2fa")
                    return;
                } 
                verificationSuccess(resData)
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

    const handle2fa = async (e) => {
        e.preventDefault()        
        try {
            const res = await fetch(`${API_HOST}/auth/2fa_login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ token,  email, password}),
            });

            const resData = await res.json();
            
            if (res.status == 200) {
                setEmail("");
                setToken("")
                setTokenError("")
                verificationSuccess(resData)
            } else {
                setTokenError("Invalid Token")
            }
        } catch (err) {
            console.error(`Error updating Two-Factor Authentication :`, err);
        }
    }

    const verificationSuccess = (resData) => {
        try {
            setEmail("");
            setPostHogUser(email);
                    
            if (resData.access_token && resData.session_id) {
                setSessionCookies(resData.access_token, resData.session_id, 7);
                // Redirect to /chat
                let is_checkout_flow = getCookie("is_checkout_flow");
                if (is_checkout_flow) {
                    removeCookie("is_checkout_flow");
                    // parse data from cookie
                    let details = JSON.parse(is_checkout_flow);
                    if (details?.plan_id && typeof details?.is_annual === 'boolean') {
                        return window.location.href = `/pricing?plan_selected=${details?.plan_id}&is_annual=${details?.is_annual}`;
                    } else {
                        return window.location.href = `/pricing`;
                    }
                } else if (unsubscribe) {
                    return window.location.href = `/chat?unsubscribe`;
                }
                window.location.href = '/chat';
            }
        } catch(err) {
            console.log(err);            
        }
    }
    return (
        <>
            {authSection == 'login' &&
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
                            <Link href="" className='forgot_password' onClick={() => setAuthSection("forgot")}>Forgot password?</Link>
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
            {authSection == 'forgot' && 
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
                            <Link href="" className='forgot_password' onClick={() => setAuthSection("login")}>Back to Sign in</Link>
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
            {authSection == '2fa' && 
                <div className="auth_container">
                    <div className='auth_wrap'>
                        <div className='logo'>
                            <img src="/next_images/logo.svg" alt="StatementAI Logo" />
                        </div>
                        <h1>Two Factor Authentication</h1>
                        <div className='content-wrapper two_factor'>
                            {notification && <div className='_notification'>{notification}</div>}
                            <form onSubmit={handle2fa} style={{ maxWidth: 400, margin: "auto" }} autoComplete="off">
                                <p className="two_factor_description">Enter the 6-digit code from your authenticator app</p>
                                <div className="field_wrap">
                                    <input
                                        type="text"
                                        placeholder="Enter Code"
                                        maxLength={6}
                                        inputMode="numeric"
                                        pattern="[0-9]*"
                                        onChange={(e) => setToken(e.target.value)}
                                        onInput={(e) => {
                                            e.target.value = e.target.value.replace(/[^0-9]/g, "");
                                    }}
                                    />
                                </div>
                                <p className='_error'>{tokenError}</p>
                                <button type='submit' className='login_button'>
                                    Verify
                                </button>
                            </form>
                            <Link href="" className='forgot_password' onClick={() => {
                                setAuthSection("login")
                                setTokenError("")
                            }}>
                                Back to Sign in
                            </Link>
                        </div>
                    </div>
                </div>
            }
        </>
    )
}
