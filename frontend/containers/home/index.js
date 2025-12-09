'use client'
import Link from "next/link";

export default function Home () {
    return (
        <div className="home" style={{height: "50vh", display: "flex", alignItems: "center", justifyContent: "center"}}>
            <img className="_statement-logo" src="/next_images/statement_logo.svg" slt="Statement"/>
            <h1>Welcome to Statement</h1>
            <h2>Your financial insights start here.</h2>
            <div className="_action-button">
                <div className="_left">
                    <h3>Login</h3>
                    <div className="_explanation">Access your dashboard</div>
                </div>
                <div className="_right">
                    <Link href="/login">
                        <button>Login</button>
                    </Link>
                </div>
            </div>
            <div className="_action-button">
                <div className="_left">
                    <h3>Create Account</h3>
                    <div className="_explanation">Set up your workspace in minutes</div>
                </div>
                <div className="_right">
                    <Link href="/signup">
                        <button>Sign Up</button>
                    </Link>
                </div>
            </div>
            <div className="_support">
                Need help contact <a href="support@askstatement.com">Contact support</a>
            </div>
        </div>
    )
}