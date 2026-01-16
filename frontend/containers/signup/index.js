"use client";
import { useState } from 'react';

import '@/style/container/auth.scss';

//components
import SocialButtons from '@/components/uiElements/socialButtons';

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function Login () {


    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [firstname, setFirstname] = useState("");
    const [lastname, setLastname] = useState("");
    const [message, setMessage] = useState("");
    const [signupLoading, setSignupLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage("");
        setSignupLoading(true)
        const minLoadingTime = 1000; 
        const startTime = Date.now();

        try {
            const elapsed = Date.now() - startTime;
            if (elapsed < minLoadingTime) {
                await new Promise(resolve => setTimeout(resolve, minLoadingTime - elapsed));
            }

            if (!email || !password || !firstname || !lastname) {
                setMessage("All fields are required");
                return;
            }
            const res = await fetch(`${API_HOST}/auth/signup`, {
                method: "POST",
                headers: {
                "Content-Type": "application/json",
                },
                body: JSON.stringify({ email, password, firstname, lastname }),
            });

            if (res.status === 200) {
                setEmail("");
                setPassword("");
                window.location.href = '/login'; // Redirect to login after successful signup
            } else {
                const data = await res.json();
                setMessage(data.detail || "Registration failed");
            }
        } catch (error) {
            setMessage("Error connecting to server");
        } finally {
            setSignupLoading(false)
        }
    };

    return (
        <div className="auth_container">
            <div className='auth_wrap'>
                <div className='logo'>
                    <img src="/next_images/logo.svg" alt="StatementAI Logo"/>
                </div>
                <h1>Sign up to Statement</h1>
                <div className='content-wrapper'>
                    <form onSubmit={handleSubmit} style={{ maxWidth: 400, margin: "auto" }}>
                        <div className='inline-fields'>
                            <div className="field_wrap">
                                <input required placeholder="First Name" onChange={(e) => setFirstname(e.target.value)}/>
                            </div>
                            <div className="field_wrap">
                                <input required placeholder="Last Name" onChange={(e) => setLastname(e.target.value)}/>
                            </div>
                        </div>
                        <div className="field_wrap">
                            <input required placeholder="Email" autoComplete="off" type="email" onChange={(e) => setEmail(e.target.value)}/>
                        </div>
                        <div className="field_wrap">
                            <input required type="password" placeholder="Create Password" name="real-password" autoComplete="new-password" onChange={(e) => setPassword(e.target.value)}/>
                        </div>
                        <button type='submit' className='login_button'>
                            {signupLoading ? <div className='_loading'><img src='/next_images/signin_loading.svg' />Signing up...</div>
                                : 'Sign up'}
                        </button>
                    </form>
                    <div className='_error'>{message}</div>
                    <p className='register'>Already have an account? <a href="/login">Login</a></p>
                    <div className='divider'>
                        <div className='_before'></div>
                        <span>or</span>
                        <div className='_after'></div>
                    </div>
                    <SocialButtons setMessage={setMessage} />
                    <div className='policy'>
                        <p><a href='/terms'>Terms of Service</a> and <a href='/privacy'>Privacy Policy</a></p>
                    </div>
                </div>
            </div>
        </div>
    )
}